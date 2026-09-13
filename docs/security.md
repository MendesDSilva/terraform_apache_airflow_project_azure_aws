# Segurança e fronteiras de acesso

Segredos: .env, tokens OAuth, AWS SSO e Azure CLI ficam fora do Git. Senhas locais
são geradas aleatoriamente e não aparecem no README. .runtime contém configuração
de conta e permanece ignorado, embora exporte somente outputs públicos.

State Terraform é sensível mesmo quando outputs usam sensitive=true. Usar backend
privado, criptografado, versionado e com locking antes do CD. Não publicar planos,
states, crash logs ou caches como artefatos de workflow.

Airflow usa volume Docker privado auth-cache com diretório raiz 0700. Os serviços
Airflow compartilham a mesma identidade de laboratório; um usuário com controle do
Docker pode ler suas sessões. Não oferecer este Compose como ambiente multiusuário
ou produção. Faça logout e remova o volume ao terminar uma máquina compartilhada.

AWS: runtime policy separada do deploy, S3 privado/TLS, Glue assume sua role e não
recebe credenciais em argumentos. Azure: HNS, Entra ID e RBAC; shared access key
desabilitada. Key Vault vazio enquanto não houver segredo necessário.

Databricks: OAuth U2M e objetos separados por origem. A ponte não transporta segredos
para notebooks. Não usar DBFS root, mounts legados ou tokens Spark de Storage.
O usuário de deploy é dono dos objetos; compartilhar acesso exige grants específicos.

O scanner local verifica arquivos rastreados; Gitleaks complementa a detecção no CI.
Antes da primeira publicação, confira `git status --short` e execute
`python scripts/check_secrets.py` depois de selecionar os arquivos para o commit.
Nenhum scanner prova ausência absoluta de segredo: revise o diff antes de publicar.
