FROM apache/airflow:3.3.1-python3.11
USER root
RUN apt-get update && apt-get install -y --no-install-recommends unzip \
    && rm -rf /var/lib/apt/lists/*
# CLIs isoladas evitam conflitos entre Azure CLI e as dependências do Airflow.
RUN python -m venv /opt/azure-cli \
    && /opt/azure-cli/bin/pip install --no-cache-dir azure-cli==2.90.0 \
    && ln -s /opt/azure-cli/bin/az /usr/local/bin/az
ARG AWS_CLI_VERSION=2.34.0
ARG DATABRICKS_CLI_VERSION=1.15.0
RUN curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-${AWS_CLI_VERSION}.zip" -o /tmp/aws.zip \
    && unzip -q /tmp/aws.zip -d /tmp && /tmp/aws/install \
    && rm -rf /tmp/aws /tmp/aws.zip \
    && curl -fsSL "https://github.com/databricks/cli/releases/download/v${DATABRICKS_CLI_VERSION}/databricks_cli_${DATABRICKS_CLI_VERSION}_linux_amd64.zip" -o /tmp/db.zip \
    && unzip -q /tmp/db.zip -d /tmp/db \
    && install /tmp/db/databricks /usr/local/bin/databricks && rm -rf /tmp/db /tmp/db.zip
USER airflow
COPY requirements.txt requirements-dev.txt /opt/airflow/
RUN pip install --no-cache-dir "apache-airflow==3.3.1" -r requirements.txt \
    --constraint https://raw.githubusercontent.com/apache/airflow/constraints-3.3.1/constraints-3.11.txt \
    && pip install --no-cache-dir -r requirements-dev.txt
COPY --chown=airflow:root utils /opt/airflow/utils
COPY --chown=airflow:root dags /opt/airflow/dags
COPY --chown=airflow:root tests /opt/airflow/tests
COPY --chown=airflow:root --chmod=755 scripts /opt/airflow/scripts
ENV PYTHONPATH=/opt/airflow
