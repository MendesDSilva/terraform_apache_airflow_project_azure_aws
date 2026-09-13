---
name: azure
description: Orientar alterações de azure no projeto Airflow multicloud.
---

# Objetivo
Manter as decisões desta área compatíveis com a implementação didática.

# Quando usar
Ao alterar código ou documentação de azure neste repositório.

# Regras e padrões
ADLS Gen2 com HNS e RBAC. Bronze CSV; Airflow transfere do ADLS para volume Databricks. Key Vault pode ficar vazio quando identidades bastam. Não usar chaves de Storage.

# O que evitar
Não ampliar a implantação além da tarefa autorizada. Não copiar credenciais dos exemplos locais.

# Checklist
- Consultar docs/ e os testes da área.
- Preservar as regras acima e validar o comportamento alterado.

