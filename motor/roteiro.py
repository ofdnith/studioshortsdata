"""Formato do roteiro (JSON) e validação. Só tipos de cena do catálogo são aceitos."""

import json
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- cenas

class Valor(Base):
    rotulo: str
    valor: float
    cor: str | None = None


class CenaBarras(Base):
    """Comparar poucos valores, com contagem animada."""
    tipo: Literal["barras"]
    dados: list[Valor] = Field(min_length=1, max_length=5)
    unidade: str = ""
    casas: int = 0
    destaque: str | None = None


class Serie(Base):
    nome: str
    cor: str | None = None


class Grupo(Base):
    rotulo: str
    valores: list[float]


class CenaBarrasPareadas(Base):
    """Grupos lado a lado (uma barra por série), marcando o vencedor."""
    tipo: Literal["barras_pareadas"]
    series: list[Serie] = Field(min_length=2, max_length=3)
    grupos: list[Grupo] = Field(min_length=1, max_length=7)
    unidade: str = ""
    marcar_vencedor: str | None = Field(None, description="nome da série marcada onde vence")
    destaque: str | None = Field(None, description="rótulo do grupo em foco")


class Parte(Base):
    rotulo: str
    valor: float
    cor: str | None = None


class BarraEmp(Base):
    rotulo: str
    cor: str | None = None
    partes: list[Parte] = Field(min_length=1, max_length=8)


class Legenda(Base):
    cor: str
    texto: str


class DestaqueEmp(Base):
    barra: str
    partes: list[str]
    texto: str = ""


class CenaBarraEmpilhada(Base):
    """Partes de um todo (uma ou mais barras 100%), com destaque."""
    tipo: Literal["barra_empilhada"]
    barras: list[BarraEmp] = Field(min_length=1, max_length=3)
    legenda: list[Legenda] = []
    destaque: DestaqueEmp | None = None


class Ponto(Base):
    x: float
    y: float


class ConjuntoPontos(Base):
    nome: str
    pontos: list[Ponto] = Field(min_length=2)


class Estatistica(Base):
    rotulo: str
    valor: str


class Reta(Base):
    a: float = Field(description="intercepto")
    b: float = Field(description="inclinação")


class CenaDispersao(Base):
    """Pontos, com morph entre conjuntos e painel de estatísticas.
    Conjuntos embutidos: 'datasaurus/<nome>' e 'anscombe/<I..IV>'."""
    tipo: Literal["dispersao"]
    conjuntos: list[str | ConjuntoPontos] = Field(min_length=1)
    estatisticas: list[Estatistica] = Field([], max_length=3)
    reta: Reta | None = None
    mostrar_nome: bool = True


class GraficoPequeno(Base):
    titulo: str
    conjunto: str | ConjuntoPontos
    reta: Reta | None = None
    curva: bool = False
    outlier: Ponto | None = None


class CenaGradeGraficos(Base):
    """Vários gráficos pequenos (até 4), foco em um por vez."""
    tipo: Literal["grade_graficos"]
    graficos: list[GraficoPequeno] = Field(min_length=2, max_length=4)
    foco: int | None = Field(None, description="índice (0..) do gráfico em foco")


class Linha(Base):
    rotulo: str
    valores: list[float]


class CenaTabela(Base):
    """Poucos números em linhas e colunas, vencedor destacado por coluna."""
    tipo: Literal["tabela"]
    colunas: list[str] = Field(min_length=1, max_length=4)
    linhas: list[Linha] = Field(min_length=1, max_length=4)
    unidade: str = ""
    unidades: list[str] = Field([], description="unidade por coluna (sobrepõe 'unidade')")
    vencedor: Literal["maior", "menor"] | None = "maior"
    coluna_total: bool = Field(False, description="última coluna é o total (cor amarela)")


class No(Base):
    id: str
    rotulo: str
    cor: str | None = None


class SetaCausal(Base):
    de: str
    para: str
    tracejada: bool = False
    rotulo: str | None = None


class CenaDiagramaCausal(Base):
    """Nós e setas: variável escondida, causa e efeito (até 4 nós)."""
    tipo: Literal["diagrama_causal"]
    nos: list[No] = Field(min_length=2, max_length=4)
    setas: list[SetaCausal] = Field(min_length=1, max_length=6)
    subtitulo: str = ""
    layout: Literal["auto", "linha", "ciclo"] = "auto"


