# GitHub Actions

CI executa em PR e push main: Ruff, pytest, scanner de arquivos sensíveis, Gitleaks,
import/topologia Airflow dentro da imagem, Spark/Delta separado, fmt e validate nas
cinco raízes Terraform. Não usa credenciais cloud e funciona em forks.

O workflow Infrastructure usa workflow_dispatch ou conclusão bem-sucedida do CI na main e começa desabilitado.
Antes de definir ENABLE_INFRA_CD=true:

1. Conclua primeiro apply local e migração dos states AWS/Azure para S3.
2. Aplique os bootstraps e confira policies de deploy AWS; o acesso ao state sozinho
   não permite criar infraestrutura.
3. Crie Environment `terraform-dev`, restrito a main, com required reviewers.
   Se o plano GitHub não permitir proteção, mantenha CD desabilitado e aplique localmente.
4. Cadastre as Variables abaixo no Environment e ENABLE_INFRA_CD no repositório.

| Variable | Valor |
|---|---|
| AWS_DEPLOY_ROLE_ARN | Output github_role_arn do bootstrap AWS |
| AWS_REGION | Região AWS/backend |
| TF_STATE_BUCKET | Output state_bucket |
| PROJECT_SUFFIX | Mesmo sufixo dos recursos aplicados |
| AZURE_CLIENT_ID | Client ID da managed identity CI |
| AZURE_TENANT_ID | Tenant ID |
| AZURE_SUBSCRIPTION_ID | Assinatura configurada |
| AZURE_LOCATION | Região Azure aplicada |
| AZURE_AIRFLOW_PRINCIPAL_ID | Object ID do usuário Airflow |

OIDC substitui credenciais permanentes. O workflow usa uma matriz AWS/Azure sequencial,
com concurrency global que não cancela apply em andamento. Workflow dispatch permite
selecionar uma raiz e gerar somente plan; CI aprovado na main libera plan e apply da mesma revis?o do mesmo arquivo
após a proteção do Environment. Planos não são publicados como artefatos: podem conter
dados sensíveis. Nenhum conteúdo de PR é interpolado diretamente em comandos shell.

Não há plan autenticado automático em PR nesta primeira versão. Isso evita conceder
identidade a código não revisado e mantém o fluxo explicável. Para estudar plan use
workflow_dispatch na main. Não adicionar pull_request_target com checkout do PR.

Databricks Free Edition permanece provisionado localmente via OAuth U2M. A federação
de conta não foi comprovada; não armazenamos PAT em GitHub Secrets como substituição.
Alterações em notebooks exigem terraform apply da raiz databricks depois da revisão.

As permissões RBAC do Azure CI ficam no RG existente. Destroy de laboratório continua
local, seguindo a ordem documentada. A primeira implantação também continua local.
