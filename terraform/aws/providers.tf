provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = "airflow-multicloud", Environment = "dev" }
  }
}