class CenaPessoa(Base):
    """Caricatura genérica + cartão. 'pessoa' é o nome em roteiro.pessoas."""
    tipo: Literal["pessoa"]
    pessoa: str


class CenaLugar(Base):
    """Ilustração de um lugar da biblioteca (sem ilustração: cai em 'mapa')."""
    tipo: Literal["lugar"]
    lugar: str
    legenda: str = ""
    lat: float | None = None
    lon: float | None = None


class CenaMapa(Base):
    """Mapa simples (globo) com alfinete."""
    tipo: Literal["mapa"]
    lugar: str
    lat: float
    lon: float
    legenda: str = ""


class CenaTextoGrande(Base):
    """Frase de impacto (frase, palavra gigante, caixa), ou carimbo por cima da cena anterior."""
    tipo: Literal["texto_grande"]
    texto: str
    estilo: Literal["frase", "carimbo", "palavra", "caixa"] = "frase"
    subtitulo: str = ""
    objeto: str | None = Field(None, description="objeto da biblioteca desenhado acima da frase")


class CenaChamada(Base):
    """Fechamento com chamada para seguir."""
    tipo: Literal["chamada"]
    texto: str = "Siga para mais curiosidades de dados"


# ---------------------------------------------------------------- gráficos novos

class SerieLinha(Base):
    nome: str
    cor: str | None = None
    valores: list[float] = Field(min_length=2)


class CenaLinha(Base):
    """Série no tempo (uma ou mais linhas), com anotação num ponto."""
    tipo: Literal["linha"]
    rotulos_x: list[str] = Field(min_length=2)
    series: list[SerieLinha] = Field(min_length=1, max_length=3)
    unidade: str = ""
    destaque: str | None = None
    anotacao: str = ""
    ilustrativo: bool = False


class LinhaVertical(Base):
    x: float
    rotulo: str = ""
    cor: str | None = None


class CenaDistribuicao(Base):
    """Curva de distribuição com área sombreada, linhas de referência e amostras opcionais."""
    tipo: Literal["distribuicao"]
    forma: Literal["normal", "assimetrica", "bimodal", "uniforme"] = "normal"
    media: float = 0
    desvio: float = 1
    sombrear_de: float = 0
    sombrear_ate: float = 0
    rotulo_area: str = ""
    linhas: list[LinhaVertical] = Field([], max_length=3)
    rotulo_eixo: str = ""
    amostras: bool = False
    ilustrativo: bool = True


class Bin(Base):
    rotulo: str
    valor: float


class CenaHistograma(Base):
    """Barras contíguas (faixas de valores), com destaque."""
    tipo: Literal["histograma"]
    barras: list[Bin] = Field(min_length=3, max_length=20)
    unidade: str = ""
    destaque: list[str] = []
    rotulo_eixo: str = ""
    ilustrativo: bool = False


class Fatia(Base):
    rotulo: str
    valor: float
    cor: str | None = None


class CenaPizza(Base):
    """Partes de um todo em pizza ou rosca."""
    tipo: Literal["pizza"]
    fatias: list[Fatia] = Field(min_length=2, max_length=6)
    destaque: str | None = None
    rosca: bool = True
    centro: str = ""
    ilustrativo: bool = False


class ItemRanking(Base):
    rotulo: str
    valor: float
    cor: str | None = None


class CenaRanking(Base):
    """Ranking em barras horizontais (até 8), do maior para o menor."""
    tipo: Literal["ranking"]
    itens: list[ItemRanking] = Field(min_length=2, max_length=8)
    unidade: str = ""
    destaque: str | None = None
    ilustrativo: bool = False


class CenaSimulacao(Base):
    """Simulação: moeda ou dado lançados N vezes; a média converge para o esperado."""
    tipo: Literal["simulacao"]
    experimento: Literal["moeda", "dado"] = "moeda"
    lancamentos: int = 1000


# ---------------------------------------------------------------- cenas de apoio

class CenaIcones(Base):
    """Isotipo: grade de bonecos/círculos com uma parte destacada (ex.: 1 em cada 4)."""
    tipo: Literal["icones"]
    total: int = 100
    destaque: int = 0
    icone: Literal["pessoa", "circulo"] = "pessoa"
    rotulo: str = ""
    cor: str | None = None


