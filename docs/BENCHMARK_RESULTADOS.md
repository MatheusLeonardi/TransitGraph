# Benchmark de BFS e DFS

- Execução em 2026-11-14T14:53:32-03:00, horário de São Paulo.
- Python 3.14.0, Windows-11-10.0.26200-SP0, AMD64 Family 25 Model 33 Stepping 2, AuthenticAMD.
- Data de serviço do banco registrada como 2026-11-01.
- Uma execução de aquecimento e mediana de 21 repetições por algoritmo e consulta.
- Tempos medidos após carregar o SQLite e construir os recortes. A medição inclui a construção do resultado da busca, com geometria, API e renderização fora do intervalo.
- Pico de alocações Python em execução adicional com tracemalloc, em KiB. O grafo já estava em memória. A medição cobre a alocação incremental da busca.

## Pequena · Dois níveis na Vila Leopoldina

7 vértices e 6 arestas. Origem 480012875.

| Consulta | Busca | Mediana (ms) | Pico (KiB) | Descobertas | Visitas | Arestas examinadas | Arestas do caminho |
|---|---|---:|---:|---:|---:|---:|---:|
| Alcance completo | BFS | 0.0023 | 1.6 | 7 | 7 | 6 | — |
| Alcance completo | DFS | 0.0032 | 1.0 | 7 | 7 | 6 | — |
| Até 480014889 | BFS | 0.0021 | 1.7 | 7 | 4 | 6 | 2 |
| Até 480014889 | DFS | 0.0016 | 1.0 | 3 | 3 | 2 | 2 |

## Intermediária · Linhas 2025-10 e 172K-10

177 vértices e 181 arestas. Origem 8812664.

| Consulta | Busca | Mediana (ms) | Pico (KiB) | Descobertas | Visitas | Arestas examinadas | Arestas do caminho |
|---|---|---:|---:|---:|---:|---:|---:|
| Alcance completo | BFS | 0.0414 | 12.2 | 177 | 177 | 181 | — |
| Alcance completo | DFS | 0.0727 | 16.9 | 177 | 177 | 181 | — |
| Até 940004410 | BFS | 0.0085 | 2.6 | 32 | 31 | 31 | 25 |
| Até 940004410 | DFS | 0.0394 | 11.7 | 105 | 105 | 107 | 25 |

## Grande · Rede completa

20.812 vértices e 27.218 arestas. Origem 480012875.

| Consulta | Busca | Mediana (ms) | Pico (KiB) | Descobertas | Visitas | Arestas examinadas | Arestas do caminho |
|---|---|---:|---:|---:|---:|---:|---:|
| Alcance completo | BFS | 7.2236 | 695.6 | 20534 | 20534 | 26938 | — |
| Alcance completo | DFS | 10.6939 | 1164.8 | 20534 | 20534 | 26938 | — |
| Até 480014632 | BFS | 0.2119 | 44.5 | 742 | 640 | 964 | 16 |
| Até 480014632 | DFS | 7.3982 | 1164.4 | 14065 | 14065 | 17347 | 3225 |

Na travessia completa, compare as contagens das duas buscas partindo da mesma origem. Em consultas com destino, as ordens de visita determinam quanto trabalho cada busca faz antes de parar. A BFS encerra ao retirar o destino da fila e a DFS ao descobri-lo.

As diferenças de tempo refletem este computador, o alcance de cada origem e a instrumentação de cada algoritmo. As medições das três instâncias ilustram a escala do trabalho executado. O limite assintótico depende dos vértices e arestas examinados.
