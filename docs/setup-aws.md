# AWS

## Autenticação e primeira criação

Use conta de estudo e um permission set SSO de provisionamento revisado pelo administrador.
Terraform precisa criar S3, Glue/Catalog/Crawler, Athena e IAM. A policy runtime criada
pelo projeto serve ao Airflow; não dá permissão para provisionar infraestrutura.

```powershell
aws configure sso --profile airflow-dev
aws sso login --profile airflow-dev
$env:AWS_PROFILE = 'airflow-dev'
Copy-Item terraform/aws/terraform.tfvars.example terraform/aws/terraform.tfvars
# Edite suffix e region no arquivo copiado.
terraform -chdir=terraform/aws init
terraform -chdir=terraform/aws validate
terraform -chdir=terraform/aws plan -out=deployment.tfplan
terraform -chdir=terraform/aws apply deployment.tfplan
terraform -chdir=terraform/aws output
```

Anexe a policy `airflow_policy_arn` ao permission set/role de execução conforme a
administração da sua conta. Não crie access keys permanentes. O deploy publica o
script Glue e common.py no S3; o job usa Glue 5.0, dois G.1X, sem retries internos.

## Login dentro do Docker

Depois de inicializar Airflow, configure um profile separado no cache Docker:

```powershell
docker compose run --rm auth -c "aws configure sso --profile airflow-dev --use-device-code --no-browser"
docker compose run --rm auth -c "aws sso login --profile airflow-dev --use-device-code --no-browser"
```

Abra a URL e informe o código mostrados. O profile deve ter acesso aos recursos do
projeto. SDK boto3 usa AWS_PROFILE e a cadeia de credenciais SSO. Os caches ficam no
volume Docker auth-cache, fora do repositório.

## Conferência

Após uma carga bem-sucedida, confira os três CSVs e manifesto em Bronze no S3.
Abra Glue Runs pelo run_id dos logs Airflow; confira o Parquet no caminho de tentativa.
O task Athena registra tabela, query_id e contagem. No console Athena selecione o
workgroup e database dos outputs e execute `SELECT * FROM <tabela_registrada> LIMIT 10`.
O workgroup limita cada consulta a 100 MiB e armazena resultados criptografados no S3.

Não dispare o crawler diretamente contra a raiz de tentativas. Airflow atualiza o
alvo antes de dispará-lo e valida o resultado terminal. A tabela resultante é um
snapshot atual; histórico analítico fica nas tabelas Delta do Databricks.
