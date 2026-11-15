# Guia de defesa do TransitGraph

**Tema 1 · Representação e Busca em Grafos · Banca de 17/11/2026**

Este guia usa a `main` no commit `c858131` e o GTFS da SPTrans com data
de serviço de **01/11/2026**. Para abrir as linhas de BFS e DFS durante a
banca, use o [mapa do código](MAPA_DO_CODIGO.md). Para a divisão completa
das falas, use o [ensaio](ENSAIO_APRESENTACAO.md).

## Explique a aplicação apontando para o código

| Funcionalidade | Arquivo e símbolo | Resposta oral |
|---|---|---|
| Problema real | [API](../backend/app.py#L240), `run_bfs` e `run_dfs` | “O TransitGraph responde a duas perguntas sobre a rede de ônibus. A BFS encontra um caminho com menos conexões entre duas paradas. A DFS mostra a cobertura dirigida de uma origem e a ordem dos retornos.” |
| Vértices e arestas | [Grafo](../backend/algorithms/graph.py#L64), `Graph.add_stop` e `Graph.add_edge` | “Cada código de parada é um vértice. Se uma viagem ativa atende uma parada imediatamente depois de outra, inserimos uma aresta no sentido da viagem. Uma mesma aresta pode estar associada a várias linhas.” |
| GTFS | [Importador](../backend/gtfs/importer.py#L160), `import_gtfs`. [Calendário](../backend/gtfs/service_filter.py#L2), `get_active_service_ids` | “Selecionamos viagens de ônibus ativas no calendário semanal, agrupamos por viagem e ordenamos as paradas por stop_sequence. As ocorrências, com viagem, sentido e shape, são preservadas para montar o itinerário.” |
| Banco e instâncias | [SQLite](../backend/models/database.py#L274), `load_graph`. [Recortes](../backend/services/instance_service.py#L15), `build_instances`. [Flask](../backend/app.py#L73), `create_app` e `select_instance` | “O SQLite guarda a rede e os metadados. Flask carrega o grafo na inicialização e escolhe uma instância em memória para cada consulta. Os recortes usam a mesma data do grafo completo.” |
| BFS e FIFO | [BFS](../backend/algorithms/bfs.py#L12), `bfs` | “Inicializamos deque com a origem. popleft retira o mais antigo. Em cada vizinho novo, gravamos seu predecessor antes de enfileirar. A primeira descoberta respeita os níveis de distância, então a cadeia de predecessores dá o menor número de arestas.” |
| DFS e backtracking | [DFS](../backend/algorithms/dfs.py#L10), `dfs` | “Cada quadro da pilha guarda uma parada e seu iterador de vizinhos. A DFS registra o vizinho novo, empilha e desce na hora. Quando o quadro esgota os vizinhos, pop registra o retorno em finish_order e a busca retoma o pai.” |
| Dijkstra | [Dijkstra](../backend/algorithms/dijkstra.py#L33), `dijkstra` e `_estimated_travel_time`. [Pesos do GTFS](../backend/gtfs/importer.py#L374), `import_gtfs` | “Dijkstra minimiza a soma dos segundos por aresta. O peso é a mediana dos intervalos válidos entre partida e chegada consecutivas. Quando falta peso, há uma estimativa por distância reta e uma regra para ausência de coordenadas. O resultado é tempo estimado dentro do modelo.” |
| Chamadas Flask | [Entrada e rotas](../backend/app.py#L60), `read_algorithm_input`, `run_bfs`, `run_dfs`, `run_dijkstra`, `compare_algorithms` | “A API valida os códigos, seleciona o grafo da requisição e chama o algoritmo Python. A comparação chama BFS e DFS sobre os mesmos dados. Com destino vazio, a DFS percorre a cobertura.” |
| Resposta no navegador | [Interface](../frontend/static/js/app.js#L516), `apiFetch`, `executeBFS`, `executeDFS`, `executeWeightedSearch` e `compareAlgorithms`. [Resposta](../backend/app.py#L23), `prepare_algorithm_result` | “O JavaScript faz POST, lê o JSON e mostra caminho e métricas. Para BFS e DFS, appendVisitOrder apresenta as ordens. O painel ponderado mostra tempo, fonte dos pesos e caminho.” |
| Itinerário e mapa | [Itinerário](../backend/services/itinerary_service.py#L161), `build_itinerary`. [OSRM](../backend/services/road_matching_service.py#L380), `refine_itinerary_geometry`. [Leaflet](../frontend/static/js/app.js#L705), `drawItinerary` | “Com o caminho já calculado, escolhemos as linhas, aproveitamos a continuidade de viagens e recortamos os shapes. O OSRM é opcional e ajusta o desenho de fragmentos elegíveis. O Leaflet desenha os dados recebidos.” |
| Evidência de correção | [Travessias](../tests/test_traversals.py), [API](../tests/test_api.py), [geografia](../tests/test_geography.py), [auditoria de encerramento](AUDITORIA_ENTREGA.md) | “Os testes verificam caminhos e ordens esperados em grafos dirigidos com ciclos, alternativas e cadeias longas. Na auditoria final, também comparamos os algoritmos contra referências independentes e repetimos consultas reais no Edge.” |
| Limites | [README](../README.md#limitações), [importador](../backend/gtfs/importer.py#L160), [itinerário](../backend/services/itinerary_service.py#L11) | “Analisamos um grafo agregado de uma data de serviço. Espera, trânsito, caminhada e compatibilidade de horários e transferências exigem outro modelo. A escolha de linhas procura reduzir trocas dentro do caminho escolhido.” |

## Raciocínio para a defesa

**BFS.** Mostre `deque([origin])` (12), `popleft()` (24),
`visit_order.append(current)` (26) e `parent[neighbor]` antes de
`queue.append(neighbor)` (31–39). Quando um vizinho é descoberto no nível
`k + 1`, um caminho mais curto teria sido encontrado por um vértice de um
nível anterior. Mostre `path.reverse()` (55). Numa consulta dirigida,
um destino pode ficar fora da parte alcançável. Um código inválido é
tratado como erro de entrada. [BFS](../backend/algorithms/bfs.py)

**DFS.** Mostre o quadro inicial (10), o topo `stack[-1]` (17), a descida
(20–24) e o `for…else` de finalização (25–27). O `break` mantém o
iterador do pai suspenso no próximo vizinho e deixa os outros ramos para
depois. Com destino, a lista de finalização pode ser parcial ou vazia.
Sem destino, a travessia percorre todo o alcance dirigido. Ambas as buscas
custam O(V + E) em tempo e O(V) em espaço auxiliar no pior caso da parte
alcançável. [DFS](../backend/algorithms/dfs.py)

**Dijkstra.** Mostre `heapq.heappop` (46), o descarte de rótulo antigo
(47–48), a leitura do peso (55–57) e o relaxamento (59–63). Com pesos
não negativos, o destino retirado com o menor rótulo válido tem custo
ótimo no modelo. O heap pode conter mais de uma entrada para a mesma
parada. O limite seguro desta implementação é O((V + E) log(E + 1))
para um percurso com arestas, com O(V + E) de memória auxiliar no pior caso.
Em grafo simples, a forma usual é O((V + E) log V). [Dijkstra](../backend/algorithms/dijkstra.py)

## Resultados para citar

| Consulta | Resultado observado |
|---|---|
| Pequena · `480012875 → 480014889` | Duas arestas em ambas. BFS visita `4811488` antes do destino, DFS descobre o destino antes desse ramo. Sem destino, DFS registra sete descobertas e sete finalizações. |
| Intermediária · `8812664 → 940004410` | BFS com 25 arestas e uma troca de linha no itinerário, 2025-10 → 172K-10. |
| Completa · `480012875 → 480014632` | BFS 16 arestas e 640 visitas. DFS 3.225 arestas e 14.065 descobertas. Dijkstra 16 arestas e 1.906,0 s, exibidos como 31,8 min. |
| Completa · `560009135 → 5506671` | BFS, DFS e Dijkstra sem caminho. Da origem, BFS e DFS visitam 20 paradas. A DFS sem destino também aponta alcance de 20, incluindo a origem. |
| Completa · `600012584 → 3609172` | BFS tem 34 arestas e **4.046,0 s** ao somar os pesos do seu caminho. Dijkstra tem 39 arestas e **3.380,5 s**, com 39 pesos GTFS e nenhuma estimativa geográfica. |

Para a última consulta, diga: “O caminho da BFS tem cinco conexões a menos.
O do Dijkstra tem uma soma de pesos **665,5 segundos menor**. Comparamos
os dois caminhos com a mesma tabela de pesos. Esse valor representa o
modelo estático entre paradas.” A soma da BFS foi calculada na auditoria
usando seus pares consecutivos. O painel da BFS exibe arestas, enquanto
o botão **Menor tempo (Dijkstra)** mostra até uma casa decimal em minutos
(56,3 min nessa consulta). Use esse exemplo como reserva para perguntas.

## 20 perguntas difíceis de banca

| Nº | Pergunta | Resposta oral e evidência |
|---:|---|---|
| 1 | Por que usar um grafo e por que ele é dirigido? | “Paradas são identificáveis e viagens dão relações consecutivas. O arco inverso só existe se uma viagem ativa o percorrer.” [Graph.add_edge](../backend/algorithms/graph.py#L64) |
| 2 | Como duas linhas na mesma conexão afetam V e E? | “Existe uma entrada de destino por origem. O conjunto edge_routes acumula as linhas e trip_edges mantém ocorrências.” [Graph](../backend/algorithms/graph.py#L64) |
| 3 | O que acontece se inverter a consulta? | “A adjacência muda. Encontrar caminho de A a B não garante que B alcance A.” [bfs](../backend/algorithms/bfs.py#L31) |
| 4 | Por que a fila FIFO dá distância mínima? | “A retirada acontece por distância não decrescente. Um caminho mais curto teria descoberto o destino num nível anterior.” [bfs](../backend/algorithms/bfs.py#L22) |
| 5 | Por que descobertos e visitados podem diferir? | “BFS marca ao descobrir, antes de enfileirar, e registra visita na retirada. Ao retirar o destino, outros descobertos podem ficar na fila.” [bfs](../backend/algorithms/bfs.py#L22) |
| 6 | Por que parent é atualizado antes de enfileirar? | “Para que outra aresta que chega ao mesmo vértice já o reconheça e não o enfileire de novo.” [bfs](../backend/algorithms/bfs.py#L31) |
| 7 | Como provar que o caminho reconstruído é válido? | “Cada pai foi atribuído enquanto a busca examinava uma aresta de saída para o filho. Sigo os pais até a origem e inverto a sequência.” [bfs](../backend/algorithms/bfs.py#L43) |
| 8 | Qual a diferença entre DFS com pilha de quadros e empilhar todos os vizinhos? | “O quadro preserva o iterador. O break garante que o primeiro filho é explorado antes de descobrir os vizinhos seguintes, como na DFS recursiva.” [dfs](../backend/algorithms/dfs.py#L16) |
| 9 | Quando um vértice entra em finish_order? | “Quando seu iterador se esgota e o quadro sai da pilha. A parada antecipada pelo destino pode deixar quadros ativos.” [dfs](../backend/algorithms/dfs.py#L16) |
| 10 | DFS retorna mesmo um caminho com 3.225 arestas? | “Sim, exatamente nesse par e nessa ordem de adjacências. A cadeia de pais pertence ao primeiro ramo que descobre o destino. BFS encontra 16 no mesmo par.” [dfs](../backend/algorithms/dfs.py#L29) · [Benchmark](BENCHMARK_RESULTADOS.md) |
| 11 | De onde vem O(V + E)? | “Cada vértice é descoberto uma vez e cada aresta de saída do subgrafo explorado é examinada no máximo uma vez. Filas, quadros e pais somam O(V) de memória auxiliar.” [bfs](../backend/algorithms/bfs.py#L12) · [dfs](../backend/algorithms/dfs.py#L10) |
| 12 | Alcance e componente fraca respondem à mesma pergunta? | “Alcance segue arcos dirigidos da origem. A componente fraca é calculada após ignorar sentidos. Uma parada da mesma componente ainda pode ser inalcançável.” [weakly_connected_components](../backend/algorithms/connectivity.py#L15) |
| 13 | De onde vêm os segundos usados por Dijkstra? | “O importador acumula diferenças positivas de horário entre paradas consecutivas e guarda a mediana por aresta. No banco da aula, todas as 27.218 arestas têm peso.” [import_gtfs](../backend/gtfs/importer.py#L374) |
| 14 | Por que Dijkstra pode parar ao tirar o destino do heap? | “Com pesos não negativos, o menor rótulo válido retirado não pode ser melhorado por um caminho que parta dos rótulos restantes. Entradas antigas são descartadas antes do teste de destino.” [dijkstra](../backend/algorithms/dijkstra.py#L44) |
| 15 | Por que mais arestas podem somar menos segundos? | “Cada aresta tem peso próprio. A rota de 39 arestas somou 3.380,5 s, enquanto a de 34 arestas somou 4.046,0 s no mesmo modelo.” [dijkstra](../backend/algorithms/dijkstra.py#L53) · [Auditoria](AUDITORIA_ENTREGA.md) |
| 16 | Como se comporta quando falta peso ou não existe caminho? | “Sem peso, calcula um tempo por distância reta a 18 km/h, com piso de 1 s. Sem coordenadas, usa 60 s. Se não alcançar o destino válido, retorna found=false, caminho e tempo nulos.” [_estimated_travel_time](../backend/algorithms/dijkstra.py#L8) · [dijkstra](../backend/algorithms/dijkstra.py#L65) |
| 17 | O SQLite é consultado a cada vizinho visitado? | “As adjacências e pesos são carregados em memória na inicialização. O itinerário pode ler os pontos dos shapes no SQLite depois da busca.” [load_graph](../backend/models/database.py#L274) · [_shape_points](../backend/services/itinerary_service.py#L60) |
| 18 | Onde o JavaScript passa a origem, o destino e a instância? | “A função do botão envia os códigos no JSON. apiFetch adiciona a instância na URL, e Flask seleciona g.graph antes da rota.” [apiFetch](../frontend/static/js/app.js#L4) · [select_instance](../backend/app.py#L100) |
| 19 | O que o GTFS e o OSRM conseguem afirmar sobre a viagem real? | “O GTFS descreve o serviço planejado. O OSRM usado aplica um perfil rodoviário de carro para corrigir o desenho quando passa nas verificações. Horários, transferências operacionais e condições reais ficam fora do modelo.” [import_gtfs](../backend/gtfs/importer.py#L160) · [refine_itinerary_geometry](../backend/services/road_matching_service.py#L380) |
| 20 | O número 67 inclui prova automatizada de otimalidade do Dijkstra? | “O teste persistido de API inclui entrada inválida para Dijkstra. A auditoria executou verificações adicionais, com Floyd–Warshall em grafos pequenos, relaxamento repetido na rede real e um caso de fallback.” [Suíte de API](../tests/test_api.py#L44) · [Auditoria](AUDITORIA_ENTREGA.md) |

## Checklist de apresentação em 10 minutos

### Antes da banca

- [ ] Confirme os cinco nomes na capa do PowerPoint e nomes, RAs, contribuições e revisão de IA no relatório.
- [ ] Use Python 3.14 e instale as dependências antes da aula. O acesso ao índice de pacotes é necessário na primeira instalação.
- [ ] Abra o PowerPoint oficial, o editor em **BFS 12–39 e 49–55**, **DFS 10–27**, e deixe **Dijkstra 33–63**, `backend/app.py` e `frontend/static/js/app.js` prontos para perguntas.
- [ ] Inicie o servidor e abra [TransitGraph](http://127.0.0.1:5000). Em outro terminal, consulte `Invoke-RestMethod http://127.0.0.1:5000/api/health`. Espere `online`, 20.812 vértices e 27.218 arestas.
- [ ] Se a porta 5000 estiver ocupada, encerre a instância anterior ou use uma porta livre conforme o [roteiro](ROTEIRO_APRESENTACAO.md).

```powershell
Set-Location D:\transitgraph
# Somente se ainda precisar criar e preparar o ambiente:
# python -m venv .venv
# .\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:TRANSITGRAPH_DATABASE = (Resolve-Path .\data\processed\transitgraph.db).Path
$env:TRANSITGRAPH_MAP_MATCHING = "0"
.\.venv\Scripts\python.exe run.py
```

### Ordem de execução

| Relógio | Pessoa e ação |
|---|---|
| 0:00–1:05 | Integrante 1 · slides 1–2, objetivo e grupo. |
| 1:05–2:25 | Integrante 2 · slides 3–4, dados e grafo. |
| 2:25–3:15 | Integrante 3 · slide 5, fila, visita e caminho BFS. |
| 3:15–4:05 | Integrante 4 · slide 6, pilha, descoberta e retorno. |
| 4:05–4:50 | Integrante 5 · slide 7, comparação de 16 e 3.225. |
| 4:50–5:55 | Slide 8 · integrantes 1, 3 e 4. Pequena, duas arestas, diferença de ordens, DFS sem destino. |
| 5:55–6:45 | Slide 8 · integrantes 2 e 3. Intermediária, 25 arestas e uma troca. |
| 6:45–8:10 | Slide 8 · integrantes 4 e 5. Completa, 20 alcançáveis e caso sem caminho. |
| 8:10–10:00 | Integrante 5 · slides 9–10, validação e limites. |

A demo dura **3:20**. Deixe a rota longa de Dijkstra para a banca. Se o
mapa ou o CDN falhar, mantenha o navegador nos resultados de texto, ordens e
contagens. Se a interface falhar, use a [consulta PowerShell à API](ROTEIRO_APRESENTACAO.md#se-os-serviços-externos-falharem)
e as [capturas da demo](apresentacao/comparacao-pequena.png). O servidor local e
o SQLite precisam permanecer disponíveis. Leaflet, Cytoscape.js, tiles do
OpenStreetMap e OSRM são recursos externos. Desligue o OSRM para reduzir a
dependência de rede durante o ensaio.
