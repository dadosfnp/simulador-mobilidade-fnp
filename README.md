# Tarifa zero no seu município (FNP)

Página pública em que a pessoa digita o nome do município e vê o repasse simulado
aos ônibus municipais na estimativa preliminar da FNP para a PEC 18/2026 (tarifa
zero aos fins de semana). Visual na identidade "Território" da FNP.

A mecânica segue a calculadora de salário do Nexo: a página não calcula nada
pesado, ela consulta uma tabela pronta (gerada da planilha) e monta frases,
cartões e barras.

O texto da metodologia é a "Nota metodológica sobre a tarifa zero aos fins de
semana", enviada pela gerência de mobilidade, reproduzida sem alteração em
`site/index.html` (seção "Nota metodológica" e constantes `NOTA_*` do script).
Mudou a nota? Atualize os dois lugares e a constante `ARRANJOS` de
`scripts/gerar_dados.py`.

O site fala só do repasse da tarifa zero. As colunas de FPM da planilha servem
apenas para conferir a consistência dela e não vão para o JSON nem para a página.

## Estrutura

```
dados/municipios-ibge.json    lista oficial de municípios do IBGE (5.571)
scripts/gerar_dados.py        planilha .xlsx + lista IBGE -> site/dados-municipios.json
scripts/montar_html_unico.py  site/ -> docs/index.html (dados embutidos, arquivo único)
site/index.html               a página-fonte (busca o JSON ao lado se não houver embutido)
site/dados-municipios.json    gerado; não editar à mão
docs/index.html               gerado; é o que o GitHub Pages publica
```

A planilha `.xlsx` não vai para o repositório (`.gitignore`).

## Atualizar os dados

```bash
pip install openpyxl
python scripts/gerar_dados.py CAMINHO/fpm_mobilidade.xlsx
python scripts/montar_html_unico.py
git add site docs && git commit -m "chore: atualiza dados da simulação"
```

`gerar_dados.py` confere o cabeçalho, códigos IBGE repetidos ou inexistentes, a
consistência da planilha e se os municípios dos arranjos da nota batem com o IBGE;
se algo não bater, para com a linha do problema em vez de gerar dado errado.

Para atualizar a lista do IBGE (só se surgir município novo):

```bash
curl -sf "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado" -o dados/municipios-ibge.json
```

## Publicar (GitHub Pages)

Settings > Pages: "Deploy from a branch", branch `main`, pasta `/docs`. Cada push
na `main` atualiza o site em alguns minutos.

Não há servidor, banco nem cookie; a página não guarda o que a pessoa digita.
Depende só do Google Fonts (Outfit e Work Sans); sem ele, cai na fonte do sistema.

Link direto para um município: `.../#ibge-3550308` (código IBGE de 7 dígitos).

## Como a página trata cada município

- **Incluído no rateio** (repasse > 0): repasse simulado por ano, por habitante,
  participação nos R$ 8 bi, comparação por habitante e ranking no estado.
- **Na planilha, sem repasse**: "Não contemplado", com o critério da nota (mais de
  50 mil habitantes e transporte coletivo municipal declarado na Pemob).
- **Arranjos metropolitanos da nota** (Goiânia, Recife, Grande Vitória, Aracaju;
  33 municípios fora da planilha): "Não calculado", com o texto da nota sobre o
  segmento intermunicipal e a linha do arranjo.
- **Fernando de Noronha** (fora da planilha, sem arranjo): "Não calculado", com o
  critério da nota.

Outras regras: faixa populacional derivada da população (0 divergências com a
planilha); quintil do IFEM (https://ifem.fnp.org.br/), 1º = menor receita por
habitante, vazio = receita não declarada ao Siconfi; valores por habitante de
grupos = soma dos repasses / soma das populações.
