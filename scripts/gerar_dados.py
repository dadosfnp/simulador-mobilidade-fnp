"""Converte a planilha da simulação no JSON enxuto que a página consome.

Uso:
    python scripts/gerar_dados.py CAMINHO/fpm_mobilidade.xlsx

Saída: site/dados-municipios.json

O que vai para o JSON: só o repasse simulado aos ônibus municipais (coluna
"Adicional de mobilidade" da planilha), população e quintil do IFEM. As colunas
de FPM da planilha são usadas apenas para conferir a consistência da planilha
e NÃO são gravadas: o site fala só do repasse da tarifa zero aos fins de semana.

Municípios fora da planilha: a lista oficial do IBGE (dados/municipios-ibge.json,
baixada de https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado)
é comparada com a planilha. Os que faltam são, pela nota metodológica, os
municípios dos arranjos metropolitanos tratados no segmento intermunicipal
(ARRANJOS abaixo), mais Fernando de Noronha. Cada um vai para "fora" com o nome
do arranjo (ou vazio), para a página explicar o motivo.

Formato: lista de listas, sem nomes de chave repetidos, para o arquivo ficar
pequeno. A ordem das colunas está em "colunas"/"colunas_fora".

O script é idempotente: rodar de novo com a mesma planilha gera o mesmo arquivo.
"""
import json
import logging
import re
import sys
import unicodedata
from pathlib import Path

import openpyxl

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger('gerar_dados')

COLUNAS_ESPERADAS = [
    'Código IBGE', 'Município - UF', 'UF', 'População', 'Faixa populacional',
    'Faixa 80 mil', 'Quintil', 'Adicional de FPM', 'Adicional de mobilidade',
    'Diferença de adicional de mobilidade pelo FPM',
]
RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / 'site' / 'dados-municipios.json'
LISTA_IBGE = RAIZ / 'dados' / 'municipios-ibge.json'

# Copiado da "Nota metodológica sobre a tarifa zero aos fins de semana"
# (seção "Arranjos metropolitanos excluídos do rateio municipal").
# Chave: nome do arranjo como está na nota; valor: (UF, municípios).
ARRANJOS = {
    'Goiânia (GO)': ('GO', [
        'Goiânia', 'Abadia de Goiás', 'Aparecida de Goiânia', 'Aragoiânia', 'Bela Vista de Goiás',
        'Bonfinópolis', 'Brazabrantes', 'Caldazinha', 'Caturaí', 'Goianira', 'Goianápolis', 'Guapó',
        'Hidrolândia', 'Inhumas', 'Nerópolis', 'Nova Veneza', 'Santa Bárbara de Goiás',
        'Santo Antônio de Goiás', 'Senador Canedo', 'Terezópolis de Goiás', 'Trindade',
    ]),
    'Recife (PE)': ('PE', ['Recife', 'Olinda', 'Camaragibe']),
    'Grande Vitória (ES)': ('ES', ['Vitória', 'Vila Velha', 'Serra', 'Cariacica', 'Viana']),
    'Aracaju (SE)': ('SE', ['Aracaju', 'Barra dos Coqueiros', 'Nossa Senhora do Socorro', 'São Cristóvão']),
}


def chave_nome(nome):
    """Nome comparável: sem acento e em minúsculas."""
    return unicodedata.normalize('NFD', nome).encode('ascii', 'ignore').decode().lower().strip()


