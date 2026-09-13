output "pipeline_config" {
  value = {
    account_url = azurerm_storage_account.lake.primary_dfs_endpoint
    filesystem  = azurerm_storage_data_lake_gen2_filesystem.bronze.name
  }
}
output "key_vault_uri" { value = azurerm_key_vault.project.vault_uri }
