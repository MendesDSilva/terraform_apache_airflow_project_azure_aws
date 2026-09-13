terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "5.4.0"
    }
  }
}
provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}
variable "subscription_id" { type = string }
variable "project_resource_group" { type = string }
variable "github_repository" { type = string }
variable "github_environment" {
  type    = string
  default = "terraform-dev"
}
data "azurerm_resource_group" "project" { name = var.project_resource_group }
data "azurerm_client_config" "current" {}
resource "azurerm_user_assigned_identity" "github" {
  name                = "id-airflow-github"
  location            = data.azurerm_resource_group.project.location
  resource_group_name = data.azurerm_resource_group.project.name
}
resource "azurerm_federated_identity_credential" "github" {
  name                      = "github-environment"
  user_assigned_identity_id = azurerm_user_assigned_identity.github.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = "https://token.actions.githubusercontent.com"
  subject                   = "repo:${var.github_repository}:environment:${var.github_environment}"
}
resource "azurerm_role_assignment" "deployment" {
  for_each             = toset(["Contributor", "Role Based Access Control Administrator", "Storage Blob Data Owner"])
  scope                = data.azurerm_resource_group.project.id
  role_definition_name = each.value
  principal_id         = azurerm_user_assigned_identity.github.principal_id
}
output "client_id" { value = azurerm_user_assigned_identity.github.client_id }
output "tenant_id" { value = data.azurerm_client_config.current.tenant_id }
