output "pipeline_config" {
  value = {
    host = var.host
    jobs = { for cloud, job in databricks_job.pipeline : cloud => job.id }
  }
}
