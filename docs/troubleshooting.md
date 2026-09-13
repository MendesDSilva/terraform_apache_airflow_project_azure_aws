# Troubleshooting

| Sintoma | Verificação / correção |
|---|---|
| Docker não conecta ao pipe | Inicie Docker Desktop e selecione containers Linux; execute docker info |
| Containers encerram/OOM | Aumente memória do Docker; execute Spark separado do Airflow |
| Delta: `does not support truncate in batch mode` nos testes | Use as versões fixadas em `requirements-spark.txt` e reconstrua `docker compose build spark-test`; veja [validação](validation.md) |
| .env ausente | Execute python scripts/local_setup.py; ele não sobrescreve .env existente |
| UI não abre | docker compose ps; logs airflow-init e airflow-apiserver; confira porta 8080 |
| DAG não aparece | Logs do DAG processor; execute serviço test para importação |
| Configuração ausente aws/azure | Aplique a raiz necessária e exporte outputs com --clouds correto |
| SSO expirado | Repita aws sso login dentro do serviço auth, não apenas no Windows |
| Azure CLI não autenticado | az login --use-device-code dentro do auth; confira assinatura e Object ID |
| Azure 403 após apply | Aguarde propagação RBAC; confirme Data Owner/Contributor e repita operação |
| OAuth Databricks inválido | Renove login e confirme o profile airflow-dev no cache usado pelo container |
| Catálogo negado | Confirme CREATE CATALOG; administrador cria/concede objetos e depois importe Terraform |
| Free Edition atingiu cota | Aguarde liberação de compute; não aumente retries indefinidamente |
| Hash de transferência divergente | Não execute o job manualmente; repita transferência para nova tentativa |
| Crawler já executando | Aguarde READY e examine LastCrawl; não dispare concorrentes |
| Athena não encontra tabela | Use nome registrado pela task, database/workgroup dos outputs |
| Valores dobrados no Power BI | Filtre uma única load_date; as cargas são snapshots do mesmo CSV |
| Terraform provider timeout | Repita validate após confirmar recursos locais; não confundir com erro de credencial |
| ResourceAlreadyExists | Importe apenas recursos pertencentes ao projeto; não remova recursos existentes para contornar |
| Destroy recusa bucket/catálogo | Revise conteúdo e esvazie somente objetos do projeto; não habilite force_destroy global |

Não execute apply para resolver erros de lint/import. Não coloque tokens em prints
ou envie logs de configuração completos. Para diagnóstico, doctor.py é somente leitura
e informa quais verificações não comprovam autorização de escrita.
