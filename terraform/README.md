# Infraestrutura

Consulte [guia Terraform](../docs/terraform.md). Cada subpasta aws, azure e databricks
é uma raiz com state próprio; bootstrap/aws e bootstrap/azure preparam state/OIDC.
Nenhum recurso é criado por testes ou terraform validate. Copie os exemplos para
terraform.tfvars somente localmente. Arquivos de lock devem ser versionados.
