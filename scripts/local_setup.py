"""Gera somente configuração local; não imprime os segredos."""
import base64
import json
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    env = ROOT / ".env"
    if not env.exists():
        sample = (ROOT / ".env.example").read_text(encoding="utf-8")
        values = {
            "POSTGRES_PASSWORD": secrets.token_hex(24),
            "FERNET_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
            "JWT_SECRET": secrets.token_hex(32),
            "AIRFLOW_ADMIN_PASSWORD": secrets.token_urlsafe(24),
        }
        env.write_text(sample + "\n" + "\n".join(f"{k}={v}" for k, v in values.items()) + "\n",
                       encoding="utf-8")
        env.chmod(0o600)
    config = runtime / "config.json"
    if not config.exists():
        config.write_text(json.dumps({"source_revision":
            "42efa594aaf3ef5b24877c7b61f1c1d7abc280cc"}, indent=2), encoding="utf-8")
    print("Configuração local pronta. Login admin; senha em .env (AIRFLOW_ADMIN_PASSWORD).")


if __name__ == "__main__":
    main()