class CenaNumeroGrande(Base):
    """Número gigante com contagem animada e contexto."""
    tipo: Literal["numero_grande"]
    valor: float
    prefixo: str = ""
    sufixo: str = ""
    casas: int = 0
    contexto: str = ""
    objeto: str | None = None


class CenaObjeto(Base):
    """Ilustração de um objeto da biblioteca, com legenda."""
    tipo: Literal["objeto"]
    objeto: str
    legenda: str = ""


class LadoComparacao(Base):
    titulo: str
    texto: str = ""
    objeto: str | None = None


class CenaComparacao(Base):
    """Dois cartões lado a lado: versus, mito × fato, antes × depois."""
    tipo: Literal["comparacao"]
    estilo: Literal["versus", "mito_fato", "antes_depois"] = "versus"
    esquerda: LadoComparacao
    direita: LadoComparacao
    vencedor: Literal["esquerda", "direita"] | None = None


class Evento(Base):
    ano: str
    texto: str


class CenaLinhaDoTempo(Base):
    """Linha do tempo vertical com 2 a 6 eventos."""
    tipo: Literal["linha_do_tempo"]
    eventos: list[Evento] = Field(min_length=2, max_length=6)
    destaque: int = -1


class CenaPassos(Base):
    """Lista de passos/itens que aparecem um a um."""
    tipo: Literal["passos"]
    itens: list[str] = Field(min_length=2, max_length=5)
    marcador: Literal["numero", "check", "x"] = "numero"


class CenaCitacao(Base):
    """Citação com autor (e retrato, se a pessoa estiver em 'pessoas')."""
    tipo: Literal["citacao"]
    texto: str
    autor: str
    detalhe: str = ""
    pessoa: str = ""


Cena = Annotated[Union[
    CenaBarras, CenaBarrasPareadas, CenaBarraEmpilhada, CenaDispersao, CenaGradeGraficos,
    CenaTabela, CenaDiagramaCausal, CenaPessoa, CenaLugar, CenaMapa, CenaTextoGrande, CenaChamada,
    CenaLinha, CenaDistribuicao, CenaHistograma, CenaPizza, CenaRanking, CenaSimulacao,
    CenaIcones, CenaNumeroGrande, CenaObjeto, CenaComparacao, CenaLinhaDoTempo, CenaPassos, CenaCitacao,
], Field(discriminator="tipo")]

TIPOS_GRAFICO = ["barras", "barras_pareadas", "barra_empilhada", "dispersao", "grade_graficos", "tabela",
                 "linha", "distribuicao", "histograma", "pizza", "ranking", "simulacao", "icones"]
TIPOS_CENA = TIPOS_GRAFICO + ["diagrama_causal", "pessoa", "lugar", "mapa", "texto_grande", "chamada",
                              "numero_grande", "objeto", "comparacao", "linha_do_tempo", "passos", "citacao"]


# ---------------------------------------------------------------- roteiro

class Trecho(Base):
    fala: str
    titulo_tela: list[str] = Field(default_factory=list, max_length=3)
    cena: Cena
    fonte_id: str | None = None


class Fonte(Base):
    id: str
    rodape: str
    citacao: str
    url: str
    trecho_que_comprova: str = ""


class Pessoa(Base):
    nome: str
    datas: str = ""
    descricao: str = Field("", description="ex.: estatístico britânico")
    feito: str = ""
    genero: Literal["masculino", "feminino"] | None = None
    cor_pele: Literal["clara", "media", "morena", "escura"] | None = None
    idade_na_epoca: int | None = None
    fonte_id: str | None = None


class Roteiro(Base):
    tema: str
    titulo_capa: str
    legenda: str = ""
    hashtags: list[str] = []
    trechos: list[Trecho] = Field(min_length=1)
    fontes: list[Fonte] = []
    pessoas: list[Pessoa] = []

    def fonte(self, fonte_id: str | None) -> Fonte | None:
        return next((f for f in self.fontes if f.id == fonte_id), None)

    def pessoa(self, nome: str) -> Pessoa | None:
        return next((p for p in self.pessoas if p.nome.lower() == nome.lower()), None)

    def contar_palavras(self) -> int:
        return sum(len(t.fala.split()) for t in self.trechos)


def carregar(caminho: str | Path) -> Roteiro:
    return Roteiro.model_validate(json.loads(Path(caminho).read_text(encoding="utf-8")))
