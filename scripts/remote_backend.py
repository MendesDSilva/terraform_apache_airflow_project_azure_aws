"""Cria configuração local ignorada para migração explícita do state."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", choices=["aws", "azure", "databricks"])
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "terraform" / args.root
    # json.dumps também produz strings HCL seguras para esses valores simples.
    import json
    (root / "backend.tf").write_text('terraform {\n  backend "s3" {}\n}\n', encoding="utf-8")
    values = {"bucket": args.bucket, "key": f"dev/{args.root}/terraform.tfstate", "region": args.region}
    text = "\n".join(f"{k} = {json.dumps(v)}" for k, v in values.items())
    (root / "state.backend.hcl").write_text(text + "\nencrypt = true\nuse_lockfile = true\n", encoding="utf-8")
    print(f"Execute terraform -chdir=terraform/{args.root} init -migrate-state -backend-config=state.backend.hcl")


if __name__ == "__main__":
    main()
