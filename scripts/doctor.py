"""Verificação somente leitura; rode no serviço auth após os logins."""
import argparse
import sys

from utils.config import CATALOGS, read_config, validate_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clouds", choices=["aws", "azure", "both"], default="both")
    parser.add_argument("--databricks-only", action="store_true")
    args = parser.parse_args()
    selected = ["aws", "azure"] if args.clouds == "both" else [args.clouds]
    errors = []
    if not args.databricks_only:
        config = read_config()
        validate_config(config, args.clouds)
        for cloud in selected:
            try:
                if cloud == "aws":
                    from utils.aws import client
                    client("sts", config[cloud]).get_caller_identity()
                    client("s3", config[cloud]).head_bucket(Bucket=config[cloud]["bucket"])
                else:
                    from utils.azure import filesystem
                    filesystem(config[cloud]).get_file_system_properties()
                print(cloud + ": autenticação e leitura OK")
            except Exception as exc:
                errors.append(f"{cloud}: {type(exc).__name__}; renove login/verifique RBAC")
    try:
        from utils.databricks import workspace
        ws = workspace()
        ws.current_user.me()
        names = {catalog.name for catalog in ws.catalogs.list()}
        for cloud in selected:
            catalog = CATALOGS[cloud]
            if catalog in names:
                ws.volumes.read(f"{catalog}.staging.inbound")
                print(f"{catalog}: catálogo e volume acessíveis")
            else:
                print(f"{catalog}: ainda não criado; CREATE CATALOG deve ser confirmado")
        print("Databricks: login/listagem OK. Leitura não comprova privilégios de escrita/jobs.")
    except Exception as exc:
        errors.append(f"Databricks: {type(exc).__name__}; renove OAuth/verifique permissões")
    for error in errors:
        print(error, file=sys.stderr)
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
