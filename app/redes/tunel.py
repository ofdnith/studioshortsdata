"""URL pública temporária para UM arquivo (o Instagram baixa o vídeo de uma URL).

Sobe um servidor HTTP mínimo numa porta local que só serve o arquivo pedido, num caminho
aleatório, e abre um túnel rápido do cloudflared para ele. O app em si (porta 8000) nunca é
exposto. Tudo é encerrado ao sair do `with`.
"""

import re
import secrets
import shutil
import subprocess
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx


class ErroTunel(Exception):
    pass


def cloudflared_instalado() -> bool:
    return shutil.which("cloudflared") is not None


@contextmanager
def url_publica(arquivo: Path, log=print, espera_s: int = 40):
    if not cloudflared_instalado():
        raise ErroTunel("cloudflared não está instalado (brew install cloudflared).")
    arquivo = Path(arquivo)
    caminho = f"/{secrets.token_urlsafe(24)}/{arquivo.name}"
    tamanho = arquivo.stat().st_size

    class Handler(BaseHTTPRequestHandler):
        def _ok(self, corpo: bool):
            if self.path != caminho:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(tamanho))
            self.end_headers()
            if corpo:
                with open(arquivo, "rb") as f:
                    shutil.copyfileobj(f, self.wfile)

        def do_GET(self):
            self._ok(True)

        def do_HEAD(self):
            self._ok(False)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    porta = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    proc = subprocess.Popen(["cloudflared", "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{porta}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        base, registrado = None, False
        fim = time.time() + espera_s
        while time.time() < fim and not registrado:
            linha = proc.stdout.readline()
            if not linha and proc.poll() is not None:
                break
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", linha)
            if m and not base:
                base = m.group(0)
            if base and "Registered tunnel connection" in linha:
                registrado = True
        if not base or not registrado:
            raise ErroTunel("O túnel do cloudflared não conectou a tempo.")
        # drena a saída do cloudflared para o processo não travar
        threading.Thread(target=lambda: [None for _ in proc.stdout], daemon=True).start()
        url = base + caminho
        host = base.removeprefix("https://")
        # confere o DNS público (DNS-over-HTTPS), sem contaminar o cache de DNS do Mac
        for _ in range(30):
            try:
                r = httpx.get("https://cloudflare-dns.com/dns-query", params={"name": host, "type": "A"},
                              headers={"accept": "application/dns-json"}, timeout=8)
                if r.json().get("Answer"):
                    break
            except (httpx.HTTPError, ValueError):
                pass
            time.sleep(2)
        else:
            raise ErroTunel("O endereço do túnel não apareceu no DNS público.")
        # teste local: só informativo (o DNS do Mac pode demorar a enxergar o endereço novo)
        try:
            ok = httpx.head(url, timeout=10).status_code == 200
        except httpx.HTTPError:
            ok = False
        log("túnel no ar" + ("" if ok else " (o teste local não alcançou o endereço; o Instagram baixa pelo DNS público)"))
        log("URL pública temporária pronta")
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        srv.shutdown()
        log("túnel encerrado")
