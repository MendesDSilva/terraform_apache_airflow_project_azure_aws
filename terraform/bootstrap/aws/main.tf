terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.63.0"
    }
  }
}
provider "aws" { region = var.region }
variable "region" {
  type    = string
  default = "us-east-1"
}
variable "suffix" { type = string }
variable "github_repository" {
  type        = string
  description = "owner/repo exato, respeitando maiúsculas."
}
variable "github_environment" {
  type    = string
  default = "terraform-dev"
}
variable "oidc_provider_arn" {
  type        = string
  default     = null
  description = "Informe se já existe provider GitHub na conta; não duplique."
}
variable "deployment_policy_arns" {
  type        = set(string)
  default     = []
  description = "Policies de provisionamento revisadas pelo administrador, distintas da policy runtime."
}
resource "aws_s3_bucket" "state" {
  bucket = "airflow-multicloud-state-${var.suffix}"
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_policy" "tls" {
  bucket = aws_s3_bucket.state.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Deny", Principal = "*", Action = "s3:*",
    Resource  = [aws_s3_bucket.state.arn, "${aws_s3_bucket.state.arn}/*"],
    Condition = { Bool = { "aws:SecureTransport" = "false" } }
  }] })
}
resource "aws_iam_openid_connect_provider" "github" {
  count          = var.oidc_provider_arn == null ? 1 : 0
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}
resource "aws_iam_role" "github" {
  name = "airflow-multicloud-${var.suffix}-github"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect    = "Allow", Action = "sts:AssumeRoleWithWebIdentity",
    Principal = { Federated = coalesce(var.oidc_provider_arn, try(aws_iam_openid_connect_provider.github[0].arn, null)) },
    Condition = { StringEquals = {
      "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:environment:${var.github_environment}"
    } }
  }] })
}
resource "aws_iam_role_policy" "state" {
  role = aws_iam_role.github.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:ListBucket"], Resource = aws_s3_bucket.state.arn },
    { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = "${aws_s3_bucket.state.arn}/dev/*" },
    { Effect = "Allow", Action = ["s3:DeleteObject"], Resource = "${aws_s3_bucket.state.arn}/dev/*.tflock" }
  ] })
}
resource "aws_iam_role_policy_attachment" "deployment" {
  for_each   = var.deployment_policy_arns
  role       = aws_iam_role.github.name
  policy_arn = each.value
}
output "state_bucket" { value = aws_s3_bucket.state.id }
output "github_role_arn" { value = aws_iam_role.github.arn }
