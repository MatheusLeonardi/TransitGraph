# TransitGraph

Aplicação de Teoria dos Grafos para explorar a conectividade da rede de ônibus
de São Paulo a partir de dados GTFS da SPTrans.

O projeto usa **Busca em Largura (BFS)** e **Busca em Profundidade (DFS)** em
uma rede real, permite identificar a ordem de visita dos vértices e compara o
comportamento dos dois algoritmos na mesma consulta.

## Problema e modelagem

O grafo direcionado é definido por `G = (V, E)`:

- `V`: paradas de ônibus presentes nas viagens ativas na data escolhida;
- `E`: conexões direcionadas entre paradas consecutivas de uma viagem;
- `edge_routes`: conjunto de linhas que realiza cada conexão.

A direção da aresta importa porque uma viagem pode percorrer somente um dos
sentidos entre duas paradas. Arestas repetidas por diferentes viagens são
consolidadas, preservando as linhas associadas.

As adjacências de saída ficam em dicionários ordenados pela inserção, com
uma entrada por vizinho. A topologia ocupa O(V + E). Uma matriz de adjacência
para a rede completa teria 433.139.344 posições. O SQLite preserva a ordem
das arestas na recarga. Essa ordem decide empates na BFS e influencia a
árvore de descoberta da DFS.

Com o GTFS incluído e a data `2026-11-01`, o grafo possui 20.812 vértices e
27.218 arestas direcionadas.

## Papel dos algoritmos

### BFS — menor quantidade de conexões

A BFS explora o grafo em níveis usando uma fila. No TransitGraph, ela encontra
um caminho entre origem e destino com o menor número de arestas. A busca
ignora os pesos de tempo mantidos para a consulta independente com Dijkstra.

### DFS — exploração e alcançabilidade

A DFS usa uma pilha de vértices ativos com o iterador de cada adjacência.
Sem destino, mede a cobertura direcionada de uma parada e informa quantas
paradas da instância ficam fora dessa cobertura. Com destino, a DFS para
na descoberta e pode fornecer um caminho maior que o mínimo. Ao esgotar os
vizinhos de um vértice, a DFS o finaliza e retorna ao quadro anterior.

Sem destino, ambas as buscas visitam todo o subgrafo alcançável a partir da
origem. A análise de componentes fracos usa outra DFS sobre a projeção
que ignora o sentido das arestas.

### Comparação

| Característica | BFS | DFS |
|---|---|---|
| Estrutura | Fila | Pilha |
| Estratégia | Explora por níveis | Aprofunda um ramo |
| Menor caminho não ponderado | Garante | Não garante |
| Uso no projeto | Rota com menos arestas | Alcançabilidade e exploração |
| Complexidade | `O(V + E)` | `O(V + E)` |
| Memória assintótica | `O(V)` | `O(V)` |

A interface mostra a ordem numerada de visita, os totais de descobertas e
visitas, as arestas examinadas, o caminho e o tempo da busca. Na BFS, cada
visita é uma retirada da fila. Na DFS, cada visita é uma descoberta e a
ordem de finalização aparece à parte.

## Qualidade da geometria

As conexões preservam as ocorrências de parada, viagem, sentido e shape. A
seleção procura manter a mesma viagem para conexões consecutivas de uma linha.
O diagnóstico mostra quando o caminho topológico exige trocar de viagem.

O importador usa as distâncias GTFS quando existem nos dois arquivos e são
consistentes. No feed incluído, as paradas são projetadas nos segmentos do
shape em ordem crescente. Códigos de parada consecutivos com coordenadas
iguais podem ocupar a mesma posição. O SQLite inclui 76.987 ocorrências,
das quais 13 desse tipo ficam explicitamente sem trajeto de rua confirmado.

O traçado oficial é exibido em primeiro lugar. Trechos com baixa resolução
ou ligações aproximadas aparecem tracejados. O OSRM pode refinar fragmentos
esparsos, desde que preserve os pontos de controle em ordem e mantenha a
geometria dentro dos limites de confiança e desvio. O perfil público prediz
trajetos de carro e pode divergir de corredores exclusivos de ônibus.

Use **Diagnóstico geográfico**, abaixo do mapa, para selecionar uma conexão
e comparar o GTFS, a proposta do OSRM e o traçado final. Consulte também a
[auditoria geográfica](docs/AUDITORIA_GEOMETRIA.md).

O refinamento pode ser desativado:

```powershell
$env:TRANSITGRAPH_MAP_MATCHING = "0"
python run.py
```

