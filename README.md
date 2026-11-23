# Simulador do adicional de mobilidade (FNP)

Página pública em que a pessoa digita o nome do município e vê quanto ele recebe
com o adicional de mobilidade, comparado ao adicional de FPM. Visual na
identidade "Território" da FNP (guia de estilo da FNP).

A mecânica segue a calculadora de salário do Nexo: a página não calcula nada
pesado, ela consulta uma tabela pronta (gerada da planilha) e monta frases,
cartões e barras.

## Estrutura

```
dados/municipios-ibge.json    lista oficial de municípios do IBGE (5.571)
scripts/gerar_dados.py        planilha .xlsx + lista IBGE -> site/dados-municipios.json
scripts/montar_html_unico.py  site/ -> docs/index.html (dados embutidos, arquivo único)
site/index.html               a página-fonte (busca o JSON ao lado se não houver embutido)
site/dados-municipios.json    gerado; não editar à mão
docs/index.html               gerado; é o que o GitHub Pages publica
```

A planilha `.xlsx` não vai para o repositório (`.gitignore`); o JSON gerado é a
fonte que a página usa.

## Atualizar os dados

```bash
pip install openpyxl
python scripts/gerar_dados.py CAMINHO/fpm_mobilidade.xlsx
python scripts/montar_html_unico.py
git add site docs && git commit -m "chore: atualiza dados da simulação"
```

`gerar_dados.py` confere o cabeçalho, códigos IBGE repetidos ou inexistentes e
se a coluna de diferença é mesmo mobilidade menos FPM; se algo não bater, para
com a linha do problema em vez de gerar dado errado.

Para atualizar a lista do IBGE (só se surgir município novo):

```bash
curl -sf "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado" -o dados/municipios-ibge.json
```

## Publicar (GitHub Pages)

Em Settings > Pages do repositório: Source "Deploy from a branch", branch
`main`, pasta `/docs`. Cada push na `main` atualiza o site em alguns minutos.

Não há servidor, banco nem cookie; a página não guarda o que a pessoa digita.
Depende só do Google Fonts (Outfit e Work Sans); sem ele, cai na fonte do sistema.

Link direto para um município: `.../#ibge-3550308` (código IBGE de 7 dígitos).

## Regras de leitura dos dados

- Faixa populacional é derivada da população: <10 mil, <30 mil, <80 mil,
  <250 mil, <500 mil, 500 mil ou mais (conferido: 0 divergências com a planilha).
- Quintil vem do IFEM (https://ifem.fnp.org.br/): 1º = menor receita corrente
  por habitante. Quintil vazio = município que ainda não declarou receita ao
  Siconfi; a página mostra "Sem quintil".
- Valores por habitante de grupos são ponderados pela população
  (soma dos valores / soma das populações).
- Municípios da lista do IBGE que não estão na planilha (34: regiões
  metropolitanas de Recife, Aracaju, Vitória e Goiânia, e Fernando de Noronha)
  são aqueles em que o transporte coletivo não é gerido pela prefeitura. Eles
  aparecem na busca com valores zerados e ficam fora de totais, médias e rankings.
