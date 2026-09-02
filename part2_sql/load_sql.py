import csv
import sqlite3
from pathlib import Path

PASTA = Path(__file__).resolve().parent
DADOS = PASTA.parent / "data"
ARQUIVO_SQL = PASTA / "queries.sql"
PASTA_SAIDA = PASTA / "output"

TABELAS = {
    "investimento_midia": [
        ("data", str),
        ("campanha_id", str),
        ("plataforma", str),
        ("nome_campanha", str),
        ("gasto", float),
        ("impressoes", int),
        ("cliques", int),
    ],
    "leads": [
        ("lead_id", str),
        ("nome", str),
        ("telefone", str),
        ("criado_em", str),
        ("campanha_id", str),
        ("etapa_atual", str),
    ],
    "vendas": [
        ("venda_id", str),
        ("lead_id", str),
        ("data_fechamento", str),
        ("valor_contrato", float),
    ],
}


def criar_tabelas(conexao):
    for tabela, colunas in TABELAS.items():
        definicao = ", ".join(
            f"{coluna} {'REAL' if tipo is float else 'INTEGER' if tipo is int else 'TEXT'}"
            for coluna, tipo in colunas
        )
        conexao.execute(f"CREATE TABLE {tabela} ({definicao})")


def carregar_csv(conexao, tabela, colunas):
    with (DADOS / f"{tabela}.csv").open(encoding="utf-8-sig", newline="") as arquivo:
        registros = []
        for linha in csv.DictReader(arquivo):
            valores = []
            for coluna, tipo in colunas:
                bruto = linha[coluna].strip()
                if bruto == "":
                    valores.append(None)
                elif tipo is float:
                    valores.append(float(bruto))
                elif tipo is int:
                    valores.append(int(bruto))
                else:
                    valores.append(bruto)
            registros.append(valores)
        placeholders = ", ".join("?" for _ in colunas)
        conexao.executemany(f"INSERT INTO {tabela} VALUES ({placeholders})", registros)
        return len(registros)


def checagens(conexao):
    orfas = conexao.execute(
        "SELECT COUNT(*) FROM vendas v LEFT JOIN leads l ON l.lead_id = v.lead_id "
        "WHERE l.lead_id IS NULL"
    ).fetchone()[0]
    duplicados = conexao.execute(
        "SELECT COUNT(*) - COUNT(DISTINCT lead_id) FROM leads"
    ).fetchone()[0]
    sem_etapa = conexao.execute(
        "SELECT COUNT(*) FROM leads WHERE etapa_atual IS NULL OR etapa_atual = ''"
    ).fetchone()[0]
    print(
        f"verificacoes: vendas sem lead: {orfas} | lead_id duplicado: {duplicados} "
        f"| lead sem etapa: {sem_etapa}"
    )


def formatar_tabela(cabecalhos, linhas):
    def celula(valor):
        if valor is None:
            return "-"
        if isinstance(valor, float):
            return f"{valor:.2f}"
        return str(valor)

    celulas = [[celula(v) for v in linha] for linha in linhas]
    larguras = [
        max(len(cabecalhos[i]), max((len(c[i]) for c in celulas), default=0))
        for i in range(len(cabecalhos))
    ]
    cabecalho = " | ".join(h.ljust(larguras[i]) for i, h in enumerate(cabecalhos))
    separador = "-+-".join("-" * larguras[i] for i in range(len(cabecalhos)))
    corpo = [
        " | ".join(c[i].ljust(larguras[i]) for i in range(len(cabecalhos))) for c in celulas
    ]
    return "\n".join([cabecalho, separador] + corpo)


def main():
    conexao = sqlite3.connect(":memory:")
    criar_tabelas(conexao)
    for tabela, colunas in TABELAS.items():
        total = carregar_csv(conexao, tabela, colunas)
        print(f"{tabela}: {total} linhas carregadas")
    checagens(conexao)
    consultas = [s.strip() for s in ARQUIVO_SQL.read_text(encoding="utf-8").split(";") if s.strip()]
    relatorio = []
    for indice, consulta in enumerate(consultas, 1):
        titulo = next(ln for ln in consulta.splitlines() if ln.startswith("--"))
        cursor = conexao.execute(consulta)
        cabecalhos = [d[0] for d in cursor.description]
        linhas = cursor.fetchall()
        bloco = [titulo, formatar_tabela(cabecalhos, linhas), ""]
        relatorio.extend(bloco)
        print("\n".join(bloco))
    PASTA_SAIDA.mkdir(exist_ok=True)
    (PASTA_SAIDA / "resultados.txt").write_text("\n".join(relatorio), encoding="utf-8")
    print(f"resultados salvos em {PASTA_SAIDA / 'resultados.txt'}")


if __name__ == "__main__":
    main()
