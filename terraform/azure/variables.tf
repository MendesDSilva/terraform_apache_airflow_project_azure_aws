variable "subscription_id" { type = string }
variable "location" {
  type    = string
  default = "eastus"
}
variable "suffix" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9]{6,10}$", var.suffix))
    error_message = "Use 6 a 10 letras minúsculas ou números."
  }
}
variable "airflow_principal_id" {
  type        = string
  description = "Object ID do usuário/identidade que autentica Airflow pelo Azure CLI."
}
