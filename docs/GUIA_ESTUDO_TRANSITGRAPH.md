# Guia de estudo do TransitGraph

**Teoria dos Grafos · Tema 1 · Entrega em 17/11/2026**

## A. Problema e visão geral

O TransitGraph transforma a rede de ônibus de São Paulo, descrita pelo GTFS da
SPTrans, em um grafo de paradas. Ele responde a duas perguntas. Entre duas
paradas, qual caminho usa o menor número de conexões? A partir de uma parada,
quais outras podem ser alcançadas seguindo o sentido das viagens?

A **BFS** resolve a primeira pergunta. A **DFS** permite explorar a segunda e
observar quando cada ramo termina. A interface também compara as buscas com a
mesma entrada, pesquisa paradas, exibe itinerários, mostra a vizinhança no grafo
interativo e resume componentes fracamente conexas. Dijkstra oferece uma opção
separada de menor tempo estimado.

## B. Como a rede vira um grafo

Um vértice é uma parada identificada pelo `stop_id`. Sua posição e seu nome
são metadados. Para duas paradas consecutivas A e B de uma viagem ativa, o
importador cria a aresta **A → B** conforme `stop_sequence`. B → A só existe se
uma sequência ativa também registrar esse sentido. Se duas linhas realizam A → B,
a lista de adjacência guarda um único vizinho B e o conjunto `edge_routes`
guarda ambas as linhas.

O grafo armazena pesos em segundos, calculados pela mediana das amostras válidas
de chegada à parada seguinte menos partida da anterior. Dijkstra usa esses
pesos. BFS e DFS usam apenas as adjacências. Cada aresta vale uma conexão para
a BFS. Se Dijkstra encontrar uma aresta sem horário, usa uma estimativa
geográfica a 18 km/h, com 60 segundos de substituição quando faltam coordenadas.

O importador seleciona viagens de ônibus e serviços ativos conforme
`calendar.txt`. Em `trips.txt`, `trip_id` vincula a viagem ao serviço, à linha, ao
sentido e ao `shape_id`. Em `stop_times.txt`, ordena-se cada viagem pelo
`stop_sequence`. Nomes e coordenadas vêm de `stops.txt`, e os metadados das
linhas de `routes.txt`. `trip_edges` preserva cada ocorrência do par de paradas
por linha, com viagem, sentido e intervalo no shape. Isso permite distinguir
passagens repetidas pela mesma parada.

