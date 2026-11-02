"""CLI do motor.

  python -m motor render roteiro.json --saida video.mp4 [--voz pm_alex] [--velocidade 1.2]
  python -m motor previa roteiro.json 0 5.5 12 [--pasta storage/previa]
  python -m motor validar roteiro.json
  python -m motor amostra --voz pf_dora --velocidade 1.2 --saida amostra.mp3
"""

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m motor", description="Motor de vídeos curtos")
    sub = ap.add_subparsers(dest="comando", required=True)

    r = sub.add_parser("render", help="renderiza o MP4, a capa e 4 prévias")
    r.add_argument("roteiro")
    r.add_argument("--saida", required=True)
    r.add_argument("--voz", default="pm_alex")
    r.add_argument("--velocidade", type=float, default=1.2)

    p = sub.add_parser("previa", help="gera PNGs de alguns instantes (em segundos)")
    p.add_argument("roteiro")
    p.add_argument("tempos", nargs="+", type=float)
    p.add_argument("--pasta", default="storage/previa")
    p.add_argument("--voz", default="pm_alex")
    p.add_argument("--velocidade", type=float, default=1.2)

    v = sub.add_parser("validar", help="valida o JSON do roteiro")
    v.add_argument("roteiro")

    a = sub.add_parser("amostra", help="MP3 curto com a voz")
    a.add_argument("--voz", default="pm_alex")
    a.add_argument("--velocidade", type=float, default=1.2)
    a.add_argument("--saida", default="storage/amostra.mp3")

    args = ap.parse_args(argv)

    if args.comando == "amostra":
        from motor.narracao import amostra
        print(amostra(args.voz, args.velocidade, Path(args.saida)))
        return

    from motor.roteiro import carregar
    try:
        roteiro = carregar(args.roteiro)
    except ValidationError as e:
        sys.exit(f"Roteiro inválido:\n{e}")

    if args.comando == "validar":
        print(f"ok: {len(roteiro.trechos)} trechos, {roteiro.contar_palavras()} palavras")
        return

    from motor.render import Config, previa, renderizar
    cfg = Config(args.voz, args.velocidade)
    if args.comando == "previa":
        previa(roteiro, args.tempos, Path(args.pasta), cfg)
    else:
        def barra(f):
            print(f"\r{f * 100:5.1f}%", end="", flush=True, file=sys.stderr)
        res = renderizar(roteiro, Path(args.saida), cfg, progresso=barra,
                         log=lambda m: print(f"\n{m}" if m.startswith("pronto") else m, file=sys.stderr))
        print(res.mp4)


if __name__ == "__main__":
    main()
