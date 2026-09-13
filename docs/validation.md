# Validação local

Verificações executadas em 9 de setembro de 2026, em Windows/PowerShell com
Docker Desktop usando containers Linux.

## Resultados

| Verificação | Resultado |
|---|---|
| `ruff check .` | Passou |
| `python -m pytest tests/unit -q` | 13 testes passaram |
| `docker compose run --rm --no-deps test` | 14 testes passaram, incluindo importação e topologia da DAG |
| `terraform fmt -check -recursive terraform` | Passou |
| `terraform validate` | Passou nas raízes aws, azure, databricks, bootstrap/aws e bootstrap/azure |
| `docker compose config --quiet` | Passou |
| `python scripts/check_secrets.py` | Nenhum arquivo proibido identificado entre os arquivos considerados pelo Git |
| Testes Spark/Delta | 5 testes passaram em 282,76 s com PySpark 3.5.5 e Delta 3.3.2 |

## Correções da validação

O teste da DAG usa o caminho `airflow.dag_processing.dagbag.DagBag`, sem o
argumento removido `include_examples`, e compara o valor do enum de trigger rule.
As exceções da DAG são importadas de `airflow.sdk.exceptions`, conforme indicado
pelo Airflow 3.3.1 instalado.

A combinação PySpark 3.5.9 e Delta 3.3.2 falhou na primeira gravação
`saveAsTable` com overwrite: quatro testes passaram e o teste de reexecução
falhou. O ambiente local de testes foi fixado em PySpark 3.5.5 para contornar o
[bug Delta #4671](https://github.com/delta-io/delta/issues/4671).
Essa alteração afeta a imagem de testes, sem alterar os runtimes dos jobs cloud.
A escrita continua usando `replaceWhere` por `load_date` para preservar outras cargas. A suíte final confirmou joins, métricas, rejeição de valores inválidos e chaves conflitantes, reexecução preservando outras datas e equivalência da Gold após a transferência via Parquet.

## Reproduzir

```powershell
python -m ruff check .
python -m pytest tests/unit -q
python scripts/check_secrets.py
terraform fmt -check -recursive terraform
foreach ($tfRoot in @('aws', 'azure', 'databricks', 'bootstrap/aws', 'bootstrap/azure')) {
    terraform "-chdir=terraform/$tfRoot" init -backend=false -input=false -lockfile=readonly
    terraform "-chdir=terraform/$tfRoot" validate
}
docker compose config --quiet
docker compose build airflow-apiserver spark-test
docker compose run --rm --no-deps test
docker compose run --rm --no-deps spark-test
```

Antes dos comandos Docker, execute `python scripts/local_setup.py` caso ainda
não tenha preparado o ambiente. Os testes não precisam de login cloud; o build
precisa de acesso aos registries e a execução Spark baixa os JARs do Delta.

## Retomada da integração em 9 de setembro de 2026

Os registros locais posteriores aos testes mostram tentativas de provisionamento:

- Databricks: o log de apply registra sucesso, com 10 recursos adicionados e 2
  alterados, e outputs dos jobs AWS e Azure. O plano posterior indicava alterações
  em dois jobs; a convergência ainda precisa ser conferida.
- AWS: o log de apply termina durante a criação do bucket, sem confirmação de
  conclusão. O diagnóstico atual com `--clouds both` interrompe na configuração
  ausente `aws.bucket`.
- Azure: o log de apply registra `403 AuthorizationFailed` na leitura do Resource
  Group. É necessário verificar a identidade e suas permissões na assinatura.
- Airflow: `docker compose ps` confirmou os sete serviços persistentes ativos;
  API server, scheduler, PostgreSQL e Redis reportaram estado saudável. A porta
  publicada neste ambiente é `http://localhost:8081`. Isso não comprova login na
  UI ou execução de tarefas.

## Autenticação AWS confirmada após a configuração SSO

O perfil `airflow-dev` foi salvo no volume de autenticação Docker, com região
`us-east-1`. `aws sts get-caller-identity` confirmou o usuário SSO `mateus` usando
`PowerUserAccess`. `s3api head-bucket` confirmou acesso ao bucket do projeto e
sua região, com verificação da conta proprietária esperada.

A consulta `iam get-role` retornou `AccessDenied` para a role Glue do projeto.
Foi preparado o arquivo local `.runtime/aws-deploy-iam-policy.json` com permissões
complementares limitadas à role Glue e à policy runtime; `iam:PassRole` fica
restrito ao serviço Glue. A política foi posteriormente adicionada ao permission set pelo usuário; veja o resultado do provisionamento abaixo.
A autenticação bem-sucedida não comprova a conclusão do provisionamento.

## Provisionamento AWS concluído após a atribuição IAM

A leitura IAM passou a retornar `NoSuchEntity` para a role Glue, confirmando que
ela ainda não existia e que a negação de acesso anterior havia sido resolvida.
Não havia processo Terraform ativo. O plano adquiriu o lock normalmente.

O bucket existente pertencia à conta autenticada, mas sua entrada no state não
continha instâncias. Ele foi importado com sucesso, preservando o recurso.
O plano revisado criou 12 recursos/configurações e adicionou as tags Project e
Environment ao bucket. O apply terminou com `12 added, 1 changed, 0 destroyed`.
Foram provisionados Glue job/crawler/database, IAM, Athena, proteções do S3 e os
dois scripts de processamento. Nenhum job ou consulta foi disparado nesta etapa.

A verificação posterior com `terraform plan -detailed-exitcode` retornou código 0
com `No changes`. Os logs locais estão em `.runtime/aws-plan-resume.log`,
`.runtime/aws-apply-resume.log` e `.runtime/aws-verify-resume.log`.

`python scripts/export_config.py --clouds aws` exportou a configuração AWS e
Databricks para o Airflow. `doctor.py --clouds aws` confirmou autenticação e leitura
AWS, mas terminou com código 1 por falha de autenticação Databricks (`ValueError`).
É necessário concluir o OAuth Databricks no volume Docker antes da DAG AWS.
O runner local `.runtime/aws_terraform.py` utilizou credenciais temporárias SSO
somente no ambiente do subprocesso Terraform, sem gravá-las em arquivos.

## OAuth Databricks concluído

O callback OAuth retornado pelo Chrome inclui uma barra raiz em `localhost:8020/`.
O auxiliar foi ajustado para aceitar essa forma equivalente e a imagem Airflow foi
reconstruída. O perfil `airflow-dev` ficou válido; `databricks auth token` passou.
O diagnóstico confirmou acesso aos catálogos e volumes `aws-airflow-gold` e
`azure-airflow-gold`. A leitura não comprova execução ou escrita dos jobs.
## Ainda não comprovado

Continuam pendentes o login Azure no Docker e o processamento do ramo Azure, o login
na UI Airflow e os workflows no GitHub Actions. O ramo AWS concluiu a execução
fim a fim em 10 de setembro, conforme as evidências abaixo.

Para Azure, conclua o login pelo navegador no serviço auth e execute o diagnóstico antes da DAG.

## Retomada em 10 de setembro de 2026

`doctor.py --clouds aws` terminou com código 0: autenticação/leitura AWS e acesso
ao catálogo e volume Databricks AWS confirmados. O SDK registrou timeout ao detectar
a versão da CLI Databricks, mas o diagnóstico de acesso concluiu com sucesso.
Os sete serviços persistentes estavam ativos, com a UI em `http://localhost:8081`.
A consulta ao banco Airflow mostrou a DAG pausada e sem execuções anteriores;
`airflow dags list-import-errors -o json` retornou uma lista vazia.

A leitura do Resource Group Azure voltou a retornar `403 AuthorizationFailed`
para `Microsoft.Resources/subscriptions/resourcegroups/read`. O bloqueio de
permissões Azure permanece; nenhum provisionamento Azure foi repetido nesta etapa.

### Execução AWS concluída

A DAG `multi_cloud_data_pipeline` terminou com estado `success` para
`manual__resume_2026_09_10_aws`, com `clouds=aws` e `load_date=2026-09-10`.
Início: 06:06:30 UTC; término: 06:14:11 UTC (03:06:30–03:14:11 em São Paulo).

- `prepare` passou na segunda tentativa após um timeout da API interna Airflow.
- Todas as seis tarefas AWS e `complete` passaram; as quatro tarefas Azure foram
  puladas conforme o parâmetro da execução.
- Glue: `jr_7978fa343c05223da12fafe8e79b83dc1dd83350d21673beac6b06ce70bcab69`.
- A transferência da Silver para o volume Databricks passou com verificação de hashes.
- Athena retornou **1.000 linhas**, consulta `f21cb395-92d8-42c1-a7c5-5a41e2121cee`,
  tabela `snapshot_attempt_4c2003ae48a743aca6f0b296fa9432ed`.
- Databricks: execução `879387396403243` terminou em `TERMINATED/SUCCESS`.
  Silver (`1026283594823670`) e Gold (`97998841150143`) também tiveram `SUCCESS`.

Os estados e o resultado Athena foram conferidos no banco de metadados Airflow;
os resultados Silver/Gold foram confirmados pela API de Jobs Databricks.
A DAG permanece habilitada e sem agendamento automático (`schedule=None`).

## Correção de acesso e provisionamento Azure em 10 de setembro de 2026

O login anterior usava um service principal em outra assinatura. O login de usuário
confirmou a assinatura `6952c881-dbd8-4d45-9a51-2f91c4a5a7a6` e a função Owner.
O tenant correto é `90f1a335-5b30-40b6-bfc3-69b0275a63b1`; o Object ID do usuário
configurado para deploy/Airflow é `6bb745f5-1b94-41b1-a2bd-0a21cf4d7147`.
As variáveis locais foram atualizadas. O state anterior não continha recursos
Azure gerenciados, apenas o data source de identidade.

O fluxo de device code retornou `AADSTS530035` por security defaults. O login pelo
navegador no Windows concluiu sem desabilitar as proteções do diretório.

O primeiro plano criou cinco recursos, mas o Key Vault falhou com
`MissingSubscriptionRegistration`. Após registrar `Microsoft.KeyVault`, um novo
plano criou somente o cofre, com `1 added, 0 changed, 0 destroyed`.
Os seis recursos Azure foram provisionados: Resource Group, Storage Account com
ADLS Gen2, filesystem Bronze, Key Vault e duas atribuições de acesso a dados.
`export_config.py --clouds both` exportou os outputs para o Airflow.

Logs locais: `.runtime/azure-plan-correct-subscription.log`,
`.runtime/azure-apply-correct-subscription.log`, `.runtime/azure-plan-keyvault.log`
e `.runtime/azure-apply-keyvault.log`.

O login Windows não autentica o Docker. Foi aberta uma janela interativa com
`.runtime/login-azure-docker.ps1` para autenticar a mesma conta no volume do Airflow.
A execução fim a fim Azure ainda depende da conclusão desse login e do diagnóstico.

A verificação final com `terraform plan -detailed-exitcode` retornou código 0 e
`No changes`. Evidência: `.runtime/azure-verify-correct-subscription.log`.

## Execução Azure concluída em 12 de setembro de 2026

A execução anterior `manual__resume_2026_09_10_azure` havia falhado apenas em
`azure.databricks`: Bronze e transferência passaram, mas o notebook Silver remoto
lançou `TypeError: can only concatenate str (not "Row") to str`. O código local já
continha a correção `json.dumps(counts.first().asDict())`; ela foi publicada com
`terraform apply` no Databricks (`0 added, 5 changed, 0 destroyed`).

`doctor.py --clouds azure` confirmou autenticação e leitura Azure, além de acesso
ao catálogo e volume Databricks. A DAG `multi_cloud_data_pipeline` terminou em
`success` para `manual__resume_2026_09_12_azure`, com `clouds=azure` e
`load_date=2026-09-12`. Início: 00:06:50 UTC de 13/09; término: 00:10:50 UTC.
`prepare` passou na segunda tentativa; Bronze, transferência, Databricks e
`complete` passaram. As tarefas AWS foram puladas pelo parâmetro da execução.

O job Databricks `624511401574731` terminou em `TERMINATED/SUCCESS`:
Silver (`191481089344987`) e Gold (`489695532168371`) tiveram `SUCCESS`.
A ordem dos blocos de tarefa no Terraform foi alinhada à ordem retornada pelo
provider; `terraform fmt -check main.tf` passou e o plano final retornou
`No changes`. O login na UI e os workflows GitHub Actions ainda não foram
validados nesta retomada.

## Login da UI e verificação local de CI em 12 de setembro de 2026

O formulário FAB em `http://localhost:8081/auth/login/` aceitou o usuário admin
com a senha do `.env` local. O POST redirecionou para `/`, que respondeu 200;
na mesma sessão, `/auth/login/` também redirecionou para `/`. Isso confirma o
login HTTP da UI, sem depender de inspeção visual no navegador.

Os workflows `ci.yml` e `infra.yml` foram lidos como YAML válido. Os passos
locais de CI executados nesta retomada passaram: Ruff, 13 testes unitários,
scanner de arquivos sensíveis, 14 testes Airflow, cinco testes Spark/Delta,
`terraform fmt -check -recursive terraform` e `terraform validate` nas cinco
raízes. Para isso, foi corrigida a ordem dos imports em `utils/databricks.py`
e formatado o `terraform/azure/terraform.tfvars` local.

Não houve execução hospedada do GitHub Actions: este diretório ainda não possui
commits nem remote Git. `gh repo view` confirmou ausência de remotos. O passo
Gitleaks em modo `git`, builds de imagem do workflow e o deploy OIDC do workflow
Infrastructure não foram executados nesta retomada. O deploy continua
condicionado a `ENABLE_INFRA_CD=true` e à preparação documentada em `ci-cd.md`.
