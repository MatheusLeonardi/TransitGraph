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

Com o GTFS incluído e a data `2026-11-01`, o grafo possui 20.812 vértices e
27.218 arestas direcionadas.

## Papel dos algoritmos

### BFS — menor quantidade de conexões

A BFS explora o grafo em níveis usando uma fila. No TransitGraph, ela encontra
um caminho entre origem e destino com o menor número de arestas. Como o grafo
não possui pesos, isso significa menor quantidade de conexões entre paradas,
mas não necessariamente menor tempo de viagem.

### DFS — exploração e alcançabilidade

A DFS usa uma pilha e aprofunda um ramo antes de retroceder. Ela é utilizada
para identificar as paradas alcançáveis a partir de uma origem. Quando recebe
um destino, também pode encontrar um caminho, mas não garante que ele seja o
menor.

### Comparação

| Característica | BFS | DFS |
|---|---|---|
| Estrutura | Fila | Pilha |
| Estratégia | Explora por níveis | Aprofunda um ramo |
| Menor caminho não ponderado | Garante | Não garante |
| Uso no projeto | Rota com menos arestas | Alcançabilidade e exploração |
| Complexidade | `O(V + E)` | `O(V + E)` |
| Memória assintótica | `O(V)` | `O(V)` |

A interface mostra, para cada algoritmo, a ordem numerada de visita, o total
de vértices descobertos e processados, o caminho e o tempo de execução.

## Qualidade da geometria

As paradas são associadas aos pontos do `shapes.txt` por programação dinâmica,
buscando a melhor sequência monotônica global. Associações acima de 150 metros
são rejeitadas e desenhadas com o fallback simplificado, evitando trajetos que
saltem para regiões incorretas.

Na base de 01/11/2026, 76.651 referências de aresta possuem geometria validada
e 60 foram rejeitadas. Entre as referências aceitas, a distância mediana entre
parada e shape é 12,1 metros e o percentil 95 é 48,4 metros.

Quando um shape possui intervalos maiores que 60 metros, a aplicação tenta
refinar o traçado com o serviço de *map matching* do OSRM sobre a malha do
OpenStreetMap. O resultado só é aceito quando preserva extremos, comprimento,
sentido e proximidade do corredor original. Geometrias aprovadas são mantidas
em cache no SQLite; qualquer falha utiliza automaticamente o shape GTFS.

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

### 2. Construir o banco a partir do GTFS

O ZIP padrão deve estar em `data/raw/_sptrans_gtfs.zip`. A data deve estar no
período de validade de `calendar.txt`.

```powershell
python scripts/build_graph.py --date 2026-11-01
```

Também é possível informar caminhos diferentes:

```powershell
python scripts/build_graph.py `
  --date 2026-11-01 `
  --gtfs D:\dados\sptrans_gtfs.zip `
  --database data\processed\transitgraph.db
```

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

## Testes

```powershell
python -m pytest -v
```

Os testes cobrem os algoritmos, ordem de visita, entradas inválidas,
componentes conexos, persistência das geometrias, refinamento viário e a API
de comparação.

## Benchmark reproduzível

Para medir BFS e DFS no banco real e em grafos sintéticos:

```powershell
python scripts/benchmark.py --output docs/BENCHMARK_RESULTADOS.md
```

O script usa semente fixa, registra o ambiente da execução e calcula medianas
de várias medições. Os tempos variam conforme o computador; portanto, o grupo
deve executar novamente esse comando na máquina usada na apresentação.

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
tests/               # testes automatizados
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
- a interface limita a ordem exibida às primeiras 200 visitas para manter a
  resposta legível, preservando o total processado.

## Dados

Antes de redistribuir o GTFS, confirme os termos de uso e atribuição da fonte.
Registre no relatório a data de obtenção do arquivo, a data de serviço usada e
as estatísticas geradas pelo comando de construção.
