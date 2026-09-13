---
name: security
description: Orientar alterações de security no projeto Airflow multicloud.
---

# Objetivo
Manter as decisões desta área compatíveis com a implementação didática.

# Quando usar
Ao alterar código ou documentação de security neste repositório.

# Regras e padrões
Sem credenciais/state no Git, logs ou XCom. SSO AWS, Azure CLI e OAuth Databricks em caches Docker privados. OIDC para CI AWS/Azure. Não assumir federação na Free Edition. Não conceder acesso a contas inteiras quando recurso pode ser delimitado.

# O que evitar
Não ampliar a implantação além da tarefa autorizada. Não copiar credenciais dos exemplos locais.

# Checklist
- Consultar docs/ e os testes da área.
- Preservar as regras acima e validar o comportamento alterado.

