---
name: airflow
description: Orientar alterações de airflow no projeto Airflow multicloud.
---

# Objetivo
Manter as decisões desta área compatíveis com a implementação didática.

# Quando usar
Ao alterar código ou documentação de airflow neste repositório.

# Regras e padrões
Use Airflow 3.3.1 e airflow.sdk. Importe clientes somente durante tasks. AWS/Azure independentes; XCom contém metadados. Aguarde estados terminais com timeout. Uma execução ativa evita disputa por snapshots.

# O que evitar
Não ampliar a implantação além da tarefa autorizada. Não copiar credenciais dos exemplos locais.

# Checklist
- Consultar docs/ e os testes da área.
- Preservar as regras acima e validar o comportamento alterado.