**Exemplo real.** No recorte intermediário, a BFS entre Sesc Santana
(`8812664`) e Av. Júlio Buono, 2007 (`940004410`), obtém 25 arestas. O
itinerário seleciona as linhas 2025-10 e 172K-10, com uma troca. Entre duas
paradas consecutivas há uma aresta. A sequência selecionada de linhas determina
as trocas. [Importador](../backend/gtfs/importer.py) ·
[Representação](../backend/algorithms/graph.py) · [Dados SPTrans](../README.md#dados-e-instâncias)

## C. Busca em Largura

A BFS começa com a origem na fila e em `parent`, com predecessor vazio. A fila
FIFO retira a entrada mais antiga com `popleft()`. Para cada vizinho de saída
ainda ausente de `parent`, registra o predecessor e acrescenta o vizinho ao final
da fila. Esse registro é feito na descoberta, garantindo uma única inserção
por vértice. O algoritmo guarda a ordem das retiradas em `visit_order`.
Quando retira o destino, para. Para reconstruir o caminho, segue os predecessores
do destino até a origem e inverte a lista.

**Por que minimiza arestas?** A fila processa distâncias em ordem não
decrescente. Ao descobrir um vizinho a partir do nível `k`, o caminho até ele
tem `k + 1` arestas. Um caminho de comprimento menor teria chegado por um
predecessor processado em um nível anterior e já teria descoberto o vizinho.
Isso vale quando todas as conexões contam uma unidade. A ordem dos vizinhos
decide empates entre caminhos de mesma distância.

Com listas de adjacência, tempo **O(V + E)** e espaço auxiliar **O(V)** no
pior caso. Os símbolos incluem somente os vértices e arestas que a busca pode
atingir. A topologia do grafo armazenado ocupa **O(V + E)**. Fila, predecessores
e ordem de visita compõem a memória auxiliar. [Implementação da BFS](../backend/algorithms/bfs.py)

### Exemplo didático compartilhado com a DFS

Insira as arestas nesta ordem. `A→B, A→C, B→D, D→E, E→F, C→F, E→B`.
O último arco fecha o ciclo B → D → E → B. Origem A e destino F.

| Passo | Retira da fila | Registra predecessores | Fila após o passo |
|---:|---|---|---|
| 0 | — | A recebe vazio | A |
| 1 | A | B ← A, C ← A | B, C |
| 2 | B | D ← B | C, D |
| 3 | C | F ← C | D, F |
| 4 | D | E ← D | F, E |
| 5 | F | Encerra a busca | E |

Ordem de visita **A, B, C, D, F**. O caminho é **A → C → F**, com duas arestas.
E foi descoberto, mas permanecia na fila quando F foi retirado.

## D. Busca em Profundidade

A DFS mantém uma pilha explícita de quadros. Cada quadro guarda um vértice
ativo e um iterador apontando para o próximo vizinho. Ao achar um vizinho
novo, registra seu predecessor, anota a descoberta e empilha seu quadro.
Quando o iterador se esgota, desempilha o quadro e registra a finalização.
Esse retorno ao quadro anterior é o **backtracking**. Na presença de um ciclo,
o mapa `parent` impede descobrir de novo um vértice já alcançado.

Com destino, encerra ao descobri-lo. Quadros que ainda estiverem na pilha
ficam sem registro de finalização. Com o destino em branco, a busca esgota
todos os vizinhos atingíveis, e o total descoberto, incluindo a própria
origem, é a cobertura direcionada. O caminho usa a mesma técnica de seguir
predecessores e inverter a lista. A pilha explícita evita o limite de
recursão do Python. O pior caso é **O(V + E)** em tempo e **O(V)** em espaço
auxiliar. [Implementação da DFS](../backend/algorithms/dfs.py)

| Passo | Ação no exemplo | Pilha após a ação |
|---:|---|---|
| 0 | Descobre A | A |
| 1 | A descobre B | A, B |
| 2 | B descobre D | A, B, D |
| 3 | D descobre E | A, B, D, E |
| 4 | E descobre F | A, B, D, E, F |

Com destino F, a descoberta é **A, B, D, E, F**. O caminho tem **quatro
arestas** e a ordem de finalização está vazia. Sem destino, F é finalizado
primeiro. E retoma a adjacência, encontra B já descoberto e finaliza. Após
finalizar D e B, A descobre C. C encontra F já descoberto. A ordem completa de
descoberta é **A, B, D, E, F, C**. A finalização é **F, E, D, B, C, A**.

## E. Comparação em consultas reais

| Consulta | BFS | DFS |
|---|---|---|
| Pequena, `480012875 → 480014889` | 2 arestas. Visita `480012875, 480014888, 4811488, 480014889`. | 2 arestas. Descobre `480012875, 480014888, 480014889`. |
| Completa, `480012875 → 480014632` | 16 arestas, 640 visitas, 742 descobertas, 964 arestas examinadas. | 3.225 arestas, 14.065 visitas e descobertas, 17.347 arestas examinadas. |
| Completa, `560009135 → 5506671` | Sem caminho. 20 visitas. | Sem caminho. 20 visitas. |

A BFS retira da fila em ordem de nível. A DFS segue a ordem de ramos da lista
de adjacência. A mesma parada pode aparecer mais cedo em uma busca, e uma
consulta com destino pode encerrar com coberturas parciais diferentes. Sem
destino, ambas alcançam o mesmo conjunto, em ordens possivelmente diferentes.
Com origem `480012875` na rede completa, ambas visitaram 20.534 paradas e
examinaram 26.938 arestas em travessia completa. Com destino, compare as
contagens e as condições de parada antes de interpretar os tempos.

No caso de 16 contra 3.225, a DFS localiza um caminho pelo primeiro ramo que
chega ao destino, e a BFS garante o menor comprimento em arestas. A contagem
de arestas mede conexões consecutivas de parada. Tempo de viagem e baldeações
são quantidades distintas. [Benchmark e metodologia](BENCHMARK_RESULTADOS.md)

## F. Arquitetura e arquivos

```text
ZIP GTFS SPTrans
  -> scripts/build_graph.py -> backend/gtfs/importer.py
  -> backend/models/database.py -> data/processed/transitgraph.db
  -> run.py -> Flask em backend/app.py -> Graph em memória
       -> três instâncias em backend/services/instance_service.py
       -> BFS, DFS e Dijkstra em backend/algorithms/
       -> itinerário e recortes de shapes em backend/services/itinerary_service.py
       -> ajuste viário opcional em backend/services/road_matching_service.py
       -> JSON -> frontend/static/js/app.js e frontend/templates/index.html
               -> ordens, métricas, mapa Leaflet e grafo Cytoscape.js
```

| Componente | Pontos de entrada e responsabilidade |
|---|---|
| Backend | `run.py` inicia o servidor. `create_app` carrega o SQLite. `select_instance` escolhe o grafo por consulta. |
| API | `/api/algorithms/bfs`, `/api/algorithms/dfs`, `/api/algorithms/compare` e `/api/algorithms/dijkstra`. `prepare_algorithm_result` acrescenta itinerário e limita cada ordem a 200 registros, mantendo totais. |
| Persistência | `save_graph` e `load_graph` persistem ou reconstroem paradas, arestas, linhas, pesos e ocorrências. A recarga preserva a ordem armazenada. |
| Itinerário | `choose_routes` escolhe linhas ao longo da sequência de paradas. `build_itinerary` prioriza a continuidade das ocorrências da viagem e recorta os shapes. |
| Interface | `app.js` envia a entrada, mostra contagens e visita, desenha fragmentos com Leaflet e apresenta o diagnóstico. Cytoscape.js exibe uma vizinhança dirigida e limitada. |
| Conectividade | `weakly_connected_components` cria uma projeção sem direção. A DFS a partir de uma parada segue a direção original. |

[API](../backend/app.py) · [SQLite](../backend/models/database.py) ·
[Interface JavaScript](../frontend/static/js/app.js) · [Conectividade](../backend/algorithms/connectivity.py)

## G. Geometria e mapa

A sequência de paradas calculada pelas buscas determina **quais conexões**
exibir. O `shapes.txt` fornece uma polilinha oficial que auxilia a determinar
**onde desenhá-las**. Os pontos seguem `shape_pt_sequence`. O importador prioriza
distâncias compatíveis quando informadas nos arquivos de shapes e de horários.
No ZIP incluído, faltam em `stop_times.txt`, então a associação projeta as
paradas em ordem sobre segmentos do shape. Paradas consecutivas com coordenadas
idênticas podem compartilhar posição. Passagens reais em momentos diferentes
são distinguíveis pela ocorrência na viagem.

Leaflet desenha a polilinha e o fundo do OpenStreetMap. O map matching do OSRM
é opcional. Ele tenta associar os pontos do fragmento esparso à rede viária.
O resultado só é aceito se respeitar sequência dos pontos de controle, confiança,
deslocamento, extensão e corredor do GTFS. O perfil público considera carros.
Em corredores exclusivos ou vias paralelas a proposta pode ser incompatível
com o ônibus.

O **Diagnóstico geográfico** apresenta GTFS, proposta OSRM e traçado final. Um
fragmento com traçado incerto ou ligação aproximada fica tracejado. Uma ligação
entre dois códigos com coordenadas iguais pode aparecer sem polilinha, com a
indicação **sem trajeto de rua confirmado**. A eventual quebra de viagem exige
interpretação separada da quantidade de trocas de linha. Esses detalhes chegam
depois da busca e pertencem à representação do itinerário.
[Auditoria geográfica e capturas](AUDITORIA_GEOMETRIA.md) ·
[Serviço viário](../backend/services/road_matching_service.py)

## H. Testes e reprodução

Na raiz do projeto, com a instalação pronta, execute
`.\.venv\Scripts\python.exe -m pytest -q`. A verificação final em Python 3.14
registrou **67 aprovados**. A suíte cobre visita, predecessor por caminho
esperado, ciclos, direção, empates e cadeia com 5.000 vértices, além de API,
recortes, SQLite, importação e regressões de geometria e OSRM. Para conferir um
caminho manualmente, valide a origem e o destino, cada par consecutivo na lista
de adjacência e a distância de `len(caminho) - 1`. Para uma BFS, compare os níveis
e a menor distância obtida por inspeção do recorte pequeno.

| Instância selecionável | Vértices | Arestas | Reprodução |
|---|---:|---:|---|
| Pequena | 7 | 6 | Duas conexões a partir de `480012875`. Compare as ordens e rode DFS sem destino para ver as sete descobertas. |
| Intermediária | 177 | 181 | Linhas 2025-10 e 172K-10. Repita o caminho de 25 arestas e uma troca. |
| Completa | 20.812 | 27.218 | Rode o caso sem caminho e compare as 20 visitas de cada busca. |

Os três grafos usam a data de serviço de 01/11/2026. Os resultados são
independentes da disponibilidade do OSRM. Para encontrar erros de apresentação,
use o navegador da sala. Para isolar a lógica, também é possível consultar
`/api/stats?instance=local` e as rotas pelos comandos do roteiro.
[Roteiro de demonstração](ROTEIRO_APRESENTACAO.md) · [Suíte](../tests/)

## I. Limitações e possíveis melhorias

- O grafo agregado por parada descreve conectividade. Horários de embarque,
  espera, caminhada, regras de transferência e operação em tempo real
  exigiriam modelagem temporal e dados adicionais.
- A seleção de linhas minimiza trocas dentro do caminho selecionado. A busca
  por um caminho global de menos baldeações poderia usar estados
  `(parada, linha)`, com um custo explícito para a troca.
- O calendário usa as regras semanais do arquivo incluído. A interpretação
  de exceções e frequências em outros feeds requer suporte adicional.
- A visualização depende de bibliotecas CDN e tiles externos. Pré-empacotar
  as bibliotecas seria uma melhoria para demonstrações desconectadas.
- Um ajuste viário é uma inferência cartográfica. Validação operacional
  requer dados de campo ou confirmação do operador.

## J. Glossário

| Termo | Definição |
|---|---|
| Grafo | Conjunto de vértices e relações representadas por arestas. |
| Vértice | Elemento da rede. Aqui, uma parada identificada por código. |
| Aresta | Relação de adjacência. Aqui, uma conexão entre paradas consecutivas de viagem. |
| Grafo direcionado | Grafo com origem e destino definidos em cada aresta. |
| Lista de adjacência | Representação que associa a cada vértice seus vizinhos de saída. |
| BFS | Busca em largura, que explora o grafo por níveis com fila. |
| DFS | Busca em profundidade, que aprofunda um ramo antes de retroceder. |
| FIFO | O primeiro elemento inserido é o primeiro a sair. |
| Pilha | Estrutura em que o último elemento inserido é o primeiro a sair. |
| Predecessor | Vértice a partir do qual outro foi descoberto na busca. |
| Caminho | Sequência de vértices com uma aresta no sentido correto entre cada par consecutivo. |
| Conjunto alcançável | Vértices que admitem caminho dirigido a partir da origem, incluindo a própria origem. |
| Componente fracamente conexa | Região conectada quando se ignora o sentido das arestas. |
| GTFS | Formato de dados de transporte público com linhas, viagens, paradas, calendário e geometrias. |
| Shape | Sequência de pontos geográficos que representa o traçado de uma viagem. |
| Map matching | Associação de uma sequência de coordenadas aos segmentos de uma malha viária. |
