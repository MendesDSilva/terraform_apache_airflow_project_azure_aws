"""Login Azure no Docker com callback pelo navegador do host, sem copiar tokens."""
import argparse
import json
import subprocess
import sys
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

PREFIX = 'AZURE_BROWSER_LOOPBACK:'
if len(sys.argv) == 3 and sys.argv[1] == '--emit':
    print(PREFIX + sys.argv[2], flush=True)
    raise SystemExit(0)

FORWARD = r'''
import json, sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError
x = json.load(sys.stdin)
r = Request(x['url'], data=x['body'].encode() if x['method'] == 'POST' else None,
            headers={'Content-Type': x['content_type']}, method=x['method'])
try:
    response = urlopen(r, timeout=30)
except HTTPError as e:
    response = e
with response:
    print(json.dumps({'status': response.status,
                      'type': response.headers.get('Content-Type', 'text/html'),
                      'body': response.read().decode('utf-8')}))
'''
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tenant', required=True, type=uuid.UUID)
parser.add_argument('--subscription', required=True, type=uuid.UUID)
args = parser.parse_args()
project = Path(__file__).resolve().parents[1]
container = 'airflow-azure-browser-' + uuid.uuid4().hex[:8]
command = ['docker', 'compose', 'run', '--rm', '-T', '--no-deps', '--name', container,
           '-v', f'{Path(__file__).resolve().as_posix()}:/opt/airflow/scripts/azure_login.py:ro',
           '-e', 'BROWSER=python /opt/airflow/scripts/azure_login.py --emit %s',
           'auth', '-c',
           f'AZURE_CORE_LOGIN_EXPERIENCE_V2=off az login --tenant {args.tenant} --output none && '
           f'az account set --subscription {args.subscription} && '
           'python /opt/airflow/scripts/doctor.py --clouds azure']
server = None
process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, encoding='utf-8', errors='replace', cwd=project)
try:
    for line in process.stdout:
        if not line.startswith(PREFIX):
            print(line.rstrip(), flush=True)
            continue
        target = line[len(PREFIX):].strip()
        parts = urlsplit(target)
        if parts.scheme == 'https' and parts.hostname == 'login.microsoftonline.com':
            parts = urlsplit(parse_qs(parts.query).get('redirect_uri', [''])[0])
        if parts.scheme != 'http' or parts.hostname not in ('localhost', '127.0.0.1') or not parts.port:
            raise ValueError('Expected a loopback welcome page from Azure CLI')
        port = parts.port
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.forward()
            def do_POST(self):
                self.forward()
            def forward(self):
                if self.headers.get('Host') not in (f'localhost:{port}', f'127.0.0.1:{port}'):
                    self.send_error(400)
                    return
                if urlsplit(self.path).path not in ('', '/'):
                    self.send_error(404)
                    return
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 <= size <= 65536:
                    self.send_error(413)
                    return
                payload = {'url': f'http://localhost:{port}' + self.path,
                           'method': self.command,
                           'content_type': self.headers.get('Content-Type', 'application/x-www-form-urlencoded'),
                           'body': self.rfile.read(size).decode('utf-8') if size else ''}
                try:
                    result = subprocess.run(['docker', 'exec', '-i', container, 'python', '-c', FORWARD],
                                            input=json.dumps(payload), capture_output=True, text=True, timeout=40)
                    result.check_returncode()
                    answer = json.loads(result.stdout)
                    body = answer['body'].encode('utf-8')
                    self.send_response(answer['status'])
                    self.send_header('Content-Type', answer['type'])
                    self.send_header('Content-Length', str(len(body)))
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    self.wfile.write(body)
                except Exception:
                    self.send_error(502, 'Azure login callback could not be delivered')
        server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print('Abrindo login Azure no navegador. Nao e necessario copiar URLs.', flush=True)
        webbrowser.open(target)
    raise SystemExit(process.wait())
finally:
    if server:
        server.shutdown()
        server.server_close()
    if process.poll() is None:
        subprocess.run(['docker', 'stop', container], capture_output=True, timeout=30)
        process.wait(timeout=30)