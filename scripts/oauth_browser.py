#!/usr/bin/env python
"""Callback OAuth em container sem expor porta ou copiar cache Windows."""
import getpass
import sys
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen


def validated_callback(authorization_url, callback):
    target = parse_qs(urlsplit(authorization_url).query).get("redirect_uri", [""])[0]
    expected, actual = urlsplit(target), urlsplit(callback)
    expected_path = expected.path or "/"
    actual_path = actual.path or "/"
    if (expected.scheme != "http" or expected.hostname not in ("localhost", "127.0.0.1")
            or (actual.scheme, actual.netloc, actual_path) !=
            (expected.scheme, expected.netloc, expected_path)):
        raise ValueError("Callback deve corresponder ao localhost da URL OAuth original")
    if not parse_qs(actual.query).get("code") or not parse_qs(actual.query).get("state"):
        raise ValueError("Callback sem code/state; conclua o login no navegador")
    return callback


def main():
    authorization_url = sys.argv[1]
    print("Abra esta URL no navegador do host:\n" + authorization_url, flush=True)
    print("Após autorizar, o navegador pode falhar ao abrir localhost. Copie a URL final\n"
          "da barra de endereço e cole abaixo. Ela contém um código temporário; não a compartilhe.",
          flush=True)
    callback = getpass.getpass("URL final (entrada oculta): ").strip()
    validated_callback(authorization_url, callback)
    # A CLI escuta dentro deste mesmo container. Não encaminhamos para hosts externos.
    with urlopen(callback, timeout=30) as response:
        response.read()
    print("Callback entregue à CLI.")


if __name__ == "__main__":
    main()
