# Atualização do relatório técnico para a entrega

Revisão de 14/11/2026. O mapa abaixo registra as correções feitas a partir
do PDF anterior. A paginação da coluna se refere ao original preservado.
A versão atual está disponível em [DOCX](../output/documents/TransitGraph_Relatorio_Tecnico_Final.docx)
e [PDF de revisão](../output/documents/TransitGraph_Relatorio_Tecnico_Final.pdf).
Os campos destacados ainda precisam de confirmação humana.

| Página e seção | Ajuste com evidência |
|---|---|
| 1 e 10 · Capa e contribuições | Completar nomes, RAs e contribuições confirmadas. |
| 3–5 · Dados e grafo | Manter o total da rede completa, 20.812 paradas e 27.218 arestas. Acrescentar os recortes selecionáveis de 7/6 e 177/181 vértices/arestas. Indicar os pesos por mediana de segundos para Dijkstra e a contagem unitária para BFS. |
| 5–6 · Buscas e itinerário | Descrever a pilha explícita de quadros da DFS, a descoberta e a finalização. A API guarda até 200 registros de cada ordem retornada e mantém os totais. A montagem do itinerário tenta continuar na mesma viagem em cada sequência da mesma linha. |
| 6–7 · Geometria e API | Registrar 76.987 ocorrências armazenadas e 13 conexões colocalizadas sem trajeto de rua confirmado. Explicar o sinal tracejado e o refinamento opcional. O OSRM em perfil de carro é uma inferência cartográfica. [Auditoria geográfica](AUDITORIA_GEOMETRIA.md) |
| 7 · Testes e benchmark | Substituir “30 passed” por **67 testes aprovados**, confirmados em Python 3.14. Atualizar a metodologia. As tabelas atuais medem as três instâncias reais, com 21 repetições e modalidades com e sem destino. [Benchmark](BENCHMARK_RESULTADOS.md) |
| 8–9 · Figuras e comparação | Atualizar as telas. O caso `600012584 → 3609172` tem BFS com 34 arestas e 3.258 visitas, DFS com 3.872 arestas e 6.427 visitas. O exemplo preferido dos slides, `480012875 → 480014632`, tem BFS com 16 arestas e 640 visitas, DFS com 3.225 arestas e 14.065 visitas. [Captura atual da comparação](apresentacao/comparacao-pequena.png) |
| 9–10 · Escopo e limitações | Tamanhos das componentes fracas permanecem 20.797, 11, 2 e 2. O seletor já existe. Declarar qualidade variável do mapa, dependências externas e ausência de verificação operacional de passagem e horários. |
| 11 · Uso de IA | Atualizar a descrição de uso e separar evidências automatizadas desta auditoria das verificações humanas de fato realizadas pelo grupo. |

## Dados e fonte

O GTFS versionado identifica a SPTrans e a versão 311026. A data de
serviço da reconstrução é 01/11/2026. O SHA-256 do ZIP é
`a948ac3b23507ac456d94a1c40dde94740d057c82b7648ee8ec861bd2be9e1ac`.
Confirme com quem coletou os dados a data de obtenção.
[SPTrans](https://www.sptrans.com.br/desenvolvedores) ·
[Especificação GTFS](https://gtfs.org/documentation/schedule/reference/)

## Confirmações do grupo

- **Identificação** Confira os cinco nomes completos e os respectivos RAs.
  A capa contém campos em aberto.
- **Contribuições** Descreva o que cada pessoa fez, com os arquivos,
  experimentos ou materiais correspondentes. A divisão da fala serve ao
  ensaio.
- **Escopo da disciplina** Confira o enunciado integral e a proposta
  aprovada. Confirme se Tarjan, pontes, articulações ou simulação de
  fechamento foram compromissos adicionais.
- **IA e revisão humana** Codex (OpenAI) apoiou as auditorias, as correções
  técnicas, os testes e a elaboração da documentação e do material
  didático. O relatório existente registra Claude (Anthropic) na revisão
  inicial e no rascunho. Confirme essa informação e registre quais pessoas
  revisaram o código, repetiram os testes ou validaram a apresentação.
- **Versão final** Depois da aprovação do grupo, atualize o DOCX e exporte
  o PDF. Confira a capa, as figuras, as referências, a tabela de IA e a
  legibilidade das tabelas em todas as páginas.

[Auditoria final](AUDITORIA.md#verificação-final-para-17112026) ·
[Guia de estudo](GUIA_ESTUDO_TRANSITGRAPH.md) ·
[Roteiro de demonstração](ROTEIRO_APRESENTACAO.md)