def municipios_fora(codigos_na_planilha):
    """Municípios da lista do IBGE fora da planilha, como [ibge, nome, uf, arranjo].

    arranjo é o nome do arranjo metropolitano da nota ou '' quando o município não
    está em nenhum (caso de Fernando de Noronha). Falha se um município listado na
    nota não for achado no IBGE ou estiver na planilha, porque aí a nota e a
    planilha discordam e a página explicaria o motivo errado.
    """
    if not LISTA_IBGE.exists():
        raise SystemExit(f'Lista do IBGE não encontrada em {LISTA_IBGE}. Baixe-a (ver docstring do módulo).')
    lista = json.loads(LISTA_IBGE.read_text(encoding='utf-8'))
    codigos_ibge = {int(m['municipio-id']) for m in lista}
    estranhos = codigos_na_planilha - codigos_ibge
    if estranhos:
        raise SystemExit(f'Códigos na planilha que não existem na lista do IBGE: {sorted(estranhos)}')

    por_nome_uf = {(chave_nome(m['municipio-nome']), m['UF-sigla']): int(m['municipio-id']) for m in lista}
    arranjo_de = {}
    for arranjo, (uf, nomes) in ARRANJOS.items():
        for nome in nomes:
            codigo = por_nome_uf.get((chave_nome(nome), uf))
            if codigo is None:
                raise SystemExit(f'Município do arranjo {arranjo} não achado no IBGE: {nome} ({uf})')
            if codigo in codigos_na_planilha:
                raise SystemExit(f'{nome} ({uf}) está no arranjo {arranjo} da nota, mas também na planilha.')
            arranjo_de[codigo] = arranjo

    fora = [
        [int(m['municipio-id']), m['municipio-nome'], m['UF-sigla'], arranjo_de.get(int(m['municipio-id']), '')]
        for m in lista if int(m['municipio-id']) not in codigos_na_planilha
    ]
    return sorted(fora, key=lambda m: m[0])


def quintil_numero(texto):
    """'3º quintil' -> 3. Vazio -> 0 (município ainda sem dados de receita no Siconfi)."""
    if texto is None or str(texto).strip() == '':
        return 0
    achado = re.match(r'\s*([1-5])', str(texto))
    if not achado:
        raise ValueError(f'Quintil em formato inesperado: {texto!r}')
    return int(achado.group(1))


def nome_sem_uf(municipio_uf, uf):
    """'São Paulo - SP' -> 'São Paulo'. Confere se a UF do texto bate com a coluna UF."""
    sufixo = f' - {uf}'
    if not municipio_uf.endswith(sufixo):
        raise ValueError(f'Nome {municipio_uf!r} não termina com {sufixo!r}')
    return municipio_uf[: -len(sufixo)]


def main(caminho):
    log.info('Lendo %s', caminho)
    livro = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    linhas = livro.active.iter_rows(values_only=True)
    cabecalho = list(next(linhas))
    if cabecalho[: len(COLUNAS_ESPERADAS)] != COLUNAS_ESPERADAS:
        raise SystemExit(f'Cabeçalho diferente do esperado.\nVeio: {cabecalho}\nEsperado: {COLUNAS_ESPERADAS}')

    municipios, vistos = [], set()
    for numero, linha in enumerate(linhas, start=2):
        if linha[0] is None:
            continue
        try:
            ibge, mun_uf, uf, pop, _faixa, _f80, quintil, fpm, repasse, dif = linha[:10]
            ibge = int(ibge)
            if ibge in vistos:
                raise ValueError(f'código IBGE repetido {ibge}')
            vistos.add(ibge)
            # Conferência de consistência da planilha; FPM não é gravado.
            if abs((repasse - fpm) - dif) > 0.01:
                raise ValueError(f'coluna de diferença inconsistente ({dif} != {repasse} - {fpm})')
            if repasse < 0:
                raise ValueError(f'repasse negativo: {repasse}')
            municipios.append([
                ibge, nome_sem_uf(mun_uf, uf), uf, int(pop), quintil_numero(quintil), round(float(repasse), 2),
            ])
        except (TypeError, ValueError) as erro:
            raise SystemExit(f'Linha {numero} da planilha com problema: {erro}. Conteúdo: {linha}')

    municipios.sort(key=lambda m: m[0])
    fora = municipios_fora(vistos)
    dados = {
        'colunas': ['ibge', 'nome', 'uf', 'populacao', 'quintil', 'repasse'],
        'municipios': municipios,
        'colunas_fora': ['ibge', 'nome', 'uf', 'arranjo'],
        'fora': fora,
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    total = sum(m[5] for m in municipios)
    log.info('%d municípios na planilha (repasse total R$ %.2f) e %d fora dela gravados em %s (%.0f KB)',
             len(municipios), total, len(fora), SAIDA, SAIDA.stat().st_size / 1024)
    for ibge, nome, uf, arranjo in fora:
        log.info('  fora: %s (%s) %s %s', nome, uf, ibge, f'arranjo {arranjo}' if arranjo else 'sem arranjo')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Uso: python scripts/gerar_dados.py CAMINHO/fpm_mobilidade.xlsx')
    main(Path(sys.argv[1]))
