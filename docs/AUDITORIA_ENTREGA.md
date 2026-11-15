# Auditoria de encerramento do TransitGraph

**14/11/2026 · main `c858131` · data de serviço 01/11/2026**

O software está **apto para a demonstração** no ambiente verificado.
A entrega acadêmica ainda exige preenchimento e conferência pelo grupo.
A avaliação abaixo usa os requisitos informados para o Tema 1 e trata
Dijkstra como complemento.

## Diagnóstico de conformidade

| Requisito | Situação | Evidência |
|---|---|---|
| 1. BFS e DFS essenciais à solução | Atendido | A BFS resolve mínimo em número de conexões. A DFS implementada sustenta a consulta de cobertura e expõe a travessia em profundidade e as finalizações. Uma BFS completa também poderia calcular o mesmo conjunto alcançável. |
| 2. Problema real e suficientemente complexo | Atendido | Rede SPTrans com 20.812 paradas, 27.218 conexões dirigidas, múltiplas linhas por aresta e ocorrências por viagem. |
| 3. Modelagem de vértices e arestas | Atendido | Parada por ID, arco entre consecutivas de viagem ativa, direção por sequência e atributos separados por linha e ocorrência. A abstração representa conectividade de uma data. |
| 4. Implementação explícita no código do grupo | Atendido quanto à implementação. Autoria individual não verificável | BFS com deque e DFS com pilha explícita. As travessias estão no repositório em funções próprias. Contribuições e revisão humana requerem confirmação. |
| 5. Diferenças entre BFS e DFS na aplicação | Atendido | Ordens comparáveis no recorte pequeno, finalização da DFS e consulta real de 16 e 3.225 arestas. |
| 6. Resultados verificáveis | Atendido | Suíte executada, comparação com referências independentes, banco regenerado, API e navegador. |
| 7. Três instâncias | Atendido | 7/6, 177/181 e 20.812/27.218 vértices/arestas, selecionáveis na interface. São recortes da mesma base e data. |
| 8. Preparação para demonstração ao vivo | Atendido no ambiente validado | Edge com rede e com recursos externos bloqueados. Há roteiro de 10 minutos, alternativa textual e consulta pela API. A máquina da banca ainda precisa de ensaio. |
| 9. Elementos do relatório técnico | Parcialmente atendido | Estrutura, modelagem, fundamentos, arquitetura, testes, resultados, limites e Dijkstra presentes. Capa, contribuições, fonte e declaração de IA têm confirmações destacadas. |
| 10. Materiais para compreender o código | Atendido quanto ao material. Domínio individual não verificável | Relatório e slides têm excertos reais, mapa do código e roteiros. O domínio de cada integrante depende do ensaio e da apresentação oral. |

## Validação efetivamente executada

- **Suíte:** `.\.venv\Scripts\python.exe -m pytest -q` em Python 3.14.0,
  **67 aprovados**. `pip check` e a checagem de sintaxe do JavaScript passaram.
- **Correção matemática:** BFS enfileira uma vez por descoberta e retira
  em níveis. DFS mantém iteradores nos quadros e adia a descoberta dos
  irmãos enquanto desce. Ambos seguem as adjacências de saída e reconstroem
  caminhos a partir de predecessores. Dijkstra relaxa pesos não negativos,
  usa heap e descarta rótulos vencidos antes de avaliar o destino.
- **Verificações independentes desta auditoria:** 60 grafos dirigidos com
  semente fixa e **2.652 pares**. Floyd–Warshall confirmou as distâncias
  unitárias da BFS e os custos ponderados de Dijkstra. Uma DFS recursiva
  confirmou as ordens completas de descoberta e finalização. Conferi
  extremos, adjacências e validade de cada caminho retornado. Na rede
  real, relaxamento repetido confirmou os custos de Dijkstra em duas
  consultas com caminho e a ausência de caminho numa terceira. Exercitei
  também origem igual ao destino e fallback de peso em grafo pequeno.
  Essas verificações são adicionais à suíte persistida.
- **GTFS e SQLite:** reconstrução com `scripts/build_graph.py --date 2026-11-01`
  para um arquivo temporário. Paradas, ordem das adjacências, linhas, pesos,
  ocorrências e metadados foram iguais aos do banco versionado. SQLite
  passou em `quick_check` e `foreign_key_check`. Há 27.218 pesos, de 39
  a 1.800 s no banco da demonstração. Frequências do GTFS não são usadas pela
  topologia e a importação usa o calendário semanal do ZIP. A conectividade
  é estrutural e o peso agregado não comprova que o itinerário é realizável
  num horário específico.
