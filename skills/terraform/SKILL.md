---
name: terraform
description: Orientar alterações de terraform no projeto Airflow multicloud.
---

# Objetivo
Manter as decisões desta área compatíveis com a implementação didática.

# Quando usar
Ao alterar código ou documentação de terraform neste repositório.

# Regras e padrões
Raízes aws/azure/databricks e bootstrap separado. Fixar providers e versionar locks. State local inicialmente; migrar para S3 com locking antes do CD. Nunca provisionar para validar sintaxe.

# O que evitar
Não ampliar a implantação além da tarefa autorizada. Não copiar credenciais dos exemplos locais.

# Checklist
- Consultar docs/ e os testes da área.
- Preservar as regras acima e validar o comportamento alterado.

