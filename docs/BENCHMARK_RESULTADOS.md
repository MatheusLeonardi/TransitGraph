# Resultados de benchmark

- Executado em: 2026-11-02T20:56:48-03:00
- Python: 3.14.0
- Sistema: Windows-11-10.0.26200-SP0
- Processador: AMD64 Family 25 Model 33 Stepping 2, AuthenticAMD
- Banco: `D:\transitgraph\data\processed\transitgraph.db`
- Data de servico do grafo: 2026-11-01
- Semente pseudoaleatoria: 42
- Pares aleatorios no grafo real: 30
- Repeticoes por grafo sintetico: 5

## Grafo real

| Vertices | Arestas | BFS origem-destino (mediana) | DFS completa (mediana) |
| ---: | ---: | ---: | ---: |
| 20.812 | 27.218 | 6,54 ms | 12,58 ms |

## Grafos sinteticos

| Vertices | Arestas | BFS completa (mediana) | DFS completa (mediana) |
| ---: | ---: | ---: | ---: |
| 1.000 | 1.997 | 0,45 ms | 0,51 ms |
| 5.000 | 9.997 | 2,63 ms | 2,93 ms |
| 20.000 | 39.997 | 10,91 ms | 11,73 ms |
| 50.000 | 99.997 | 26,72 ms | 30,20 ms |
| 100.000 | 199.997 | 56,85 ms | 67,07 ms |
| 200.000 | 399.997 | 134,78 ms | 164,84 ms |

Os tempos dependem do computador e devem ser regenerados no ambiente usado na apresentacao.
