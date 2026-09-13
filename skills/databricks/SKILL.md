---
name: databricks
description: Orientar alterações de databricks no projeto Airflow multicloud.
---

# Objetivo
Manter as decisões desta área compatíveis com a implementação didática.

# Quando usar
Ao alterar código ou documentação de databricks neste repositório.

# Regras e padrões
Free Edition: catálogos aws-airflow-gold e azure-airflow-gold, schemas staging/silver/gold. Volumes gerenciados para arquivos, tabelas Delta fora dos volumes. Sem external locations, clusters clássicos ou APIs de conta. Validar permissões antes de implantação.

# O que evitar
Não ampliar a implantação além da tarefa autorizada. Não copiar credenciais dos exemplos locais.

# Checklist
- Consultar docs/ e os testes da área.
- Preservar as regras acima e validar o comportamento alterado.

