"""Custos por vídeo: automáticos (API do Claude, por versão de roteiro) + lançados à mão."""

from dataclasses import dataclass, field

CATEGORIAS = {
    "api_claude": "API do Claude",
    "impulsionamento": "Impulsionamento / anúncios",
    "trilha": "Trilha / música",
    "edicao": "Edição / design",
    "ferramenta": "Ferramenta / assinatura (rateio)",
    "outro": "Outro",
}
MANUAIS = {k: v for k, v in CATEGORIAS.items() if k != "api_claude"}


def cotacao(con) -> float:
    r = con.execute("SELECT valor FROM ajuste WHERE chave = 'cotacao_usd_brl'").fetchone()
    try:
        return float(r[0]) if r else 5.5
    except ValueError:
        return 5.5


def definir_cotacao(con, valor: float):
    con.execute("INSERT INTO ajuste (chave, valor) VALUES ('cotacao_usd_brl', ?) "
                "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor", (f"{valor:.4f}",))


@dataclass
class Item:
    categoria: str
    descricao: str
    valor: float
    moeda: str
    data: str
    automatico: bool
    id: int | None = None

    def em(self, moeda: str, cot: float) -> float:
        if moeda == self.moeda:
            return self.valor
        return self.valor * cot if moeda == "BRL" else self.valor / cot


@dataclass
class Resumo:
    itens: list[Item] = field(default_factory=list)
    cotacao: float = 5.5

    def total(self, moeda: str) -> float:
        return round(sum(i.em(moeda, self.cotacao) for i in self.itens), 2)

    def por_categoria(self, moeda: str = "BRL") -> dict[str, float]:
        res: dict[str, float] = {}
        for i in self.itens:
            res[i.categoria] = round(res.get(i.categoria, 0) + i.em(moeda, self.cotacao), 2)
        return res

    @property
    def api_usd(self) -> float:
        return round(sum(i.em("USD", self.cotacao) for i in self.itens if i.automatico), 4)


def resumo(con, tema_id: int) -> Resumo:
    cot = cotacao(con)
    itens = []
    for r in con.execute("SELECT versao, origem, modelo, custo_estimado, tokens_entrada, tokens_saida,"
                         " tokens_cache_leitura, tokens_cache_escrita, buscas_web, criado_em FROM roteiro"
                         " WHERE tema_id = ? AND custo_estimado > 0 ORDER BY versao", (tema_id,)):
        tipo = "correção" if r["origem"] == "correcao" else "roteiro"
        tokens = r["tokens_entrada"] + r["tokens_cache_leitura"] + r["tokens_cache_escrita"]
        itens.append(Item("api_claude",
                          f"{tipo} v{r['versao']} · {r['modelo']} · {tokens:,} tok. entrada, "
                          f"{r['tokens_saida']:,} saída, {r['buscas_web']} buscas".replace(",", "."),
                          r["custo_estimado"], "USD", r["criado_em"][:10], True))
    for r in con.execute("SELECT * FROM custo WHERE tema_id = ? ORDER BY data, id", (tema_id,)):
        itens.append(Item(r["categoria"], r["descricao"], r["valor"], r["moeda"], r["data"], False, r["id"]))
    return Resumo(itens, cot)


def totais_por_tema(con) -> dict[int, dict]:
    """{tema_id: {'BRL': x, 'USD': y}} para listas (biblioteca, temas)."""
    cot = cotacao(con)
    res: dict[int, dict] = {}

    def somar(tid, valor, moeda):
        d = res.setdefault(tid, {"BRL": 0.0, "USD": 0.0})
        usd = valor if moeda == "USD" else valor / cot
        d["USD"] += usd
        d["BRL"] += usd * cot

    for tid, v in con.execute("SELECT tema_id, sum(custo_estimado) FROM roteiro GROUP BY tema_id"):
        if v:
            somar(tid, v, "USD")
    for tid, v, m in con.execute("SELECT tema_id, sum(valor), moeda FROM custo GROUP BY tema_id, moeda"):
        somar(tid, v, m)
    return res


def adicionar(con, tema_id: int, categoria: str, descricao: str, valor: float, moeda: str, data: str | None):
    if categoria not in MANUAIS:
        categoria = "outro"
    if moeda not in ("BRL", "USD"):
        moeda = "BRL"
    con.execute("INSERT INTO custo (tema_id, categoria, descricao, valor, moeda, data) "
                "VALUES (?, ?, ?, ?, ?, coalesce(?, date('now')))",
                (tema_id, categoria, descricao.strip(), valor, moeda, data or None))


def remover(con, custo_id: int):
    con.execute("DELETE FROM custo WHERE id = ?", (custo_id,))


def moeda_fmt(v: float, moeda: str) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}" if moeda == "BRL" else f"US$ {s}"
