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

## Decisões de engenharia

O ambiente e as dependências ficam com o Poetry, travadas no `poetry.lock`, então o mesmo conjunto de versões roda em qualquer máquina. A imagem é Docker em estágio único, porque ela só precisa executar os scripts, sem etapa de publicação que justifique mais camadas. O `docker compose` é o ponto de entrada: um comando por parte, com o token saindo do `.env` em tempo de execução, nunca gravado na imagem.

O build também roda o flake8, linter que aponta erros comuns e desvios de estilo em Python, sobre todo o código: a linha `RUN flake8` quebra a construção com qualquer apontamento, então nada sem lint chega ao repositório. Como as camadas de dependência ficam em cache, o lint reexecuta apenas quando o código muda. Para rodar fora do build: `docker compose run --rm part1 flake8`.

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

## Parte 2 | Consultas SQL

As queries ficam em `part2_sql/queries.sql`. O script `load_sql.py` carrega os três CSVs num SQLite em memória, roda as queries e imprime os resultados no terminal, gravando uma cópia em `part2_sql/output/resultados.txt`.

```
docker compose run --build --rm part2
```

Antes de rodar as queries, o carregador confere o que carregou: se alguma venda aponta para um lead que não existe, se algum `lead_id` está duplicado e se algum lead ficou sem etapa. As três checagens passam sem exceção, e os 49 leads vendidos correspondem exatamente às 49 vendas.

### Tratamento dos dados

| Situação no dado | Tratamento | Por quê |
|---|---|---|
| 6 leads sem campanha, um deles vendido (VD510, R$ 44.909,27) | ficam fora das métricas por campanha e ganham a linha "(sem campanha)" no funil | a origem não existe no dado; inventar atribuição fabricaria número, e omitir esconderia receita |
| cmp_999 com 4 leads e nenhum gasto | não entra na query de custo, entra no funil | custo desconhecido não é custo zero |
| `etapa_atual` é um retrato, não um log de transições | contagem cumulativa: chegou a uma etapa quem está nela ou além, e o vendido conta em todas | é o único modelo que o formato do dado permite, e a limitação fica declarada |
| vendas fecham até 18/09, mídia termina em 30/06 | recorte declarado como teto | o funil de junho ainda pode fechar vendas, então o custo por venda apresentado só tende a cair |
| valores chegam como texto | normalização na carga: monetário em decimal, contagem em inteiro, campo vazio vira NULL | a query compara número com número, e string vazia não é campanha |

As 49 vendas fechadas somam R$ 1.797.984,15 de receita; a parte atribuída a campanhas soma R$ 1.753.074,88. A diferença é exatamente o contrato de R$ 44.909,27 do lead vendido sem campanha: nenhuma receita ficou de fora do cálculo.

### Resultados

**Custo por lead e custo por venda** (do melhor para o pior custo por venda)

| Campanha | Gasto (R$) | Leads | Custo/lead | Vendas | Custo/venda |
|---|---|---|---|---|---|
| cmp_004 | 3679.14 | 40 | 91.98 | 13 | 283.01 |
| cmp_006 | 7357.81 | 71 | 103.63 | 11 | 668.89 |
| cmp_003 | 7062.61 | 71 | 99.47 | 8 | 882.83 |
| cmp_002 | 11260.30 | 96 | 117.29 | 7 | 1608.61 |
| cmp_005 | 11596.14 | 95 | 122.06 | 5 | 2319.23 |
| cmp_001 | 10689.91 | 95 | 112.53 | 4 | 2672.48 |

O custo por lead varia de R$ 91,98 a R$ 122,06 entre campanhas, uma diferença de 1,3x. O custo por venda vai de R$ 283,01 a R$ 2.672,48, uma diferença de 9,4x. Como o preço do lead varia pouco perto disso, o que separa as campanhas é quantos leads cada uma converte em venda: a cmp_004 usa 3,1 leads por venda, e a cmp_001 usa 23,8. É no funil, depois da mídia, que esses leads se perdem.

**Funil por campanha** (leads que chegaram a cada etapa; a perda da transição anterior aparece entre parênteses)

| Campanha | Leads | em_atendimento | qualificado | briefing | proposta | vendido |
|---|---|---|---|---|---|---|
| cmp_004 | 40 | 29 (27.5%) | 27 (6.9%) | 18 (33.3%) | 16 (11.1%) | 13 (18.8%) |
| cmp_006 | 71 | 39 (45.1%) | 27 (30.8%) | 14 (48.1%) | 13 (7.1%) | 11 (15.4%) |
| cmp_003 | 71 | 39 (45.1%) | 26 (33.3%) | 15 (42.3%) | 11 (26.7%) | 8 (27.3%) |
| cmp_002 | 96 | 44 (54.2%) | 24 (45.5%) | 12 (50.0%) | 10 (16.7%) | 7 (30.0%) |
| cmp_005 | 95 | 50 (47.4%) | 37 (26.0%) | 14 (62.2%) | 9 (35.7%) | 5 (44.4%) |
| cmp_001 | 95 | 56 (41.1%) | 34 (39.3%) | 12 (64.7%) | 6 (50.0%) | 4 (33.3%) |
| (sem campanha) | 6 | 1 (83.3%) | 1 (0.0%) | 1 (0.0%) | 1 (0.0%) | 1 (0.0%) |
| cmp_999 | 4 | 0 (100.0%) | - | - | - | - |

**Ticket médio e receita** (do maior ticket para o menor)

| Campanha | Vendas | Receita (R$) | Ticket médio (R$) |
|---|---|---|---|
| cmp_004 | 13 | 517203.67 | 39784.90 |
| cmp_005 | 5 | 192034.78 | 38406.96 |
| cmp_001 | 4 | 152581.16 | 38145.29 |
| cmp_006 | 11 | 404065.89 | 36733.26 |
| cmp_002 | 7 | 251637.65 | 35948.24 |
| cmp_003 | 8 | 235551.73 | 29443.97 |

A campanha que traz o cliente de maior valor é a cmp_004, com ticket médio de R$ 39.784,90 em 13 vendas. O maior contrato individual é da cmp_001 (VD516, R$ 75.624,10), mas, com apenas 4 vendas na campanha, um contrato desses diz mais sobre um único fechamento do que sobre o cliente que a mídia atrai.

### O que sustenta a confiança

- O carregamento fecha com as fontes: 352 linhas de investimento, 478 de leads e 49 de vendas, com as checagens de integridade passando sem exceção;
- Cada query agrega cada tabela antes de cruzar com as demais, então o gasto de uma campanha não é contado mais de uma vez por causa de um JOIN;
- A receita total é a soma da receita por campanha mais o contrato do lead sem campanha, e qualquer pessoa reproduz todos os números com um único comando.

Para a realocação de verba, a cmp_004 é a candidata a receber mais: tem o melhor custo por venda, o maior ticket médio e converte 13 dos 40 leads em venda, mais que o dobro de qualquer outra campanha. A verba pode vir da cmp_002 e da cmp_005, os dois maiores orçamentos de mídia do período, que juntas gastam R$ 22.856,44 dos R$ 51.645,91 e entregam 12 das 48 vendas atribuídas a campanhas. A cmp_001 tem o pior custo por venda, mas cortar a mídia dela não resolve o problema: o lead custa o preço mediano das campanhas, e a perda de 64,7% entre qualificado e briefing acontece depois da mídia. O caso dela pede investigação de funil antes de decisão de verba.
