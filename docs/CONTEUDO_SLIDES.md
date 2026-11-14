# Conteúdo dos slides do TransitGraph

**Tema 1 · Cinco integrantes · 10:00, incluindo 3:20 de demonstração**

Os blocos **Na tela** são o texto do slide. Guarde a explicação e a fala
nas notas do apresentador. Os tempos incluem transições.

## Slide 1 — TransitGraph · 0:25

- **Objetivo** Identificar o trabalho e a equipe.
- **Na tela** TransitGraph · Conectividade da rede de ônibus de São Paulo · Teoria dos Grafos · [cinco nomes confirmados pelo grupo].
- **Visual** Título e uma captura recortada do mapa do projeto. [Cruzamento na Rua Rio Bom](geometria/followup-rio-bom-false.png)
- **Explicação técnica** Ferramenta acadêmica com grafo dirigido, dados GTFS e dois algoritmos de busca.
- **Fala · integrante 1** “Construímos o TransitGraph para estudar a rede de ônibus de São Paulo. Em dez minutos, vamos mostrar como representamos as conexões, como as duas buscas percorrem a rede e como a aplicação responde a uma consulta ao vivo.”

## Slide 2 — Perguntas sobre a rede · 0:40

- **Objetivo** Mostrar o problema real e a função de cada busca.
- **Na tela** Menor número de conexões entre duas paradas (BFS). Cobertura dirigida a partir de uma parada (DFS).
- **Visual** Duas perguntas ao lado de uma pequena rede de setas extraída do recorte real. [Grafo da instância pequena](apresentacao/grafo-pequena.png)
- **Explicação técnica** O primeiro problema tem origem e destino. O segundo pode ser consultado só com origem e inclui o vértice inicial.
- **Fala · integrante 1** “Uma pessoa pode perguntar quantas conexões são necessárias para ir de A a B. A BFS dá esse caminho. Outra pergunta é quais paradas ficam ao alcance de A seguindo o sentido das viagens. A DFS permite percorrer toda essa região e observar a ordem de retorno.”

## Slide 3 — GTFS e instâncias · 0:45

