"""Barreira simples para arquivos rastreados; CI também usa Gitleaks."""
import re
import subprocess
from pathlib import Path


def main():
    paths = subprocess.check_output([
        "git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"
    ]).decode().split("\0")
    forbidden = []
    for name in filter(None, paths):
        path = Path(name)
        if name.endswith(".example"):
            continue
        if (path.name == ".env" or ".tfstate" in name or path.suffix in (".pem", ".key", ".tfvars")
                or any(part in (".aws", ".azure", ".runtime") for part in path.parts)):
            forbidden.append(name)
        if path.is_file() and path.stat().st_size < 1024 * 1024:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"\bAKIA[A-Z0-9]{16}\b|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----", text):
                forbidden.append(name)
    if forbidden:
        raise SystemExit("Arquivos sensíveis: " + ", ".join(sorted(set(forbidden))))
    print("Nenhum arquivo proibido rastreado.")


if __name__ == "__main__":
    main()
