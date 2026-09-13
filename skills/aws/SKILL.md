---
name: aws
description: Orientar alterações de aws no projeto Airflow multicloud.
---

# Objetivo
Manter as decisões desta área compatíveis com a implementação didática.

# Quando usar
Ao alterar código ou documentação de aws neste repositório.

# Regras e padrões
Bronze CSV imutável por revisão; Glue produz Parquet por tentativa. Crawler aponta somente a tentativa confirmada. IAM restrito a recursos do projeto; transferência lê a Silver real no S3.

# O que evitar
Não ampliar a implantação além da tarefa autorizada. Não copiar credenciais dos exemplos locais.

# Checklist
- Consultar docs/ e os testes da área.
- Preservar as regras acima e validar o comportamento alterado.

