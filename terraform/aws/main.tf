locals {
  name = "airflow-multicloud-dev-${var.suffix}"
}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

resource "aws_s3_bucket" "lake" {
  bucket        = local.name
  force_destroy = false
}
resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_policy" "tls" {
  bucket = aws_s3_bucket.lake.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect    = "Deny", Principal = "*", Action = "s3:*",
    Resource  = [aws_s3_bucket.lake.arn, "${aws_s3_bucket.lake.arn}/*"],
    Condition = { Bool = { "aws:SecureTransport" = "false" } }
  }] })
}
resource "aws_s3_object" "glue" {
  bucket      = aws_s3_bucket.lake.id
  key         = "scripts/silver_glue.py"
  source      = "${path.module}/../../spark/aws/silver_glue.py"
  source_hash = filemd5("${path.module}/../../spark/aws/silver_glue.py")
}
resource "aws_s3_object" "common" {
  bucket      = aws_s3_bucket.lake.id
  key         = "scripts/common.py"
  source      = "${path.module}/../../spark/common.py"
  source_hash = filemd5("${path.module}/../../spark/common.py")
}
resource "aws_iam_role" "glue" {
  name = "${local.name}-glue"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "glue.amazonaws.com" }, Action = "sts:AssumeRole"
  }] })
}
resource "aws_iam_role_policy" "glue" {
  role = aws_iam_role.glue.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:ListBucket", "s3:GetBucketLocation"], Resource = aws_s3_bucket.lake.arn },
    { Effect = "Allow", Action = ["s3:GetObject"], Resource = ["${aws_s3_bucket.lake.arn}/bronze/*", "${aws_s3_bucket.lake.arn}/scripts/*"] },
    { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource = "${aws_s3_bucket.lake.arn}/silver/*" },
    { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "arn:${data.aws_partition.current.partition}:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws-glue/*" },
    { Effect = "Allow", Action = ["glue:GetDatabase", "glue:GetTable", "glue:GetTables", "glue:CreateTable", "glue:UpdateTable", "glue:DeleteTable", "glue:GetPartition", "glue:GetPartitions", "glue:BatchGetPartition", "glue:BatchCreatePartition", "glue:BatchUpdatePartition", "glue:BatchDeletePartition"], Resource = [
      "arn:${data.aws_partition.current.partition}:glue:${var.region}:${data.aws_caller_identity.current.account_id}:catalog",
      aws_glue_catalog_database.silver.arn,
      "${replace(aws_glue_catalog_database.silver.arn, ":database/", ":table/")}/*"
    ] }
  ] })
}
resource "aws_glue_job" "silver" {
  name              = "${local.name}-silver"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 40
  max_retries       = 0
  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${aws_s3_bucket.lake.id}/${aws_s3_object.glue.key}"
  }
  default_arguments = {
    "--extra-py-files"                   = "s3://${aws_s3_bucket.lake.id}/${aws_s3_object.common.key}"
    "--enable-continuous-cloudwatch-log" = "true"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--TempDir"                          = "s3://${aws_s3_bucket.lake.id}/silver/tmp/"
  }
  execution_property { max_concurrent_runs = 1 }
  depends_on = [aws_iam_role_policy.glue]
}
resource "aws_glue_catalog_database" "silver" {
  name = "airflow_multicloud_${var.suffix}"
}
resource "aws_glue_crawler" "silver" {
  name          = "${local.name}-silver"
  role          = aws_iam_role.glue.arn
  database_name = aws_glue_catalog_database.silver.name
  table_prefix  = "snapshot_"
  s3_target { path = "s3://${aws_s3_bucket.lake.id}/silver/bookings_enriched/" }
  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "DELETE_FROM_DATABASE"
  }
  # Airflow move o alvo para a tentativa confirmada; Terraform não desfaz a seleção.
  lifecycle { ignore_changes = [s3_target] }
  depends_on = [aws_iam_role_policy.glue]
}
resource "aws_athena_workgroup" "analytics" {
  name = local.name
  configuration {
    enforce_workgroup_configuration    = true
    bytes_scanned_cutoff_per_query     = 104857600
    publish_cloudwatch_metrics_enabled = true
    result_configuration {
      output_location = "s3://${aws_s3_bucket.lake.id}/athena-results/"
      encryption_configuration { encryption_option = "SSE_S3" }
    }
  }
}
resource "aws_iam_policy" "airflow" {
  name = "${local.name}-runtime"
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:ListBucket", "s3:GetBucketLocation"], Resource = aws_s3_bucket.lake.arn },
    { Effect = "Allow", Action = ["s3:PutObject", "s3:GetObject"], Resource = ["${aws_s3_bucket.lake.arn}/bronze/*", "${aws_s3_bucket.lake.arn}/athena-results/*"] },
    { Effect = "Allow", Action = ["s3:GetObject"], Resource = "${aws_s3_bucket.lake.arn}/silver/*" },
    { Effect = "Allow", Action = ["glue:StartJobRun", "glue:GetJobRun", "glue:BatchStopJobRun"], Resource = aws_glue_job.silver.arn },
    { Effect = "Allow", Action = ["glue:StartCrawler", "glue:GetCrawler", "glue:UpdateCrawler"], Resource = aws_glue_crawler.silver.arn },
    { Effect = "Allow", Action = ["iam:PassRole"], Resource = aws_iam_role.glue.arn, Condition = { StringEquals = { "iam:PassedToService" = "glue.amazonaws.com" } } },
    { Effect = "Allow", Action = ["glue:GetDatabase", "glue:GetTables", "glue:GetTable", "glue:GetPartitions"], Resource = [
      "arn:${data.aws_partition.current.partition}:glue:${var.region}:${data.aws_caller_identity.current.account_id}:catalog", aws_glue_catalog_database.silver.arn,
    "${replace(aws_glue_catalog_database.silver.arn, ":database/", ":table/")}/*"] },
    { Effect = "Allow", Action = ["athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults", "athena:StopQueryExecution", "athena:GetWorkGroup"], Resource = aws_athena_workgroup.analytics.arn }
  ] })
}
