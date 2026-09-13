output "pipeline_config" {
  value = {
    bucket   = aws_s3_bucket.lake.id, region = var.region,
    glue_job = aws_glue_job.silver.name, crawler = aws_glue_crawler.silver.name,
    database = aws_glue_catalog_database.silver.name, workgroup = aws_athena_workgroup.analytics.name
  }
}
output "airflow_policy_arn" { value = aws_iam_policy.airflow.arn }
