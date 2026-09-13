data "databricks_current_user" "current" {}
locals {
  catalogs = { for cloud in var.clouds : cloud => "${cloud}-airflow-gold" }
  schemas  = { for item in setproduct(var.clouds, ["staging", "silver", "gold"]) : "${item[0]}.${item[1]}" => { cloud = item[0], name = item[1] } }
  notebooks = merge(
    { for cloud in var.clouds : "${cloud}_silver" => "${path.module}/../../spark/databricks/${cloud}_silver.py" },
    { gold = "${path.module}/../../spark/databricks/gold.py" }
  )
}
resource "databricks_catalog" "cloud" {
  for_each = local.catalogs
  name     = each.value
  comment  = "Origem ${each.key}; armazenamento gerenciado Free Edition."
  # Default Storage é atribuído pelo workspace na criação SQL e preservado no import.
  lifecycle { ignore_changes = [storage_root] }
}
resource "databricks_schema" "layer" {
  for_each     = local.schemas
  catalog_name = databricks_catalog.cloud[each.value.cloud].name
  name         = each.value.name
}
resource "databricks_volume" "inbound" {
  for_each     = local.catalogs
  name         = "inbound"
  catalog_name = databricks_catalog.cloud[each.key].name
  schema_name  = databricks_schema.layer["${each.key}.staging"].name
  volume_type  = "MANAGED"
}
resource "databricks_notebook" "code" {
  for_each = local.notebooks
  path     = "${data.databricks_current_user.current.home}/airflow-multicloud/${each.key}"
  language = "PYTHON"
  # Fonte compartilhada embutida: mesmo contrato no Glue e serverless sem instalação extra.
  content_base64 = base64encode(join("\n", ["# Databricks notebook source", file("${path.module}/../../spark/common.py"), file(each.value)]))
}
resource "databricks_job" "pipeline" {
  for_each            = local.catalogs
  name                = "airflow-multicloud-${each.key}"
  max_concurrent_runs = 1
  timeout_seconds     = 2400
  parameter {
    name    = "load_date"
    default = ""
  }
  parameter {
    name    = "input_path"
    default = ""
  }
  task {
    task_key        = "gold"
    timeout_seconds = 1200
    depends_on { task_key = "silver" }
    notebook_task {
      notebook_path   = databricks_notebook.code["gold"].path
      base_parameters = { cloud = each.key }
    }
  }
  task {
    task_key        = "silver"
    timeout_seconds = 1200
    notebook_task {
      notebook_path = databricks_notebook.code["${each.key}_silver"].path
    }
  }
  depends_on = [databricks_volume.inbound, databricks_schema.layer]
}
