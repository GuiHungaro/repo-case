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

## Parte 1 | Ingestão via API

O script consome a API pública do GitHub e extrai nome, descrição, linguagem principal, estrelas, forks, data de criação e data da última atualização de todos os repositórios públicos da organização `microsoft`. O resultado vai para `part1_ingestion/output/repos_microsoft.csv`, com uma cópia datada em `output/history/`.

```
docker compose run --build --rm part1
```

Ao final, o script imprime o total coletado confrontado com o número de repositórios públicos que a própria organização declara na API, o caminho dos arquivos gravados e a duração da execução.

Decisões:

- O formato é CSV, tabela plana de sete colunas nomeadas em português, porque quem abre o arquivo no Excel é o time, e o arquivo abre direto sem ferramenta extra;
- O arquivo `repos_microsoft.csv` é o retrato do dia e é sobrescrito a cada execução, enquanto a cópia datada em `history/` preserva o que foi coletado a cada dia, então o snapshot diário não custa o histórico;
- O script só grava o arquivo quando o total coletado fecha com o número que a organização declara, então um arquivo presente na pasta é sempre um arquivo completo;
- Falhas transitórias de rede ou da API recebem três tentativas com espera crescente, e uma falha definitiva encerra o script com mensagem clara e código de saída diferente de zero, sem gravar arquivo incompleto.

## Lint

O build executa o flake8 sobre o código e falha se houver apontamentos. Para rodar o flake8 fora do build:

```
docker compose run --rm part1 flake8
```