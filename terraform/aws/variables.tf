variable "region" {
  type    = string
  default = "us-east-1"
}
variable "suffix" {
  type        = string
  description = "Sufixo único, minúsculo, de 6 a 12 caracteres."
  validation {
    condition     = can(regex("^[a-z0-9]{6,12}$", var.suffix))
    error_message = "Use 6 a 12 letras minúsculas ou números."
  }
}
