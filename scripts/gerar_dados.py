"""Converte a planilha fpm_mobilidade.xlsx no JSON enxuto que a página consome.

Uso:
    python scripts/gerar_dados.py CAMINHO/fpm_mobilidade.xlsx

Saída: site/dados-municipios.json

Municípios fora da planilha: a lista oficial do IBGE (dados/municipios-ibge.json,
baixada de https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado)
é comparada com a planilha e os que faltam vão para "fora". São os municípios em
que o transporte coletivo não é gerido pela prefeitura (consórcios metropolitanos
de Recife, Aracaju, Vitória e Goiânia, e Fernando de Noronha); a página mostra
esses com valores zerados, para a busca nunca dizer "não existe" a um município real.

Formato escolhido (por quê): uma lista de listas, sem nomes de chave repetidos,
para o arquivo ficar em ~250 KB em vez de ~700 KB. A ordem das colunas está em
"colunas", e a página lê por essa ordem. Faixa populacional e diferença NÃO são
gravadas: a página deriva as duas (faixa pela população, diferença =
mobilidade - FPM), o que evita guardar dado que pode ficar inconsistente.

O script é idempotente: rodar de novo com a mesma planilha gera o mesmo arquivo.
"""
import json
import logging
import re
import sys
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


def municipios_fora(codigos_na_planilha):
    """Municípios da lista do IBGE que não estão na planilha, como [ibge, nome, uf]."""
    if not LISTA_IBGE.exists():
        raise SystemExit(f'Lista do IBGE não encontrada em {LISTA_IBGE}. Baixe-a (ver docstring do módulo).')
    lista = json.loads(LISTA_IBGE.read_text(encoding='utf-8'))
    codigos_ibge = {int(m['municipio-id']) for m in lista}
    estranhos = codigos_na_planilha - codigos_ibge
    if estranhos:
        # Código na planilha que o IBGE não conhece indica erro de digitação na planilha.
        raise SystemExit(f'Códigos na planilha que não existem na lista do IBGE: {sorted(estranhos)}')
    fora = [
        [int(m['municipio-id']), m['municipio-nome'], m['UF-sigla']]
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
            ibge, mun_uf, uf, pop, _faixa, _f80, quintil, fpm, mob, dif = linha[:10]
            ibge = int(ibge)
            if ibge in vistos:
                raise ValueError(f'código IBGE repetido {ibge}')
            vistos.add(ibge)
            # Confere a coluna de diferença antes de descartá-la: se não bater,
            # a planilha mudou de regra e a página mostraria um número errado.
            if abs((mob - fpm) - dif) > 0.01:
                raise ValueError(f'diferença não é mobilidade - FPM ({dif} != {mob} - {fpm})')
            municipios.append([
                ibge, nome_sem_uf(mun_uf, uf), uf, int(pop), quintil_numero(quintil),
                round(float(fpm), 2), round(float(mob), 2),
            ])
        except (TypeError, ValueError) as erro:
            raise SystemExit(f'Linha {numero} da planilha com problema: {erro}. Conteúdo: {linha}')

    municipios.sort(key=lambda m: m[0])
    fora = municipios_fora(vistos)
    dados = {
        'colunas': ['ibge', 'nome', 'uf', 'populacao', 'quintil', 'fpm', 'mobilidade'],
        'municipios': municipios,
        'colunas_fora': ['ibge', 'nome', 'uf'],
        'fora': fora,
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    log.info('%d municípios na simulação e %d fora dela gravados em %s (%.0f KB)',
             len(municipios), len(fora), SAIDA, SAIDA.stat().st_size / 1024)
    for ibge, nome, uf in fora:
        log.info('  fora da simulação: %s (%s) %s', nome, uf, ibge)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Uso: python scripts/gerar_dados.py CAMINHO/fpm_mobilidade.xlsx')
    main(Path(sys.argv[1]))