Também é possível usar uma instância própria do OSRM:

```powershell
$env:TRANSITGRAPH_OSRM_URL = "http://localhost:5001"
python run.py
```

## Funcionalidades

- mapa das paradas com Leaflet e OpenStreetMap;
- pesquisa de parada por nome ou código;
- caminho com menor número de arestas usando BFS;
- origem e destino selecionados pelo nome ou código da parada;
- rota de menor tempo estimado com Dijkstra e pesos derivados dos horários GTFS;
- alcançabilidade e caminho em profundidade usando DFS;
- comparação lado a lado entre BFS e DFS;
- identificação da ordem de visita dos vértices;
- itinerário agrupado por linha, com indicação de baldeações;
- traçado real dos ônibus usando `shapes.txt` do GTFS;
- setas de sentido e marcadores de origem/destino no mapa;
- visualização de vizinhanças com Cytoscape.js;
- componentes fracamente conexos da rede;
- persistência do grafo em SQLite.

## Tecnologias

- Python e Flask;
- SQLite;
- JavaScript, Leaflet e Cytoscape.js;
- Pytest;
- dados no formato GTFS.

## Como executar

### 1. Preparar o ambiente

Requer Python 3.14 ou uma versão compatível com as dependências.

```powershell
git clone https://github.com/MatheusLeonardi/TransitGraph.git
cd TransitGraph
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. Usar o banco incluído ou reconstruí-lo

O checkout inclui o banco pronto para a demonstração. Para reconstruí-lo, o ZIP padrão deve estar em `data/raw/_sptrans_gtfs.zip`. A data deve estar no
período de validade de `calendar.txt`.

```powershell
python scripts/build_graph.py --date 2026-11-01
```

Também é possível informar caminhos diferentes.

```powershell
python scripts/build_graph.py `
  --date 2026-11-01 `
  --gtfs D:\dados\sptrans_gtfs.zip `
  --database data\processed\transitgraph.db
```

Para iniciar a aplicação com outro banco, defina `TRANSITGRAPH_DATABASE`
com o caminho desse arquivo antes de executar `python run.py`.

Esse comando importa o GTFS, constrói o grafo e salva o banco SQLite usado pela
aplicação. As geometrias são compactadas no banco para reduzir o tamanho sem
perder o traçado fornecido pela SPTrans.

### 3. Iniciar a aplicação

```powershell
python run.py
```

