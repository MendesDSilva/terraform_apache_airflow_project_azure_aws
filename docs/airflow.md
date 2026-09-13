# Airflow local

O Compose usa CeleryExecutor, Redis, PostgreSQL, API server, scheduler, DAG processor,
worker e triggerer. Serviços sem necessidade no laboratório, como Flower, foram omitidos.
Somente a UI expõe porta, vinculada a 127.0.0.1. PostgreSQL/Redis ficam na rede Docker.

```powershell
python scripts/local_setup.py
docker compose build airflow-apiserver
docker compose up airflow-init
docker compose up -d
docker compose ps
docker compose logs --tail 100 airflow-scheduler airflow-dag-processor
```

Na UI, abra multi_cloud_data_pipeline, habilite e use Trigger DAG:

```json
{"clouds": "both", "load_date": "2025-06-30"}
```

Sem load_date, a DAG usa a data UTC do início da execução, registrada na task prepare.
Use data explícita para reproduzir uma carga. Somente uma execução pode estar ativa.
clouds=aws/azure pula o outro ramo; falhas em um ramo não impedem o outro de começar.
O marcador final não mascara falhas anteriores.

## Configuração

scripts/local_setup.py cria .env sem sobrescrever um existente. Senhas são aleatórias.
scripts/export_config.py exporta apenas pipeline_config, nunca outputs sensíveis.
Não inspecione `docker compose config` sem --quiet em gravações: ele interpola segredos.

O worker executa no máximo duas tarefas concorrentes. Downloads têm timeout e limite
de 20 MiB por arquivo. Glue e Databricks têm timeout de 40 minutos; Athena 5 minutos,
Crawler 15 minutos. Timeout Glue/Databricks/Athena solicita cancelamento. Em timeout
do crawler, verifique seu estado antes de repetir. Não há polling infinito.

Dois retries com backoff cobrem falhas transitórias; ValueError de contrato vira
AirflowFailException sem retry. Não há cliente cloud no import da DAG. XCom contém
somente metadados; cada tarefa baixa, envia e descarta seus próprios arquivos.

## Testes

```powershell
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest tests/unit -q
docker compose run --rm --no-deps test
docker compose build spark-test
docker compose run --rm --no-deps spark-test
```

Os testes Spark usam Java/Delta dentro de imagem própria, sem instalar Spark no Airflow.
A primeira execução precisa baixar dependências Maven do Delta; as seguintes podem
repetir o download em containers efêmeros.

`docker compose down` preserva volumes. `docker compose down --volumes` também apaga
metadata, logs e sessões de autenticação deste projeto; use somente quando quiser
recomeçar o laboratório. Isso não apaga objetos em AWS/Azure/Databricks.

## Porta local

A porta padrão é 8080. Se estiver ocupada, defina AIRFLOW_PORT=8081 no .env
e execute docker compose up -d. Nesse caso, abra http://localhost:8081.
