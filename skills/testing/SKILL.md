---
name: testing
description: Orientar alterações de testing no projeto Airflow multicloud.
---

# Objetivo
Manter as decisões desta área compatíveis com a implementação didática.

# Quando usar
Ao alterar código ou documentação de testing neste repositório.

# Regras e padrões
Testar joins, métricas, idempotência, falhas de transferência e DAG sem credenciais. Spark separado do ambiente Airflow. Não executar jobs remotos durante testes locais.

# O que evitar
Não ampliar a implantação além da tarefa autorizada. Não copiar credenciais dos exemplos locais.

# Checklist
- Consultar docs/ e os testes da área.
- Preservar as regras acima e validar o comportamento alterado.

