# Auditoria técnica e acadêmica do TransitGraph

Auditoria realizada em 14/11/2026 para a entrega de 17/11/2026. A classificação
abaixo usa os requisitos transcritos no pedido.

## A. Diagnóstico geral

O projeto responde a duas perguntas sobre a rede de ônibus de São Paulo.
A BFS calcula um trajeto de menor número de conexões entre paradas. A DFS
mede a cobertura direcionada a partir de uma parada e mostra o que fica fora
dela. A cobertura depende da origem e pode ser muito menor que a componente
fracamente conexa que a contém.

A aplicação usa Flask, SQLite, Python e JavaScript. O importador transforma
as sequências de paradas do GTFS em arestas direcionadas, filtra viagens de
ônibus pelo calendário semanal e guarda várias linhas por aresta. O grafo
é carregado pela aplicação em memória. Leaflet mostra paradas e itinerários
no mapa. Cytoscape.js mostra vizinhanças limitadas da rede.

A rede completa tem 20.812 vértices e 27.218 arestas. Dicionários de saída
ordenados pela inserção implementam listas de adjacência com armazenamento
topológico O(V + E) e deduplicação por destino. A matriz teria mais de
433 milhões de posições. Pesos em segundos são medianas de amostras de
tempo programado por aresta e são usados pela consulta Dijkstra. BFS e DFS
usam somente a topologia.

A agregação por parada dispensa horários de embarque e regras de
transferência. O resultado descreve conectividade topológica e pode
encadear viagens que não são compatíveis no horário de um passageiro.
Frequências, exceções de calendário de outros feeds, caminhada, espera e
trânsito em tempo real ficam fora do modelo. O mapa-base e as bibliotecas
de visualização dependem de serviços externos.

## B. Conformidade acadêmica

