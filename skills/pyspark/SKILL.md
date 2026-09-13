---
name: pyspark
description: Orientar alterações de pyspark no projeto Airflow multicloud.
---

# Objetivo
Manter as decisões desta área compatíveis com a implementação didática.

# Quando usar
Ao alterar código ou documentação de pyspark neste repositório.

# Regras e padrões
Schemas reais em spark/common.py. Left joins por passenger_id e airport_id. Remover duplicatas idênticas; rejeitar conflitos de chave. amount decimal, booking_date date. Gold por carga/data/aeroporto; replaceWhere por load_date.

# O que evitar
Não ampliar a implantação além da tarefa autorizada. Não copiar credenciais dos exemplos locais.

# Checklist
- Consultar docs/ e os testes da área.
- Preservar as regras acima e validar o comportamento alterado.

