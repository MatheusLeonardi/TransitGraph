# Roteiro de apresentação — TransitGraph

Sugestão de duração: 12 a 15 minutos, seguida de perguntas.

## Integrante 1 — problema e dados

- apresentar o problema de conectividade da rede de ônibus;
- explicar que os dados são GTFS da SPTrans;
- mostrar a escala: 20.812 vértices e 27.218 arestas;
- definir cada parada como vértice e cada deslocamento consecutivo como aresta
  direcionada.

## Integrante 2 — representação do grafo

- explicar a lista de adjacência;
- mostrar que uma aresta pode ser atendida por várias linhas;
- justificar por que o grafo é direcionado;
- explicar a persistência no SQLite e a geometria do `shapes.txt`.

## Integrante 3 — BFS

- explicar a fila e a exploração por níveis;
- apresentar complexidade `O(V + E)`;
- demonstrar que a BFS garante o menor caminho em quantidade de arestas;
- deixar claro que isso não significa menor tempo de viagem.

## Integrante 4 — DFS

- explicar a pilha e o aprofundamento antes do retrocesso;
- apresentar complexidade `O(V + E)`;
- relacionar a DFS à análise de alcançabilidade;
- comparar a ordem de visita com a BFS.

## Integrante 5 — aplicação, resultados e limitações

- mostrar mapa, linhas, baldeações e sentido;
- apresentar componentes fracamente conexos;
- explicar validação das geometrias;
- concluir com limitações e possíveis extensões.

## Demonstrações preparadas

### 1. Trajeto com linhas e baldeação

- origem: `8812664` — Sesc Santana;
- destino: `940004410` — Av. Júlio Buono, 2007;
- resultado esperado: 25 arestas, linhas `2025-10` e `172K-10`, uma
  baldeação e geometria GTFS no mapa.

### 2. Diferença clara entre BFS e DFS

- origem: `480012875` — R. Br. de Jundiaí, 545;
- destino: `480014632` — R. Pio XI, 571;
- resultado observado na base de 01/11/2026:
  - BFS: 16 arestas;
  - DFS: 1.114 arestas.

Esse caso evidencia que a DFS pode encontrar um caminho válido muito maior,
enquanto a BFS garante o menor caminho no grafo não ponderado.

### 3. Ausência de caminho direcionado

- origem: `560009135` — Av. Jaceguava, 1354;
- destino: `5506671` — Av. Morumbi, 5595;
- resultado esperado: nenhum caminho direcionado encontrado.

## Perguntas prováveis

### Por que não usar Dijkstra?

O tema exige BFS e DFS. Como as arestas não possuem peso no modelo principal,
a BFS é suficiente para minimizar a quantidade de conexões. Dijkstra seria uma
extensão para tempo ou distância ponderada.

### A linha no mapa respeita as ruas?

Ela utiliza a sequência oficial do `shapes.txt`. A associação parada–shape é
monotônica e rejeita distâncias acima de 150 metros. O sistema não faz uma
validação independente das tags `oneway` do OpenStreetMap.

### A rota é a mais rápida?

Não. Ela possui o menor número de arestas. O sistema não considera trânsito,
tempo de espera ou horários em tempo real.

### Como as baldeações são escolhidas?

Depois que a BFS define o caminho de paradas, uma programação dinâmica escolhe
entre as linhas disponíveis em cada aresta procurando reduzir trocas, sem
alterar o caminho encontrado pela BFS.

## Checklist antes de apresentar

- reconstruir o banco com a mesma data usada no relatório;
- executar `python -m pytest -q`;
- testar os três exemplos acima;
- abrir o mapa antes da apresentação;
- manter uma captura de tela como alternativa para falhas de internet;
- confirmar que cada integrante conhece sua parte e a limitação da BFS.
