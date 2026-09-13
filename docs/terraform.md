# Terraform

As raízes aws, azure e databricks são independentes. Inicialmente usam state local
ignorado pelo Git. Não executar duas operações simultâneas sobre o mesmo state.
Versionar .terraform.lock.hcl; nunca versionar .terraform, states, planos e tfvars reais.

Cada raiz segue o mesmo fluxo:

```powershell
terraform -chdir=terraform/aws init
terraform fmt -check -recursive terraform
terraform -chdir=terraform/aws validate
terraform -chdir=terraform/aws plan -out=deployment.tfplan
terraform -chdir=terraform/aws apply deployment.tfplan
```

Substitua aws por azure/databricks. Os arquivos *.example devem ser copiados e editados.
Plan/apply exigem autenticação real; fmt/validate não provisionam recursos.

## Bootstrap e migração de state

Depois da primeira criação local, prepare terraform/bootstrap/aws. Ele cria um bucket
privado criptografado e versionado, OIDC GitHub e uma role com acesso ao state. Se já
houver provider GitHub na conta, passe oidc_provider_arn. A trust policy restringe
o repositório exato e o Environment terraform-dev.

deployment_policy_arns recebe policies de provisionamento aprovadas na conta.
Não reutilize a policy runtime do Airflow: faltariam criação/destruição/IAM. Deixe CD
desabilitado até anexar as permissões de deploy restritas aos recursos do projeto.
A role sem essas policies continua útil para o backend Azure, armazenado no S3.

```powershell
Copy-Item terraform/bootstrap/aws/terraform.tfvars.example terraform/bootstrap/aws/terraform.tfvars
# Configure repositório, sufixo, provider existente se necessário e policies de deploy.
terraform -chdir=terraform/bootstrap/aws init
terraform -chdir=terraform/bootstrap/aws plan
terraform -chdir=terraform/bootstrap/aws apply
python scripts/remote_backend.py aws --bucket <BUCKET-STATE> --region us-east-1
terraform -chdir=terraform/aws init -migrate-state -backend-config=state.backend.hcl
```

Repita migração para azure/databricks, cada qual com key diferente. Confirme a cópia
no S3 antes de limpar cópias locais de state. O state de bootstrap permanece local
com backup privado: seu bucket não depende do próprio backend. Não o destrua enquanto
existirem states dependentes. CI nunca migra state: deve encontrar o state já remoto.

Azure bootstrap é aplicado após o Resource Group principal existir. Cria managed
identity com federação e permissões Contributor, RBAC Administrator e Data Owner
somente nesse RG. Configure e aplique terraform/bootstrap/azure localmente. Essa
identidade não pode criar outros Resource Groups ou recriar o RG depois de destruído.

## Destruição

Pause a DAG, espere/cancele jobs e preserve dados que desejar manter. Ordem:

1. Remova tabelas gerenciadas e arquivos dos volumes do projeto no Databricks após
   revisar seus nomes; depois `terraform -chdir=terraform/databricks destroy`.
   Catálogos/schemas não vazios podem recusar remoção; não usamos force_destroy.
2. `terraform -chdir=terraform/bootstrap/azure destroy` remove a identidade CI antes do RG.
3. `terraform -chdir=terraform/azure destroy` remove Storage/RG/cofre do laboratório.
   Key Vault possui soft delete; o nome pode permanecer reservado por 7 dias.
4. Esvazie somente o bucket de dados do projeto pelo console S3 e execute
   `terraform -chdir=terraform/aws destroy`. Bucket não vazio é protegido por padrão.
5. Preserve bootstrap AWS e state até concluir a remoção e guardar evidências.
   Remoção definitiva do backend exige procedimento explícito e revisão do prevent_destroy.
6. `docker compose down` desliga o laboratório local.

Jobs Glue/serverless só são disparados pela DAG; não há schedules Terraform.
Mesmo com compute parado, armazenamento, logs, resultados Athena e transferência
podem gerar custo. Remova tentativas antigas apenas após confirmar que não são o
snapshot atual do crawler nem a entrada de job em andamento.
