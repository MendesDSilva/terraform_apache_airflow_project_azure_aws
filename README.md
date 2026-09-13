# Airflow multicloud: AWS + Azure + Databricks

Projeto didático de Engenharia de Dados: os mesmos CSVs públicos entram no S3 e no
ADLS Gen2. AWS Glue transforma a Silver AWS; Databricks produz Silver Azure e Gold
das duas origens. Airflow 3.3.1 coordena o pipeline; Terraform descreve a infraestrutura.

**Modo implementado: Databricks Free Edition com cópia para volumes gerenciados.**
Airflow transfere a Silver real do S3 e a Bronze real do ADLS ao Databricks. A Gold
fica no armazenamento gerenciado do workspace. O nome do catálogo indica a origem
dos dados, não o provedor onde os arquivos gerenciados estão fisicamente armazenados.

## Começar localmente

Pré-requisitos: Docker Desktop com containers Linux, Compose v2, Python 3.11 e
Terraform 1.10 ou superior (CI: 1.15.8). Reserve pelo menos 8 GB de RAM para Docker,
2 CPUs e espaço para imagens/volumes. A imagem das CLIs usa linux/amd64.

```powershell
git clone <URL-DO-SEU-REPOSITORIO>
cd <PASTA-CLONADA>
python scripts/local_setup.py
docker compose build airflow-apiserver spark-test
docker compose run --rm --no-deps test
docker compose run --rm --no-deps spark-test
docker compose up airflow-init
docker compose up -d
docker compose ps
```

Abra http://localhost:8080. Usuário `admin`; consulte `AIRFLOW_ADMIN_PASSWORD` no
arquivo `.env` local. A DAG começa pausada, sem exemplos e sem agendamento automático.
Os testes locais não precisam de contas cloud. Tarefas cloud exigem os recursos e
logins descritos abaixo; não há simulação apresentada como execução real.

## Preparar execução cloud posteriormente

1. [AWS](docs/setup-aws.md): SSO, Terraform, Glue e Athena.
2. [Azure](docs/setup-azure.md): ADLS, RBAC e Key Vault.
3. [Databricks](docs/setup-databricks.md): OAuth, permissões, volumes e jobs.
4. Exporte outputs: `python scripts/export_config.py --clouds both`.
5. Execute diagnóstico: `docker compose run --rm auth -c "python /opt/airflow/scripts/doctor.py --clouds both"`.
6. Na UI, habilite a DAG e dispare com `clouds` igual a `aws`, `azure` ou `both`,
   e `load_date` como `2025-06-30`, por exemplo.

É possível provisionar apenas uma cloud: escolha também o respectivo elemento em
`terraform/databricks/terraform.tfvars`, exporte somente essa cloud e use o mesmo
valor no parâmetro da DAG.

## O que estudar

| Diretório | Responsabilidade |
|---|---|
| `dags/` | Dependências, paralelismo, retries e parâmetros |
| `utils/` | Ingestão, autenticação dos clientes, transferências e polling |
| `spark/` | Contratos reais, limpeza, joins e métricas compartilhadas |
| `terraform/` | AWS, Azure, Databricks e bootstrap de CI/state |
| `tests/` | Contratos, falhas, topologia da DAG e snapshots Delta |
| `scripts/` | Setup, diagnóstico e exportação sem segredos |
| `skills/` | Orientações de manutenção por área |

Consulte [arquitetura](docs/architecture.md), [Airflow](docs/airflow.md),
[Terraform](docs/terraform.md), [CI/CD](docs/ci-cd.md),
[segurança](docs/security.md) e [troubleshooting](docs/troubleshooting.md).

## Desligar e evitar custos

`docker compose down` desliga o ambiente e preserva dados/logins locais.
Não remove recursos cloud. Glue, Crawler, Athena, Storage, Key Vault e transferência
de dados podem gerar cobrança. A Free Edition também possui cotas de execução.

Para remover recursos cloud, siga a [ordem de destruição](docs/terraform.md#destruição).
O bucket de state é protegido contra destruição acidental. Nunca publique `.env`,
`.runtime`, states ou arquivos reais de variáveis.

Esta entrega implementa e testa o projeto local. A execução fim a fim nas contas
depende de autenticação e permissões; consulte [validação](docs/validation.md) para
as evidências efetivamente obtidas.