| Requisito | Situação | Evidência |
|---|---|---|
| Tema 1 aplicado a um problema real | ATENDIDO | [import_gtfs](../backend/gtfs/importer.py), [dados e limitações](../README.md#dados-e-instâncias) |
| Representação correta e justificativa | ATENDIDO | [Graph](../backend/algorithms/graph.py), [load_graph](../backend/models/database.py) e [modelagem](../README.md#problema-e-modelagem) |
| BFS correta e útil na solução | ATENDIDO | [bfs](../backend/algorithms/bfs.py), [run_bfs](../backend/app.py) e [testes](../tests/test_traversals.py) |
| DFS correta e útil na solução | ATENDIDO | [dfs](../backend/algorithms/dfs.py), [run_dfs](../backend/app.py) e [testes](../tests/test_traversals.py) |
| Ordem observável e comparação na mesma consulta | ATENDIDO | [compare_algorithms](../backend/app.py) e [appendVisitOrder](../frontend/static/js/app.js). As listas mostram até 200 registros e mantêm as contagens totais. |
| Três instâncias com dimensões diferentes | ATENDIDO | [build_instances](../backend/services/instance_service.py), [seletor](../frontend/templates/index.html), [teste de isolamento dos recortes](../tests/test_api.py) |
| Visualização, entradas, resultados e erros | ATENDIDO | [interface](../frontend/templates/index.html) e [testes de API](../tests/test_api.py). O mapa e o grafo interativo funcionaram com os recursos externos disponíveis. |
| Testes automatizados e medições | ATENDIDO | [testes](../tests/) e [benchmark](BENCHMARK_RESULTADOS.md) em três escalas, com e sem destino |
| Roteiro e possibilidade de demonstração | ATENDIDO | [roteiro de 10 minutos](ROTEIRO_APRESENTACAO.md) e validação dos exemplos na seção F |
| Documentação técnica e identificação da equipe | PARCIALMENTE ATENDIDO | [README](../README.md) atualizado. A lista completa, os RAs e as contribuições dependem do grupo. |
| Material do relatório acadêmico | PARCIALMENTE ATENDIDO | [PDF existente](../output/documents/TransitGraph_Relatorio_Tecnico_Atualizado.pdf) tem estrutura e referências. Os números, a seção de instâncias e as evidências da interface precisam de atualização no documento editável. |
| Aderência a compromissos da proposta original e revisão por cada integrante | NÃO VERIFICÁVEL | Proposta aprovada e revisão individual do trabalho não estavam disponíveis. Confirme se Tarjan, pontes, articulações ou simulação de fechamento foram prometidos. |

## C. Auditoria dos algoritmos

**BFS.** A fila FIFO mantém os vértices por distância não decrescente da
origem. O predecessor é registrado na primeira descoberta, antes de
enfileirar. Cada predecessor liga o vértice a um nível anterior, logo a
cadeia recupera um caminho de comprimento mínimo em arestas. A ordem
retornada é a das retiradas da fila. Uma parada descoberta pode ficar
na fila após a retirada do destino. Sem destino, todos os descobertos são
visitados. A consulta de vizinhança do grafo também usa a estratégia de
níveis, com limites próprios de profundidade e tamanho.

**DFS.** Cada quadro mantém o vértice ativo e a posição do seu iterador.
Ao encontrar um vizinho novo, registra o pai, descobre o vizinho e entra
nele antes de continuar a adjacência do pai. Ao esgotar a adjacência,
registra a finalização e retorna ao quadro anterior. Com destino, a
busca para ao descobri-lo e pode deixar quadros ativos. A cadeia de pais
usa arestas válidas, e seu comprimento depende da ordem dos ramos.
A pilha explícita evita o limite de recursão do Python.

**Casos-limite e custo.** Ambas usam o mapa de pais para evitar
redescobertas em ciclos. Só usam arestas de saída. Origem igual ao
destino retorna um caminho de zero arestas. Um destino existente, porém
inalcançável, retorna ausência de caminho após esgotar o subgrafo
direcionado alcançável. Percorrer o grafo inteiro exigiria reiniciar a
busca em cada vértice ainda não descoberto. No pior caso de uma busca,
o tempo é O(V + E) e o espaço auxiliar é O(V), incluindo pais, fila ou
pilha e ordens registradas. Em travessias completas a partir da mesma
origem, as duas buscas examinam as mesmas adjacências de saída.

## D. Problemas encontrados

| Gravidade | Arquivo | Impacto | Correção |
|---|---|---|---|
| CRÍTICO | [dfs.py](../backend/algorithms/dfs.py) | Empilhar e marcar irmãos de uma vez podia impedir a descoberta de um irmão por um ramo mais profundo. O caminho e a ordem podiam divergir de uma DFS. | Pilha de iteradores, descoberta por descida e ordem de finalização. Caso mínimo A→B, A→C, B→C reproduz a diferença no predecessor de C. |
| CRÍTICO | [app.py](../backend/app.py) e [index.html](../frontend/templates/index.html) | Interface operava somente sobre o banco padrão. | Três instâncias do mesmo GTFS e seleção aplicada a todas as consultas. |
| ALTO | [benchmark.py](../scripts/benchmark.py) | A tabela da rede real comparava BFS com destino e DFS completa. | Mesma entrada e modalidade de busca para ambos, com medições de operações e memória. |
| ALTO | [app.js](../frontend/static/js/app.js) | A DFS com destino inalcançável indicava que o havia localizado. Falha no CDN do Leaflet impedia até as consultas textuais. | Mensagem de ausência de caminho, resultados preservados e visualizações tratadas como opcionais no carregamento. |
| ALTO | [tests](../tests/) | Faltavam casos que distinguissem pré-marcação de irmãos, finalização e profundidade elevada. | Testes de regressão e casos direcionados com resultados escritos explicitamente. |
| MÉDIO | [app.py](../backend/app.py) e [importer.py](../backend/gtfs/importer.py) | JSON que não é objeto podia gerar HTTP 500. Viagem sem pontos de shape podia interromper a importação ao acessar uma lista vazia. | Validação da entrada e preservação das arestas e dos pesos de viagens sem pontos de shape. |
| MÉDIO | [build_graph.py](../scripts/build_graph.py) | Data inválida ou sem serviço podia gerar exceção ou substituir o banco por uma instância vazia. | Mensagem de entrada inválida e saída antes de salvar quando não há paradas. |
| MÉDIO | [database.py](../backend/models/database.py), [requirements.txt](../requirements.txt) | A ordem SQLite dependia do plano de consulta e havia dependências sem uso. | Recarga explícita por ordem de inserção e retirada de NumPy, Pandas e suas dependências exclusivas. |
| MÉDIO | [roteiro](ROTEIRO_APRESENTACAO.md), relatório acadêmico | Roteiro de 12–15 minutos e referências históricas a testes e resultados. | Roteiro de 10 minutos com exemplos verificados e [instruções para atualizar o relatório](ATUALIZACOES_RELATORIO.md). |

## E. Alterações realizadas

- Os módulos em `backend/algorithms/` mantêm BFS e DFS explícitas e independentes
  da interface. A BFS reaproveita o mapa de pais para marcar descobertas e
  ambas contam arestas examinadas.
- `instance_service.py` gera os recortes em memória preservando os metadados
  necessários ao itinerário. `backend/app.py` seleciona o grafo por requisição.
  A rede completa continua sendo o padrão. A configuração `TRANSITGRAPH_DATABASE`
  permite usar um SQLite reconstruído em outro caminho.
- `app.js`, `index.html` e `style.css` apresentam o seletor, o diagnóstico de
  alcance, as métricas, a finalização e os caminhos dos algoritmos no mapa.
  Pesquisa por nome e código, Dijkstra, itinerários, mapa, componentes fracas
  e grafo interativo seguem disponíveis.
- `tests/test_traversals.py`, `test_api.py` e `test_gtfs.py` registram as
  regressões. README, roteiro e anexos de auditoria registram os resultados.
  O ZIP e o banco versionados foram mantidos.

## F. Resultados dos testes e desempenho

- Antes das alterações, 31 testes aprovados. Depois, **46 aprovados e
  zero reprovados**, também com as versões fixadas de Flask e Pytest em venv.
- O banco foi reconstruído do ZIP em arquivo temporário. Metadados, paradas,
  adjacências e sua ordem, linhas, pesos e referências de shape conferem com
  o banco versionado.
- `python run.py` iniciou o Flask. O Edge executou carregamento das três
  instâncias, comparação, DFS de cobertura, seleção por nome, BFS com
  baldeação, visualização da vizinhança, Dijkstra, seleção do caminho DFS no mapa e
  caso sem caminho. Com tráfego
  externo bloqueado só as visualizações ficaram indisponíveis. O OSRM
  esteve desativado neste ensaio. A suíte inclui testes do serviço viário.
- Na rede completa, com origem `480012875`, ambas as travessias completas
  visitaram **20.534** vértices e examinaram **26.938** arestas. A comparação
  com destino `480014632` retornou **16** arestas na BFS e **3.225** na DFS.
  As medianas e o pico de alocações constam no
  [benchmark reproduzível](BENCHMARK_RESULTADOS.md).
- Os tempos variam com máquina, origem, parada antecipada, ordem de
  adjacência e custo da instrumentação. As medições de memória excluem
  o grafo pré-carregado e cobrem alocações rastreadas pelo Python.

## G. Pendências

| Prioridade | Pendência | Risco acadêmico |
|---|---|---|
| Alta | Atualizar a versão editável do relatório e exportar o PDF final. Preencher nomes, RAs, contribuições e verificações de uso de IA. | A versão atual contém campos em aberto e resultados anteriores à correção da DFS. |
| Alta | Conferir enunciado integral e proposta aprovada com o professor se houver compromissos sobre Tarjan ou simulação de fechamento. | Possível divergência de escopo. |
| Alta | Ensaiar na máquina e na rede da apresentação. | A indisponibilidade de recursos externos afeta o mapa e o grafo visual. |
| Média | Confirmar data de obtenção e condições aplicáveis ao ZIP publicado. | Atribuição ou descrição metodológica incompleta. |

## H. Preparação para apresentação

Siga o [roteiro de 10 minutos](ROTEIRO_APRESENTACAO.md). Use o recorte
pequeno para explicar a ordem, o recorte intermediário para demonstrar
um itinerário real e a rede completa para contrastar cobertura
direcionada e existência de caminho. O roteiro registra códigos de
parada, resultados esperados e perguntas sobre fila, pilha, custos,
empates e componentes fracas.

## Verificação final para 17/11/2026

A revisão de 14/11/2026 mantém os achados das seções anteriores como
histórico. Os resultados atuais e a situação acadêmica constam abaixo.

| Requisito do Tema 1 | Situação atual e evidência |
|---|---|
| Aplicação real com grafo dirigido | Atendido. GTFS SPTrans com data de serviço 01/11/2026, importação por viagem e lista de adjacência por parada. SQLite passou em integridade e verificação de chaves estrangeiras. [Importador](../backend/gtfs/importer.py) · [Persistência](../backend/models/database.py) |
| Busca em largura e busca em profundidade | Atendido. BFS usa fila e predecessores para menor número de arestas. DFS usa pilha de quadros para descoberta, alcance e finalização. A comparação confirmada de 16 e 3.225 arestas usa a mesma origem e o mesmo destino. [BFS](../backend/algorithms/bfs.py) · [DFS](../backend/algorithms/dfs.py) |
| Instâncias e comparação na interface | Atendido. API e seletor confirmaram 7/6, 177/181 e 20.812/27.218. O recorte pequeno permite verificar à mão a ordem de visita. [Instâncias](../backend/services/instance_service.py) · [Roteiro](ROTEIRO_APRESENTACAO.md) |
| Funcionamento e demonstração | Atendido no ambiente verificado. Flask, API e interface no Edge abriram com a base padrão. O roteiro cobre busca, finalização, baldeação e ausência de caminho. [Roteiro](ROTEIRO_APRESENTACAO.md) |
| Documentação acadêmica | Parcialmente atendido. Apostila, banco de perguntas, conteúdo dos slides e roteiro estão disponíveis. DOCX/PDF têm resultados antigos e campos que exigem confirmação da equipe. [Atualizações por página](ATUALIZACOES_RELATORIO.md) |
| Compromissos da proposta e revisão humana | Não verificável no repositório. A equipe deve confirmar o enunciado integral, eventuais extensões prometidas e as verificações realizadas pelos integrantes. |

**Validação executada.** Python 3.14.0 no Windows, ambiente virtual do
projeto. `pip check` passou. `pytest -q` registrou **67 aprovados, zero
falhas**. SQLite retornou `ok` em `quick_check` e nenhuma ocorrência
em `foreign_key_check`. No Edge e com OSRM desligado, a comparação
pequena retornou as duas ordens esperadas e a DFS completa mostrou sete
descobertas e sete finalizações. A intermediária retornou 25 arestas e uma
troca de linha. A completa confirmou cobertura de 20 paradas na origem
`560009135` e ausência de caminho para `5506671`. A comparação maior
retornou 16 e 3.225 arestas. As consultas foram repetidas com tráfego
externo bloqueado no navegador. As respostas textuais permaneceram
disponíveis, com mapa e grafo interativo indisponíveis.

**Riscos para o dia.** Prepare a instalação e ensaie na máquina da sala.
O endereço local padrão usa a porta 5000. O roteiro tem alternativa de porta
e consulta pelo PowerShell. Instalação depende do índice Python, Leaflet e
Cytoscape.js vêm de CDN, os tiles vêm do OpenStreetMap e o OSRM público é
opcional. Para o tempo da apresentação, use OSRM desligado e mostre os
ajustes geográficos por captura. A consulta longa fica no slide 7.

[Guia de estudo](GUIA_ESTUDO_TRANSITGRAPH.md) ·
[38 perguntas](PERGUNTAS_PROFESSOR.md) · [Slides](CONTEUDO_SLIDES.md) ·
[Divisão](DIVISAO_APRESENTACAO.md)