Acesse [http://127.0.0.1:5000](http://127.0.0.1:5000).

Para desenvolvimento com recarregamento automático no PowerShell:

```powershell
$env:TRANSITGRAPH_DEBUG = "1"
python run.py
```

## Testes realizados

### Como rodar

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/benchmark.py --output docs/BENCHMARK_RESULTADOS.md
```

Os testes do item 4.5 do enunciado ficam em `tests/test_requisitos.py`, com
uma classe por categoria. Para rodar só uma categoria, use `-k`, por exemplo
`python -m pytest tests/test_requisitos.py -v -k Fronteira`.

### Resultado da execução

**152 testes aprovados** em 24,08 s: 67 já existentes e 85 novos em
`tests/test_requisitos.py`. Ambiente: Python 3.13.15, pytest 9.2.0,
networkx 3.7, Windows 11.

| Categoria do enunciado | O que foi testado | Arquivo de teste | Resultado |
|---|---|---|---|
| Casos simples com resultado verificável | Mini rede de 6 paradas com ciclo e atalho. A ordem de visita da BFS e da DFS, a ordem de finalização, o caminho e as arestas examinadas estão escritos à mão no teste. Inclui a volta `B → A`, que precisa contornar o ciclo pelo sentido das arestas | `test_requisitos.py::TestCasosSimples`; também `test_bfs.py`, `test_dfs.py`, `test_algorithms.py` | 4 aprovados |
| Casos sem solução | Destino com aresta só no sentido contrário (`D → A` existe, `A → D` não). Destino isolado, em que a busca esgota todo o alcance antes de falhar. Origem ou destino inexistente nas combinações que faltavam | `TestSemSolucao`; também `test_traversals.py` | 8 aprovados |
| Situações de fronteira | Grafo vazio. Origem igual ao destino dentro de um ciclo, sem examinar arestas. Parada sem arestas de saída. Ciclo `A → B → C → A` a partir de cada vértice. Auto-laço, aceito pelo modelo e ausente na rede real. Cadeia de 50.000 vértices, acima do limite de recursão de 1.000 do Python, para provar que a DFS iterativa não estoura | `TestFronteira`; também `test_traversals.py` | 12 aprovados |
| Instâncias de diferentes tamanhos | Grafos dirigidos aleatórios com seed fixa, de 8, 60, 500, 2.000, 5.000 e 20.000 vértices, com 0,5 a 3 arestas por vértice. Instâncias reais pequena, intermediária e completa do SQLite | `TestPropriedades`, `TestValidacaoNetworkx`, `TestRedeReal` | os mesmos 51 testes da linha seguinte |
| Validação da correção dos resultados | Propriedades: sem destino, BFS e DFS alcançam o mesmo conjunto; todo caminho usa só arestas existentes, no sentido certo; o caminho da BFS nunca é maior que o da DFS. Oráculo networkx: distância da BFS igual a `shortest_path_length`; alcance da DFS igual a `descendants` mais a origem; ordens de visita e finalização iguais, posição a posição, às de `bfs_edges`, `dfs_preorder_nodes` e `dfs_postorder_nodes` | `TestPropriedades` (24), `TestValidacaoNetworkx` (18), `TestRedeReal` (9) | 51 aprovados |
| Análise do tempo de execução | Nos grafos do benchmark, de 1.000 a 100.000 vértices, cada busca processa exatamente V vértices e examina exatamente E arestas. Os tempos ficam no benchmark abaixo | `TestDesempenho`; `scripts/benchmark.py` | 10 aprovados |

Os testes da rede real usam `data/processed/transitgraph.db`. Sem o banco, eles
aparecem como ignorados (`skipped`) e os demais continuam rodando.

> **Sobre a networkx.** A biblioteca é usada somente nos testes, como validação
> independente: os testes comparam as respostas da BFS e da DFS do projeto com
> as que a networkx calcula sobre uma cópia do mesmo grafo. Ela não substitui
> as implementações próprias em `backend/algorithms/bfs.py` e
> `backend/algorithms/dfs.py`, que são as usadas pela aplicação.

### Desempenho

Travessia completa (sem destino), mediana de 21 repetições. Os grafos
aleatórios formam um ciclo dirigido com atalhos sorteados, com E = 1,3·V como
na rede real, e são alcançáveis por inteiro a partir da origem. Nas instâncias
reais, a busca parte da origem de referência de cada recorte.

| Instância | Vértices | Arestas | Mediana BFS | Mediana DFS |
|---|---:|---:|---:|---:|
| Aleatória | 1.000 | 1.300 | 0,2416 ms | 0,3712 ms |
| Aleatória | 5.000 | 6.500 | 1,3547 ms | 2,1011 ms |
| Aleatória | 20.000 | 26.000 | 10,2559 ms | 10,6555 ms |
| Aleatória | 50.000 | 65.000 | 61,1490 ms | 92,4432 ms |
| Aleatória | 100.000 | 130.000 | 97,2056 ms | 363,5862 ms |
| Real · pequena | 7 | 6 | 0,0051 ms | 0,0069 ms |
| Real · intermediária | 177 | 181 | 0,0664 ms | 0,1542 ms |
| Real · completa | 20.812 | 27.218 | 19,1989 ms | 25,5274 ms |

O número de operações cresce exatamente como V + E, e o tempo acompanha esse
crescimento enquanto o grafo cabe no cache do processador. De 1.000 para 5.000
vértices, o trabalho cresceu 5,0 vezes e as medianas 5,6 (BFS) e 5,7 vezes
(DFS), expoente 1,07 e 1,08. Acima de 20.000 vértices, cada operação fica mais
cara e o expoente ajustado de 1.000 a 100.000 vai a 1,37 (BFS) e 1,48 (DFS). A
causa é memória, não operações a mais. Estimadas com `sys.getsizeof`, as
estruturas que a busca percorre ocupam cerca de 5 MiB com 20.000 vértices e
15 MiB com 50.000, acima dos 12 MB de cache L3 do processador usado (Intel
Core i5-1334U). As medições foram feitas num notebook na bateria. Os tempos
dos grafos maiores variam entre execuções: a BFS com 100.000 vértices levou
97,2 ms nesta e 168,6 ms numa execução anterior. O padrão de crescimento se
repetiu. Consulte os [resultados completos](docs/BENCHMARK_RESULTADOS.md),
com consultas com destino, custo por operação e pico de memória.

### Extensão: menor tempo com Dijkstra

O Dijkstra não fazia parte do objetivo do Tema 1, que trata de BFS e DFS. Ele
foi incluído por sugestão do professor, para comparar a rota com **menos
paradas** (BFS) com a de **menor tempo estimado** (Dijkstra) na mesma rede.

Execução real na rede completa (20.812 vértices, 27.218 arestas, data de
serviço 01/11/2026), da origem `600012584` ao destino `3609172`:

| Algoritmo | Arestas | Tempo estimado |
|---|---:|---:|
| BFS (menos paradas) | 34 | 4.046,0 s (67,4 min) |
| Dijkstra (menor tempo) | 39 | 3.380,5 s (56,3 min) |

O caminho do Dijkstra tem 5 arestas a mais e leva 665,5 s (cerca de 11 min) a
menos. O tempo da BFS é a soma dos pesos das arestas do caminho que ela
encontrou, pela mesma regra do Dijkstra.

O peso de cada aresta é a mediana do tempo programado no GTFS entre a partida
de uma parada e a chegada à seguinte, considerando as viagens ativas na data
de serviço. Nesse par, todas as arestas dos dois caminhos têm peso do GTFS, e
a estimativa geográfica de 18 km/h não foi usada. O tempo não inclui espera no
ponto, caminhada nem baldeação.

Para reproduzir:

```powershell
python scripts/compare_bfs_dijkstra.py 600012584 3609172
```

## Estrutura principal

```text
backend/
  algorithms/       # grafo, BFS, DFS, Dijkstra e conectividade
  gtfs/              # importação e filtragem por data
  models/            # persistência SQLite
  app.py             # API Flask
frontend/
  templates/         # interface HTML
  static/            # CSS e JavaScript
scripts/
  build_graph.py     # GTFS -> grafo -> SQLite
  benchmark.py       # medições reproduzíveis de BFS e DFS
  compare_bfs_dijkstra.py  # menos paradas (BFS) × menor tempo (Dijkstra)
tests/               # testes automatizados; test_requisitos.py cobre o item 4.5
run.py               # inicialização da aplicação
```

## Limitações

- a BFS minimiza arestas, não tempo, distância geográfica ou transferências;
- o Dijkstra soma o tempo programado entre paradas consecutivas no GTFS; não
  inclui espera de baldeação nem trânsito em tempo real;
- quando o GTFS não oferece horário para uma conexão, o Dijkstra estima o
  tempo a partir da distância reta entre coordenadas, usando 18 km/h, e informa
  quantos trechos da rota usaram essa estimativa;
- depois de obter o menor caminho, o itinerário escolhe entre as linhas de cada
  aresta procurando reduzir baldeações, sem alterar o resultado da BFS;
- o modelo atual não inclui trânsito, horários em tempo real ou caminhada;
- o refinamento viário público depende da disponibilidade do OSRM, mantendo
  fallback integral para o GTFS;
- o cache do refinamento viário fica em `data/runtime/road_cache.db`, separado
  do banco versionado do grafo;
- componentes fracos ignoram a direção das arestas durante essa análise;
- a interface e a API retornam até 200 registros de cada ordem e mantêm as
  contagens completas;
- o importador usa as regras semanais de `calendar.txt`. Exceções de calendário
  de outros feeds e frequências do serviço ficam fora do modelo atual;
- Leaflet, Cytoscape.js e o mapa-base usam recursos externos. As buscas e os
  resultados textuais também funcionam com o navegador sem acesso externo.

## Dados e instâncias

O ZIP versionado identifica a SPTrans em `agency.txt` e aponta para a versão
`311026`. A data de serviço desta auditoria é **01/11/2026**. O
`calendar.txt` do ZIP declara validade de 01/10/2023 a 01/05/2027.
[SPTrans](https://www.sptrans.com.br/desenvolvedores) ·
[GTFS Schedule Reference](https://gtfs.org/documentation/schedule/reference/).

O seletor usa a mesma base SQLite. Cada recorte preserva os sentidos
das conexões presentes no GTFS.

| Instância | Critério | Paradas | Conexões |
|---|---|---:|---:|
| Pequena | Subgrafo induzido pelas paradas a até duas arestas direcionadas da origem `480012875`, Vila Leopoldina | 7 | 6 |
| Intermediária | Arestas atendidas pelas linhas `2025-10` ou `172K-10` | 177 | 181 |
| Grande | Rede de ônibus completa para a data de serviço | 20.812 | 27.218 |

Os recortes delimitam o alcance e as alternativas de trajeto. No recorte de
linhas, o Dijkstra usa os pesos por aresta da rede completa. Em outro banco,
a disponibilidade dos recortes depende da parada e das linhas de referência.

