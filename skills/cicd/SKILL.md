---
name: cicd
description: Orientar alterações de cicd no projeto Airflow multicloud.
---

# Objetivo
Manter as decisões desta área compatíveis com a implementação didática.

# Quando usar
Ao alterar código ou documentação de cicd neste repositório.

# Regras e padrões
PR sem apply; forks sem identidade cloud. CI executa Python, DAG e Terraform. CD precisa remote state, OIDC e Environment protegido; executar só por opt-in. Databricks local via OAuth até suporte de federação verificado.

# O que evitar
Não ampliar a implantação além da tarefa autorizada. Não copiar credenciais dos exemplos locais.

# Checklist
- Consultar docs/ e os testes da área.
- Preservar as regras acima e validar o comportamento alterado.

