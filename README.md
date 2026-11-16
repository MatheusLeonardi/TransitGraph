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

## Testes

```powershell
python -m pytest -v
```

Os testes cobrem ciclos, direção, origem igual ao destino, isolamento,
alternativas de comprimentos diferentes, ordem de adjacência, retornos e DFS
com 5.000 vértices em cadeia. Também cobrem API, recortes, persistência, importação
e refinamento viário.

## Benchmark reproduzível

Para medir BFS e DFS nas três instâncias do GTFS, com e sem destino:

```powershell
python scripts/benchmark.py --output docs/BENCHMARK_RESULTADOS.md
```

O script registra medianas, contagens e pico de alocações Python por busca.
O carregamento, a montagem dos recortes e a renderização ficam fora da medição.
Consulte os [resultados do benchmark](docs/BENCHMARK_RESULTADOS.md).

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

