# Benchmark de BFS e DFS

- Execução em 2026-11-16T13:35:51-03:00, horário de São Paulo.
- Python 3.13.15, Windows-11-10.0.26200-SP0, Intel64 Family 6 Model 186 Stepping 3, GenuineIntel.
- Data de serviço do banco registrada como 2026-11-01.
- Uma execução de aquecimento e mediana de 21 repetições por algoritmo e consulta.
- Tempos medidos após carregar o SQLite e construir os grafos. A medição inclui a construção do resultado da busca, com geometria, API e renderização fora do intervalo.
- Pico de alocações Python em execução adicional com tracemalloc, em KiB. O grafo já estava em memória. A medição cobre a alocação incremental da busca.
- Grafos aleatórios: ciclo dirigido em ordem aleatória mais atalhos sorteados até E = round(1.3·V), seed 2026. O ciclo garante que a travessia a partir do vértice "0" alcance todo o grafo.

## Travessia completa

Sem destino, cada busca percorre todo o alcance da origem. O trabalho soma os vértices processados e as arestas examinadas. Nos grafos aleatórios ele vale exatamente V + E. Nas instâncias reais conta apenas a parte alcançável da origem de referência.

| Instância | Vértices | Arestas | Trabalho | Mediana BFS (ms) | Mediana DFS (ms) | BFS (ns/unidade) | DFS (ns/unidade) | Pico BFS (KiB) | Pico DFS (KiB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Aleatória | 1000 | 1300 | 2300 | 0.2416 | 0.3712 | 105 | 161 | 45.2 | 112.9 |
| Aleatória | 5000 | 6500 | 11500 | 1.3547 | 2.1011 | 118 | 183 | 176.0 | 698.7 |
| Aleatória | 20000 | 26000 | 46000 | 10.2559 | 10.6555 | 223 | 232 | 703.9 | 3133.9 |
| Aleatória | 50000 | 65000 | 115000 | 61.1490 | 92.4432 | 532 | 804 | 3182.9 | 8886.0 |
| Aleatória | 100000 | 130000 | 230000 | 97.2056 | 363.5862 | 423 | 1581 | 6365.8 | 17835.8 |
| Pequena · Dois níveis na Vila Leopoldina | 7 | 6 | 13 | 0.0051 | 0.0069 | 392 | 531 | 1.4 | 0.8 |
| Intermediária · Linhas 2025-10 e 172K-10 | 177 | 181 | 358 | 0.0664 | 0.1542 | 185 | 431 | 12.2 | 16.9 |
| Grande · Rede completa | 20812 | 27218 | 47472 | 19.1989 | 25.5274 | 404 | 538 | 695.6 | 1150.0 |

## Crescimento com o tamanho

| Faixa de vértices | Trabalho | Mediana BFS | Mediana DFS | Expoente BFS | Expoente DFS |
|---|---:|---:|---:|---:|---:|
| 1.000 → 5.000 | ×5.0 | ×5.6 | ×5.7 | 1.07 | 1.08 |
| 5.000 → 20.000 | ×4.0 | ×7.6 | ×5.1 | 1.46 | 1.17 |
| 20.000 → 50.000 | ×2.5 | ×6.0 | ×8.7 | 1.95 | 2.36 |
| 50.000 → 100.000 | ×2.0 | ×1.6 | ×3.9 | 0.67 | 1.98 |
| 1.000 → 100.000, ajuste | ×100.0 | ×402.3 | ×979.5 | 1.37 | 1.48 |

O expoente compara o crescimento da mediana com o do trabalho. Na última linha ele vem de mínimos quadrados sobre log(tempo) e log(V + E). Expoente 1 é crescimento linear, como prevê O(V + E). Como o trabalho vale exatamente V + E em todos os tamanhos, um expoente acima de 1 indica que cada operação ficou mais cara, por exemplo quando as estruturas deixam de caber no cache do processador, e não que a busca executou operações extras.

## Pequena · Dois níveis na Vila Leopoldina

7 vértices e 6 arestas. Origem 480012875.

| Consulta | Busca | Mediana (ms) | Pico (KiB) | Descobertas | Visitas | Arestas examinadas | Arestas do caminho |
|---|---|---:|---:|---:|---:|---:|---:|
| Alcance completo | BFS | 0.0051 | 1.4 | 7 | 7 | 6 | — |
| Alcance completo | DFS | 0.0069 | 0.8 | 7 | 7 | 6 | — |
| Até 480014889 | BFS | 0.0047 | 1.9 | 7 | 4 | 6 | 2 |
| Até 480014889 | DFS | 0.0034 | 0.8 | 3 | 3 | 2 | 2 |

## Intermediária · Linhas 2025-10 e 172K-10

177 vértices e 181 arestas. Origem 8812664.

| Consulta | Busca | Mediana (ms) | Pico (KiB) | Descobertas | Visitas | Arestas examinadas | Arestas do caminho |
|---|---|---:|---:|---:|---:|---:|---:|
| Alcance completo | BFS | 0.0664 | 12.2 | 177 | 177 | 181 | — |
| Alcance completo | DFS | 0.1542 | 16.9 | 177 | 177 | 181 | — |
| Até 940004410 | BFS | 0.0191 | 2.9 | 32 | 31 | 31 | 25 |
| Até 940004410 | DFS | 0.0833 | 11.7 | 105 | 105 | 107 | 25 |

## Grande · Rede completa

20.812 vértices e 27.218 arestas. Origem 480012875.

| Consulta | Busca | Mediana (ms) | Pico (KiB) | Descobertas | Visitas | Arestas examinadas | Arestas do caminho |
|---|---|---:|---:|---:|---:|---:|---:|
| Alcance completo | BFS | 19.1989 | 695.6 | 20534 | 20534 | 26938 | — |
| Alcance completo | DFS | 25.5274 | 1150.0 | 20534 | 20534 | 26938 | — |
| Até 480014632 | BFS | 0.4470 | 44.5 | 742 | 640 | 964 | 16 |
| Até 480014632 | DFS | 15.2376 | 1150.0 | 14065 | 14065 | 17347 | 3225 |

Na travessia completa, compare as contagens das duas buscas partindo da mesma origem. Em consultas com destino, as ordens de visita determinam quanto trabalho cada busca faz antes de parar. A BFS encerra ao retirar o destino da fila e a DFS ao descobri-lo.

As diferenças de tempo refletem este computador, o alcance de cada origem e a instrumentação de cada algoritmo. O limite assintótico depende dos vértices e arestas examinados.