- **Execução e interface:** iniciei `run.py` em 127.0.0.1:5000 com o banco
  incluído e OSRM desligado. Confirmei a saúde e uma consulta ponderada pelo
  PowerShell. No Edge, repeti as três instâncias, a comparação, a DFS sem
  destino, a troca de linha, Dijkstra e casos sem caminho. Com serviços
  externos bloqueados no navegador, as respostas textuais permaneceram
  disponíveis. Com rede, Leaflet, Cytoscape.js e tiles carregaram.
- **Artefatos:** abri o DOCX no Microsoft Word e renderizei o PDF versionado
  e a exportação da cópia Word. Ambos têm 12 páginas. As diferenças de texto
  extraído correspondem a cabeçalhos de tabela que se repetem em quebras
  diferentes. No Microsoft PowerPoint, abri e exportei os 10 slides
  oficiais e os 32 de estudo. Conferi 20 e 47 linhas numeradas de código,
  respectivamente, contra os arquivos atuais e revi a disposição visual.

### Resultados de referência

| Instância e consulta | BFS | DFS | Dijkstra ou itinerário |
|---|---|---|---|
| Pequena · `480012875 → 480014889` | 2 arestas, 4 visitas, 7 descobertas | 2 arestas, 3 descobertas | Sem destino, DFS tem 7 descobertas e 7 finalizações. |
| Intermediária · `8812664 → 940004410` | 25 arestas | 25 arestas | Uma troca na apresentação do caminho BFS. |
| Completa · `480012875 → 480014632` | 16 arestas, 640 visitas | 3.225 arestas, 14.065 descobertas | 16 arestas e 1.906,0 s. |
| Completa · `560009135 → 5506671` | Sem caminho, 20 visitas | Sem caminho, 20 descobertas | Sem caminho. |
| Completa · `600012584 → 3609172` | 34 arestas. Ao somar os mesmos pesos do banco, 4.046,0 s. | 3.872 arestas | 39 arestas, 3.380,5 s, todos os pesos vindos do GTFS. |

Os tempos da última coluna são pesos somados, em segundos. As medianas
no [benchmark](BENCHMARK_RESULTADOS.md) medem o tempo de execução da busca
em milissegundos. O ganho ponderado de 665,5 s na última consulta é uma
diferença dentro do modelo. [Guia de defesa](GUIA_DEFESA_DO_PROJETO.md)

## Problemas e pendências

| Gravidade | Achado | Efeito na banca |
|---|---|---|
| CRÍTICO | Nenhum encontrado. | A execução e as verificações independentes passaram. |
| ALTO | Capa oficial ainda pede os cinco nomes. O relatório marca nomes, RAs, contribuições, data de coleta, escopo aprovado e revisão humana da IA. | A versão atual ainda exige preenchimento e reexportação antes da entrega. |
| MÉDIO | O relatório explica Dijkstra, mas suas seções 8 e 9.5 registram que a versão textual ainda não tinha nova medição ponderada. O PowerPoint oficial concentra-se em BFS e DFS. O material de estudo explica os pesos no slide 18, sem exemplo numérico. | Use a consulta `600012584 → 3609172` como reserva para explicar a recomendação do professor. O fechamento do relatório pode incorporar a evidência da tabela acima. |
| MÉDIO | Os testes persistidos só acionam Dijkstra no cenário de entrada inválida, em `tests/test_api.py`. | A suíte de 67 não deve ser descrita como cobrindo a otimalidade ponderada. Nesta auditoria há verificações independentes registradas. |
| BAIXO | `ATUALIZACOES_RELATORIO.md` aponta para dois nomes de arquivo antigos, sem o sufixo `_Dijkstra`. | Abra o [DOCX atual](../output/documents/TransitGraph_Relatorio_Tecnico_Final_Dijkstra.docx) e o [PDF atual](../output/documents/TransitGraph_Relatorio_Tecnico_Final_Dijkstra.pdf) diretamente. |
| BAIXO | O README usa `venv` com ativação e o roteiro usa `.venv` com chamada direta. O mapa do código referencia `871007e` e se concentra em BFS/DFS. O código verificado permanece igual no commit atual. | Use os comandos do guia e consulte a trilha de Dijkstra incluída nele para perguntas. |

A aprovação da parte técnica não atesta a autoria de cada trecho, a
aderência a compromissos de uma proposta que não foi fornecida, nem o
domínio individual da equipe. Confirmem esses pontos no ensaio. O código,
o banco, os relatórios e as apresentações foram inspecionados sem edição.
