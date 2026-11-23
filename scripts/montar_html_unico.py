"""Monta docs/index.html: a página com os dados embutidos, num arquivo só.

Uso:
    python scripts/montar_html_unico.py

Por quê: em desenvolvimento a página busca site/dados-municipios.json por fetch
(assim o HTML fica legível). Para publicar em qualquer servidor sem se preocupar
com caminho de arquivo ou CORS, este script troca o marcador
<!--DADOS-EMBUTIDOS--> por um <script type="application/json"> com o JSON.
A página sempre tenta ler o embutido primeiro e só cai no fetch se não achar.
"""
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger('montar_html_unico')

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / 'site' / 'index.html'
DADOS = RAIZ / 'site' / 'dados-municipios.json'
SAIDA = RAIZ / 'docs' / 'index.html'  # GitHub Pages publica a pasta docs/ da branch main
MARCADOR = '<!--DADOS-EMBUTIDOS-->'
FIM_DO_HEAD = '<!--FIM-DO-HEAD-->'


def main():
    for arquivo in (PAGINA, DADOS):
        if not arquivo.exists():
            raise SystemExit(f'Arquivo não encontrado: {arquivo}. Rode antes scripts/gerar_dados.py.')
    html = PAGINA.read_text(encoding='utf-8')
    if html.count(MARCADOR) != 1:
        raise SystemExit(f'O marcador {MARCADOR} deve aparecer exatamente uma vez em {PAGINA}.')
    # "</" dentro do JSON fecharia o <script> antes da hora; escapar a barra resolve
    # e continua sendo JSON válido.
    json_seguro = DADOS.read_text(encoding='utf-8').replace('</', '<\\/')
    bloco = f'<script id="dados-municipios" type="application/json">{json_seguro}</script>'
    html = html.replace(MARCADOR, bloco)

    # site/index.html é escrito sem <html>/<head>/<body> (o publicador de prévia
    # os acrescenta). Para servir o arquivo direto, montamos o documento completo:
    # o que vem antes de <!--FIM-DO-HEAD--> vai no <head>, o resto no <body>.
    if html.count(FIM_DO_HEAD) != 1:
        raise SystemExit(f'O marcador {FIM_DO_HEAD} deve aparecer exatamente uma vez em {PAGINA}.')
    cabeca, corpo = html.split(FIM_DO_HEAD)
    documento = (
        '<!doctype html>\n<html lang="pt-br">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        f'{cabeca.strip()}\n</head>\n<body>\n{corpo.strip()}\n</body>\n</html>\n'
    )
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(documento, encoding='utf-8')
    # Sem o .nojekyll o GitHub Pages passa a pasta pelo Jekyll, o que é desnecessário aqui.
    (SAIDA.parent / '.nojekyll').write_text('', encoding='utf-8')
    log.info('Gerado %s (%.0f KB)', SAIDA, SAIDA.stat().st_size / 1024)


if __name__ == '__main__':
    main()
