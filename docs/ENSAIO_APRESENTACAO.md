# Ensaio da apresentação do TransitGraph

Entrega em **17/11/2026**. Planejem **10:00**, com **3:20 de demonstração**.
Antes de começar, deixem o navegador, o PowerPoint e o editor abertos.
Preparem os dois arquivos nos pontos indicados no mapa do código.

| Tempo | Quem conduz | Ação e explicação |
|---|---|---|
| 0:00–1:05 | Integrante 1 | Slides 1–2. Apresente os integrantes e as perguntas de caminho e cobertura. |
| 1:05–2:25 | Integrante 2 | Slides 3–4. Mostre os tamanhos, a data e o sentido das arestas. Aponte `Graph.add_edge` se perguntado. |
| 2:25–3:15 | Integrante 3 | Slide 5 e `bfs.py`, linhas 12–39. Aponte `deque`, `popleft` e `parent`. Mencione que o caminho emerge da cadeia de pais nas linhas 49–55. |
| 3:15–4:05 | Integrante 4 | Slide 6 e `dfs.py`, linhas 10–27. Aponte quadro, iterador, `break` e finalização. Volte ao slide até 4:05. |
| 4:05–4:50 | Integrante 5 | Slide 7. Explique 16 e 3.225 arestas na mesma consulta. |
| 4:50–5:55 | Integrante 1 abre. 3 e 4 explicam. | Compare as ordens na pequena. Rode DFS sem destino e abra as finalizações. |
| 5:55–6:45 | Integrante 2 seleciona. 3 explica. | Na intermediária, execute BFS e mostre as 25 conexões e uma troca. |
| 6:45–8:10 | Integrante 4 explica a cobertura. 5 fecha a consulta. | Na completa, mostre 20 alcançáveis e depois a ausência de caminho. |
| 8:10–10:00 | Integrante 5 | Slides 9–10. Resuma testes e limites do modelo. |

O integrante 5 pode operar o computador durante as trocas. Como meta de
ensaio, reservem aproximadamente 1:15, 1:35, 1:45, 2:15 e 3:10 de contribuição
por integrante, respectivamente. O cronograma inclui a operação da demo.
Se atrasar, encerrem a demonstração às 8:10 e leiam o resultado esperado do
caso que faltou.

## Consultas e plano alternativo

- **Pequena:** `480012875 → 480014889`. Duas arestas em ambas. A BFS visita
  `4811488` antes do destino, e a DFS chega ao destino sem passar por
  `4811488`. Sem destino, sete descobertas e sete finalizações.
- **Intermediária:** `8812664 → 940004410`. BFS com 25 arestas e uma troca,
  da linha 2025-10 para a 172K-10.
- **Completa:** `560009135` sem destino alcança 20 paradas. Ao definir
  `5506671`, ambas encerram sem caminho, cada uma com 20 visitas.
- **Discussão ou banca:** completa `480012875 → 480014632`. BFS 16 arestas
  e 640 visitas. DFS 3.225 arestas e 14.065 visitas.

Desliguem o OSRM no ensaio principal. Se o mapa falhar, mostrem caminho e
ordens na tela. Se o navegador falhar, usem a API via PowerShell e a captura
do recorte pequeno. [Comandos e saída esperada](ROTEIRO_APRESENTACAO.md) ·
[Captura de comparação](apresentacao/comparacao-pequena.png)

## Simulação de banca

| Quem pratica | Pergunta que o professor pode fazer | Resposta esperada |
|---|---|---|
| 1 | 1. Quais problemas o TransitGraph resolve? | Caminho com menos conexões e cobertura direcionada a partir de uma parada. |
| 1 | 2. Onde o clique vira uma consulta? | `app.js` 1079–1089 liga os botões. `executeBFS` envia o POST na linha 533. |
| 1 | 3. O mapa precisa carregar para ver o resultado? | Caminhos e ordens são apresentados no HTML com a API local. |
| 2 | 4. Onde se vê a orientação? | `Graph.add_edge` insere o destino na adjacência da origem em `graph.py` 64–79. |
| 2 | 5. Quando se lê o banco? | Na inicialização em `create_app`, chamada na linha 93. Cada requisição seleciona a instância em 100–106. |
| 2 | 6. Onde ficam as linhas que atendem a aresta? | Em `edge_routes`. A mesma aresta pode guardar várias linhas e ocorrências. |
| 3 | 7. Por que `popleft` é importante? | Na linha 24, remove a entrada antiga e preserva a ordem dos níveis. |
| 3 | 8. Por que marcar na descoberta? | `parent[neighbor]` na linha 37 precede `queue.append`, evitando inserção duplicada. |
| 3 | 9. O que `path.reverse()` faz? | A cadeia começa no destino. A linha 55 põe o resultado na ordem origem → destino. |
| 3 | 10. Por que a BFS dá o mínimo? | Com custo unitário, todo caminho mais curto teria sido descoberto por um nível anterior. |
| 4 | 11. O que entra na pilha da DFS? | O par vértice e iterador sobre seus vizinhos, nas linhas 10 e 23. |
| 4 | 12. O que o `break` da linha 24 evita? | A marcação antecipada dos irmãos. O quadro do pai espera a exploração do filho. |
| 4 | 13. Quando um vértice termina? | O iterador esgota e `stack.pop()` antecede `finish_order.append(current)`, linhas 25–27. |
| 4 | 14. Por que usar uma pilha explícita? | Permite conservar o estado da adjacência e controlar o retorno sem depender do limite de recursão. |
| 5 | 15. Onde as duas buscas são comparadas? | `compare_algorithms` em `app.py`, chamadas 341 e 345 com as mesmas entradas. |
| 5 | 16. O que 3.225 mede? | Arestas do primeiro caminho localizado pela DFS nessa consulta e nessa ordem de adjacência. |
| 5 | 17. Por que a cobertura e a componente fraca diferem? | A cobertura segue o sentido de saída a partir da origem. A componente fraca ignora os sentidos. |
| 5 | 18. O OSRM pode alterar uma rota BFS? | `prepare_algorithm_result` passa a geometria do itinerário ao refinamento depois de obter o caminho. As paradas do caminho já estão decididas. |

Todos leem o [mapa do código](MAPA_DO_CODIGO.md) e reproduzem ao menos uma
consulta sem apoio. Durante o ensaio, cada pessoa deve localizar a linha
que fundamenta sua resposta e descrevê-la em até 30 segundos.

## Checklist de entrega

- Confiram os cinco nomes, RAs e contribuições no DOCX e os nomes na capa oficial.
- Confirmem a data de coleta do GTFS, o escopo aprovado e a revisão humana do uso de IA.
- Reexportem o PDF depois de preencher os campos destacados.
- Ensaiem com os slides 5 e 6 e abram as linhas correspondentes no editor.
- Testem as três consultas no computador da sala e cronometrem a demo até 8:10.
- Deixem o PowerShell e as capturas prontos para demonstrar sem o mapa.
