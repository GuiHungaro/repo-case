# Case Técnico | Desenvolvedor Python Pleno | Automação, Dados e IA

Solução do case técnico da Cômodo. O projeto tem três partes, cada uma em sua pasta:

1. Ingestão de repositórios públicos de uma organização via API do GitHub
2. Queries SQL sobre os dados de funil (investimento, leads e vendas)
3. Classificação de conversas de pré-vendas com LLM

## Requisitos

- Docker
- Python 3.14 e Poetry, apenas para desenvolvimento local

## Preparando o ambiente

```
copy .env.example .env
```

Preencha o `GITHUB_TOKEN` no arquivo `.env` com um token pessoal do GitHub, gerado sem nenhum escopo, pois os dados consumidos são públicos. O token é injetado em tempo de execução e não fica gravado na imagem.

## Executando

```
docker compose run --build --rm part1
```

O comando constrói a imagem quando necessário e executa a parte correspondente. Os serviços disponíveis são `part1`, `part2` e `part3`. Cada parte grava seus arquivos na subpasta `output` dentro da própria pasta da parte.

## Lint

O build executa o flake8 sobre o código e falha se houver apontamentos. Para rodar o flake8 fora do build:

```
docker compose run --rm part1 flake8
```