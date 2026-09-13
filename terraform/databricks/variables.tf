variable "host" { type = string }
variable "profile" {
  type    = string
  default = "airflow-dev"
}
variable "clouds" {
  type    = set(string)
  default = ["aws", "azure"]
  validation {
    condition     = length(var.clouds) > 0 && alltrue([for c in var.clouds : contains(["aws", "azure"], c)])
    error_message = "Selecione aws, azure ou ambas."
  }
}
