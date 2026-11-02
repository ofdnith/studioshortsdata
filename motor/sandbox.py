"""Roda comandos do motor dentro da caixa de areia do macOS (sandbox-exec).

Usado quando o roteiro tem código escrito pela IA (modo livre): o processo não acessa a rede
e só escreve na pasta do vídeo, no cache de voz e na pasta temporária do sistema.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def disponivel() -> bool:
    return shutil.which("sandbox-exec") is not None


def _perfil(pastas_escrita: list[Path]) -> str:
    regras = "".join(f'(allow file-write* (subpath "{Path(p).resolve()}"))\n' for p in pastas_escrita)
    tmp = Path(tempfile.gettempdir()).resolve()
    return f"""(version 1)
(allow default)
(deny network*)
(deny file-write*)
{regras}(allow file-write* (subpath "{tmp}") (subpath "/private/var/folders") (literal "/dev/null")
       (literal "/dev/dtracehelper") (literal "/dev/stdout") (literal "/dev/stderr"))
"""


def comando(args: list[str], pastas_escrita: list[Path]) -> list[str]:
    """Linha de comando para `python -m motor <args>` dentro da caixa de areia."""
    if not disponivel():
        raise RuntimeError("sandbox-exec não está disponível: o modo livre não roda sem a caixa de areia.")
    pastas = [*pastas_escrita, RAIZ / "storage" / "cache_voz"]
    for p in pastas:
        Path(p).mkdir(parents=True, exist_ok=True)
    perfil = Path(tempfile.mkstemp(suffix=".sb")[1])
    perfil.write_text(_perfil(pastas))
    return ["sandbox-exec", "-f", str(perfil), sys.executable, "-m", "motor", *args]


def rodar(args: list[str], pastas_escrita: list[Path], timeout: int = 1800, ao_ler=None) -> tuple[int, str]:
    """Roda e devolve (código de saída, saída de erro). `ao_ler(linha)` recebe a saída em tempo real."""
    cmd = comando(args, pastas_escrita)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.Popen(cmd, cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
                            bufsize=1)
    saida = []
    try:
        for linha in iter(proc.stdout.readline, ""):
            for parte in linha.replace("\r", "\n").splitlines():
                if parte.strip():
                    saida.append(parte)
                    if ao_ler:
                        ao_ler(parte)
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return 124, "tempo esgotado"
    finally:
        Path(cmd[2]).unlink(missing_ok=True)
    return proc.returncode, "\n".join(saida[-40:])
