data "azurerm_client_config" "current" {}
resource "azurerm_resource_group" "project" {
  name     = "rg-airflow-multicloud-dev-${var.suffix}"
  location = var.location
  tags     = { project = "airflow-multicloud", environment = "dev" }
}
resource "azurerm_storage_account" "lake" {
  name                            = "stafmc${var.suffix}"
  resource_group_name             = azurerm_resource_group.project.name
  location                        = azurerm_resource_group.project.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  is_hns_enabled                  = true
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false
  tags                            = azurerm_resource_group.project.tags
}
resource "azurerm_role_assignment" "deployer_data" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = data.azurerm_client_config.current.object_id
}
resource "azurerm_storage_data_lake_gen2_filesystem" "bronze" {
  name               = "bronze"
  storage_account_id = azurerm_storage_account.lake.id
  depends_on         = [azurerm_role_assignment.deployer_data]
}
resource "azurerm_role_assignment" "airflow" {
  scope                = "${azurerm_storage_account.lake.id}/blobServices/default/containers/${azurerm_storage_data_lake_gen2_filesystem.bronze.name}"
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.airflow_principal_id
}
resource "azurerm_key_vault" "project" {
  name                       = "kv-afmc-${var.suffix}"
  resource_group_name        = azurerm_resource_group.project.name
  location                   = azurerm_resource_group.project.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  tags                       = azurerm_resource_group.project.tags
}
