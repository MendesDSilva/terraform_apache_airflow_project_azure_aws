# Databricks Free Edition

## Pré-requisitos reais

Workspace com Unity Catalog, serverless e permissão de criar catálogos/schemas,
volumes, tabelas, notebooks e jobs. O projeto não cria workspace/metastore e não usa
APIs de conta. A autenticação local encontrada durante o planejamento estava inválida;
não há evidência de execução remota nesta entrega.

```powershell
databricks auth login --host https://SEU-WORKSPACE.cloud.databricks.com --profile airflow-dev
databricks auth profiles
databricks catalogs list --profile airflow-dev
Copy-Item terraform/databricks/terraform.tfvars.example terraform/databricks/terraform.tfvars
# Edite host/profile/clouds; não adicione token.
terraform -chdir=terraform/databricks init
terraform -chdir=terraform/databricks plan -out=deployment.tfplan
terraform -chdir=terraform/databricks apply deployment.tfplan
```

São criados os catálogos aws-airflow-gold e azure-airflow-gold, conforme clouds.
O usuário de deploy é proprietário dos objetos e dos jobs. Use a mesma identidade
no Airflow local. Outra identidade precisa de grants USE CATALOG, USE SCHEMA,
READ/WRITE VOLUME e permissão CAN_MANAGE_RUN no job. O job continua executando como
seu proprietário, com CREATE TABLE/SELECT/MODIFY nos schemas/tabelas pertinentes.

Caso um catálogo já exista, importe-o antes do apply, por exemplo:

```powershell
terraform -chdir=terraform/databricks import 'databricks_catalog.cloud["aws"]' aws-airflow-gold
```

Se não houver CREATE CATALOG, um administrador deve criar os catálogos exatos e
transferir propriedade/conceder privilégios. Se Free Edition bloquear a operação,
registre essa limitação: não renomeie objetos para o catálogo default nem alegue
que a integração foi concluída.

## Autenticação no container

```powershell
docker compose run --rm auth -c "databricks auth login --host https://SEU-WORKSPACE.cloud.databricks.com --profile airflow-dev --timeout 10m"
docker compose run --rm auth -c "python /opt/airflow/scripts/doctor.py --databricks-only"
```

Abra a URL fornecida no navegador do host. Depois da autorização, o navegador tenta
abrir localhost, que pertence ao container. Copie a URL final da barra de endereço
e cole na entrada oculta do terminal. O auxiliar oauth_browser.py valida o destino
e entrega esse callback somente à CLI local, sem abrir portas no Docker. Não envie
essa URL a terceiros: ela contém um código de autorização temporário.

O cache OAuth fica em /auth/home e o profile em /auth/databricks/config. Containers
sem keyring usam DATABRICKS_AUTH_STORAGE=plaintext no volume privado, com permissões
de arquivo restritas pela CLI. Nenhum token é impresso pelo
doctor. OAuth U2M precisa ser renovado quando a sessão expirar; não é identidade
de serviço para operação permanente.

## Jobs e resultados

Terraform incorpora common.py em notebooks para preservar a mesma transformação
sem empacotamento Spark adicional. Dois jobs, cada um com Silver → Gold, sem
cluster_id. Airflow passa input_path e load_date, aguarda sucesso e registra run_id.
As tarefas recebem parâmetros de job por widgets. O limite local permite duas
tarefas remotas concorrentes; cotas Free Edition podem interromper compute.

```sql
SELECT * FROM `aws-airflow-gold`.gold.bookings_daily_airport
WHERE load_date = (SELECT max(load_date) FROM `aws-airflow-gold`.gold.bookings_daily_airport);

SELECT * FROM `azure-airflow-gold`.gold.bookings_daily_airport
WHERE load_date = (SELECT max(load_date) FROM `azure-airflow-gold`.gold.bookings_daily_airport);
```

Para Power BI, use o conector Azure Databricks/Databricks compatível com o workspace,
Server Hostname e HTTP Path do SQL warehouse. A disponibilidade de autenticação no
conector depende do ambiente. Filtre uma única load_date; não some snapshots.

Referências: [OAuth U2M](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-u2m),
[volumes](https://docs.databricks.com/aws/en/volumes/volume-files).

## Default Storage na Free Edition

Se a criação de catálogo pelo provider retornar `Metastore storage root URL does not exist`,
execute no SQL warehouse serverless do workspace:

```sql
CREATE CATALOG IF NOT EXISTS `aws-airflow-gold`;
CREATE CATALOG IF NOT EXISTS `azure-airflow-gold`;
```

Depois importe os catálogos para os endereços `databricks_catalog.cloud["aws"]` e
`databricks_catalog.cloud["azure"]` antes de gerar um novo plano. A configuração
preserva `storage_root` atribuído pelo workspace, evitando recriar os catálogos.
Revise o plano: ele não deve destruir os catálogos importados. Continue com o apply
para criar schemas, volumes, notebooks e jobs.

Esse caminho SQL foi executado com sucesso neste workspace em 09/09/2026.
Consulte [Default Storage](https://docs.databricks.com/aws/en/storage/default-storage).