- **Objetivo** Apresentar a fonte e as três escalas.
- **Na tela** SPTrans · Serviço em 01/11/2026. Pequena 7/6 · Intermediária 177/181 · Completa 20.812/27.218. Legenda da tabela com vértices e arestas.
- **Visual** Tabela com três linhas. Use a captura do grafo para ilustrar o recorte de dois níveis.
- **Explicação técnica** Os recortes vêm da mesma data de serviço. O local segue até dois níveis a partir de uma parada. O intermediário usa duas linhas.
- **Fala · integrante 2** “A SPTrans fornece paradas, viagens, ordem das paradas, horários e shapes. Selecionamos os serviços de ônibus ativos em 1º de novembro. A rede tem mais de vinte mil paradas. A instância pequena torna a ordem reproduzível à mão. A intermediária mostra um exemplo com troca de linha.” [Origem e critérios](../README.md#dados-e-instâncias)

## Slide 4 — Modelo de grafo direcionado · 0:35

- **Objetivo** Relacionar os dados às adjacências.
- **Na tela** Vértice = parada · Aresta dirigida = próximo ponto da viagem · Peso de tempo = mediana em segundos para Dijkstra.
- **Visual** Setas `480012875 → 480014888 → 480014889` e ramo a partir da origem para `4811488`.
- **Explicação técnica** Uma aresta pode atender a múltiplas linhas. O SQLite guarda conexões e ocorrências. BFS e DFS leem adjacências.
- **Fala · integrante 2** “Cada código de parada vira um vértice. A viagem estabelece o sentido entre paradas consecutivas. Se duas linhas passam pela mesma conexão, o vizinho aparece uma vez e as linhas ficam associadas à aresta. Para BFS, cada conexão conta uma unidade.” [Guia de estudo, modelagem](GUIA_ESTUDO_TRANSITGRAPH.md#b-como-a-rede-vira-um-grafo)

## Slide 5 — BFS e menor número de arestas · 0:50

- **Objetivo** Mostrar fila, níveis e caminho reconstruído.
- **Na tela** Fila FIFO · Primeira descoberta registra o predecessor · Menor número de arestas.
- **Visual** Rede didática do guia com os níveis A, B/C, D/F. Destaque `A → C → F`.
- **Explicação técnica** Ao descobrir um vértice, a busca o marca e enfileira. Ao retirar o destino, segue os predecessores. Tempo O(V + E) e espaço auxiliar O(V).
- **Fala · integrante 3** “A fila retira primeiro o vértice mais antigo. A entra, depois são descobertos B e C. Quando C é processado, descobre F com duas arestas. Qualquer caminho menor teria descoberto F num nível anterior. Guardamos o predecessor para recuperar esse caminho.” [Exemplo com fila](GUIA_ESTUDO_TRANSITGRAPH.md#c-busca-em-largura)

## Slide 6 — DFS e cobertura direcionada · 0:50

- **Objetivo** Explicar aprofundamento, retorno e parada.
- **Na tela** Pilha de vértices ativos · Descoberta ao entrar · Finalização ao esgotar os vizinhos.
- **Visual** A mesma rede, agora destacando `A → B → D → E → F`. Ao lado, pilha com F no topo.
- **Explicação técnica** Cada quadro guarda a posição entre vizinhos. O algoritmo pode terminar ao descobrir um destino ou esgotar a cobertura. Tempo O(V + E), espaço auxiliar O(V).
- **Fala · integrante 4** “A DFS entra no primeiro vizinho novo e continua por esse ramo. Quando esgota os vizinhos, volta para continuar o quadro anterior. Se informarmos F, para na descoberta. Se deixarmos o destino vazio, a ordem de finalização registra os retornos e a visita cobre tudo que é alcançável.” [Exemplo com pilha](GUIA_ESTUDO_TRANSITGRAPH.md#d-busca-em-profundidade)

## Slide 7 — Comparação na rede completa · 0:45

- **Objetivo** Mostrar a diferença verificada com os mesmos extremos.
- **Na tela** `480012875 → 480014632` · BFS 16 arestas · DFS 3.225 arestas.
- **Visual** Dois números grandes rotulados em arestas, com uma linha menor mostrando 640 e 14.065 visitas, respectivamente.
- **Explicação técnica** A quantidade de visitas depende da ordem das adjacências e do critério de parada. A DFS encontra o primeiro caminho do seu ramo. O tempo depende da consulta e da execução.
- **Fala · integrante 5** “Com a mesma origem, destino e rede, a BFS encontra 16 conexões. A DFS encontra um caminho de 3.225 porque aprofunda os ramos na ordem armazenada. As duas listas são caminhos do grafo. O número de conexões é uma métrica diferente de tempo ou trocas de linha.” [Benchmark](BENCHMARK_RESULTADOS.md)

## Slide 8 — Demonstração ao vivo · 3:20

- **Objetivo** Mostrar buscas, ordens, itinerário e ausência de caminho.
- **Na tela** Pequena · ordem de visita. Intermediária · 25 conexões e uma troca. Completa · 20 alcançáveis e destino inalcançável.
- **Visual** Aplicação aberta. Use a captura pequena se a visualização externa falhar. [Captura da comparação](apresentacao/comparacao-pequena.png)
- **Explicação técnica** O mapa é opcional para a explicação. As listas, o caminho e os totais atendem à demonstração dos algoritmos.
- **Fala e operação · cinco integrantes**
  - **4:50–5:55** 1 abre a aplicação. 3 e 4 comparam `480012875 → 480014889` na pequena. Mostre a diferença entre as ordens mesmo com duas arestas em ambos. Apague o destino e rode DFS para abrir a finalização.
  - **5:55–6:45** 2 explica o recorte intermediário. 3 apresenta a BFS de `8812664` a `940004410`. Mostre as linhas 2025-10 e 172K-10 e a única troca.
  - **6:45–8:10** Na completa, 4 apresenta a DFS só com `560009135`. Mostre 20 paradas. Compare com o destino `5506671` e leia a mensagem sem caminho.
- **Transição** Às 8:10, volte aos slides. [Roteiro com as entradas e alternativa local](ROTEIRO_APRESENTACAO.md)

## Slide 9 — Testes e resultados · 0:55

- **Objetivo** Explicar que evidências sustentam a demonstração.
- **Na tela** 67 testes aprovados · Três instâncias verificadas na interface · Execução textual confirmada com recursos externos bloqueados.
- **Visual** Recorte da comparação pequena ou uma tabela com ordens observadas.
- **Explicação técnica** A suíte cobre ordens, direção, ciclos, persistência, API e geometria. O benchmark usa 21 repetições por condição e mede as buscas antes de montar o mapa.
- **Fala · integrante 5** “Conferimos o resultado em grafos conhecidos e em consultas reais. A suíte passou com 67 testes. No navegador, o mesmo caminho e as mesmas ordens apareceram com os recursos externos bloqueados. Os tempos que registramos medem a busca e variam conforme máquina e entrada.” [Auditoria final](AUDITORIA.md#verificação-final-para-17112026)

## Slide 10 — Limitações e conclusão · 0:55

- **Objetivo** Delimitar o que o modelo permite concluir.
- **Na tela** BFS minimiza conexões · DFS mede alcance dirigido · GTFS estático e geometria com qualidade variável.
- **Visual** Captura da mesma conexão na Conde de Frontin com diagnóstico. [GTFS tracejado](geometria/followup-frontin-false.png) · [Ajuste aceito](geometria/followup-frontin-true.png)
- **Explicação técnica** O modelo agrega viagens por parada. Tempo, espera, horários, caminhada e transferência operacional exigem outro nível de informação. O OSRM ajusta o desenho conforme as verificações cartográficas.
- **Fala · integrante 5** “Com o grafo disponível, respondemos quantas conexões separam duas paradas e qual é a cobertura dirigida de uma origem. O itinerário nasce de dados programados e o mapa sinaliza a geometria incerta. Estamos prontos para repetir a consulta e explicar os resultados.”

**Total** 0:25 + 0:40 + 0:45 + 0:35 + 0:50 + 0:50 + 0:45 + 3:20 + 0:55 + 0:55 = **10:00**.
