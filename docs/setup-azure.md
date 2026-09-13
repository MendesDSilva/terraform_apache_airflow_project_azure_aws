# Azure

## Autenticação e provisionamento

É necessária uma assinatura ativa, permissão de criar Resource Group/Storage/Key Vault
e de atribuir RBAC. Preferir conta de estudo e permissões limitadas aos recursos do projeto.

```powershell
az login
az account set --subscription <SUBSCRIPTION-ID>
az ad signed-in-user show --query id -o tsv
Copy-Item terraform/azure/terraform.tfvars.example terraform/azure/terraform.tfvars
# Edite subscription_id, airflow_principal_id, suffix e location.
terraform -chdir=terraform/azure init
terraform -chdir=terraform/azure validate
terraform -chdir=terraform/azure plan -out=deployment.tfplan
terraform -chdir=terraform/azure apply deployment.tfplan
```

airflow_principal_id é o Object ID da identidade que fará o login no container,
não o Client ID de uma aplicação. Terraform concede Storage Blob Data Contributor
no filesystem Bronze. A identidade de deploy recebe Data Owner para criar o
filesystem via Entra ID. A propagação RBAC pode demorar; em 403, aguarde e repita apply.

## Login do Airflow

```powershell
docker compose run --rm auth -c "az login --use-device-code"
docker compose run --rm auth -c "az account set --subscription <SUBSCRIPTION-ID>"
```

O SDK usa AzureCliCredential e o cache Linux compartilhado. Não copiar caches Windows.
O Storage possui HNS, HTTPS/TLS e chaves compartilhadas desabilitadas. O endpoint
público autenticado permite o laboratório local, sem custos de private endpoints.

## Key Vault

O cofre começa vazio: o fluxo de identidade dispensa client secrets. Caso um segredo
Azure seja necessário depois, atribua Key Vault Secrets User ao leitor no cofre e
grave o segredo por canal administrativo seguro. Não coloque valores em Terraform,
pois também entrariam no state. Não concedemos Secrets User sem necessidade.

## Conferência

No Storage Browser, autentique com Entra ID e confira filesystem bronze, pastas de
carga, os três CSVs e manifesto. A ponte lê esses objetos, verifica o hash e envia
os bytes para azure-airflow-gold.staging.inbound. A Silver e Gold resultantes ficam
no Databricks Free Edition, não em diretórios Silver/Gold desta Storage Account.

## Assinatura correta e bloqueio de login por código

Confira a assinatura da conta aberta no portal antes de preencher `subscription_id`.
Use `az account list` e `az account set --subscription <SUBSCRIPTION-ID>` no Windows.
O `airflow_principal_id` deve corresponder ao usuário que fará login no Docker;
para login de usuário, obtenha-o com `az ad signed-in-user show --query id -o tsv`.

Se o login por código retornar `AADSTS530035`, use o fluxo pelo navegador,
preservando as configurações de segurança do diretório. No Windows:

```powershell
az login --tenant <TENANT-ID>
```

Para autenticar o Docker pelo navegador, execute no Windows:

```powershell
python scripts/azure_login.py --tenant <TENANT-ID> --subscription <SUBSCRIPTION-ID>
```

O auxiliar abre o navegador e encaminha o callback GET/POST por uma ponte restrita
à interface local `127.0.0.1`, preservando a validação OAuth da CLI Azure. A sessão
fica no volume auth-cache do Docker. Nenhum código precisa ser copiado ou colado;
a ponte é encerrada quando o login e o diagnóstico terminam.
O auxiliar exige que os outputs Azure já tenham sido exportados para o diagnóstico.

O auxiliar manual `oauth_browser.py` utilizado pelo Databricks não é compatível
com o retorno POST usado pelo Azure. Não copie caches Windows para o Docker.

Se o apply informar `MissingSubscriptionRegistration` para `Microsoft.KeyVault`,
registre o provedor antes de gerar um novo plano:

```powershell
az provider register --namespace Microsoft.KeyVault --subscription <SUBSCRIPTION-ID> --wait
```

Referências: [segurança padrão do Microsoft Entra](https://learn.microsoft.com/en-us/entra/fundamentals/security-defaults)
e [login interativo da CLI Azure](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli-interactively).
