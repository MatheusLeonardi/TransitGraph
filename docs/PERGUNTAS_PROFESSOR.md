# Perguntas do professor

Use as respostas para ensaiar em voz alta. Nos exemplos reais, considere a
rede SPTrans de 01/11/2026 e identifique a instância da consulta.

## Básica

1. **Por que usar grafos para modelar a rede de ônibus?** A rede contém pontos de parada e conexões entre eles. As listas de vizinhos permitem perguntar se duas paradas se conectam e quais podem ser atingidas a partir de uma origem.
2. **O que são vértice e aresta no TransitGraph?** O vértice é uma parada identificada por `stop_id`. A aresta é a conexão de uma parada à seguinte na sequência de uma viagem ativa.
3. **Por que o grafo é direcionado?** A ordem das paradas informa o sentido do deslocamento. O sentido inverso exige uma aresta própria, criada quando o GTFS registra uma viagem que faz essa ligação.
4. **Como funciona a BFS?** A origem entra na fila. Em cada retirada, os vizinhos inéditos entram ao final com o predecessor registrado. Assim a busca visita por níveis a partir da origem.
5. **Como funciona a DFS?** O topo da pilha guarda o vértice ativo e o ponto em que a leitura da adjacência parou. Um vizinho novo vira o próximo quadro. Ao esgotar vizinhos, a busca volta ao quadro anterior.
6. **Qual é a diferença entre fila e pilha?** A fila FIFO retira o elemento mais antigo. A pilha retira o elemento mais recente.
7. **Por que a BFS encontra o menor número de arestas?** A fila visita em ordem de distância. Um caminho mais curto descobriria o vértice num nível anterior. Logo a primeira descoberta guarda um predecessor de caminho mínimo.
8. **Por que a DFS pode encontrar caminhos muito maiores?** Ela segue a ordem dos ramos e para ao descobrir o destino. Na rede completa, `480012875 → 480014632` retornou 16 arestas na BFS e 3.225 na DFS.
9. **Como são evitados ciclos infinitos?** A entrada em `parent` marca a descoberta. A BFS registra antes de enfileirar e a DFS antes de empilhar. Arestas para vértices já descobertos são examinadas sem redescoberta.
10. **O que acontece se não existir caminho?** Com duas paradas válidas, a busca esgota o conjunto alcançável e retorna `found=false` com caminho e distância nulos. A interface exibe a ausência de caminho dirigido.
11. **Como são tratadas paradas isoladas?** Se a origem existe e não tem vizinhos de saída, a visita contém apenas ela. Se também não recebe arestas, o painel de conectividade pode identificá-la como isolada na projeção fraca.
12. **E quando origem e destino são iguais?** A origem é o caminho de um vértice e zero arestas.
13. **O que uma aresta do caminho mede?** Uma transição para a próxima parada. O itinerário calcula trocas entre linhas selecionadas. Dijkstra soma tempos por aresta.

## Intermediária

14. **Qual é a complexidade de BFS e DFS?** O(V + E) em tempo e O(V) de memória auxiliar no pior caso sobre o subgrafo alcançável. Os vizinhos são lidos por listas de adjacência e cada vértice é descoberto uma vez.
15. **Por que usar dicionários de vizinhos?** Eles evitam duplicar arestas com o mesmo par dirigido, preservam a ordem de inserção e ocupam espaço proporcional aos vértices e arestas.
16. **Como a ordem dos vizinhos influencia o resultado?** Na BFS ela define a ordem dentro de um nível e os empates de caminho mínimo. Na DFS ela define qual ramo avança primeiro e pode alterar o comprimento do caminho encontrado.
17. **Como a interface mostra BFS e DFS?** A comparação usa a mesma instância e o mesmo par de paradas. Ela exibe descoberta, visitas, arestas examinadas, caminho e tempo medido no algoritmo, além da finalização da DFS.
18. **Descoberta e visita são sempre iguais?** Na BFS a retirada conta como visita. Ao retirar o destino, outras paradas podem ficar na fila. Na DFS a ordem de visita corresponde à ordem de descoberta.
19. **O que é finalização na DFS?** O vértice termina quando o iterador de vizinhos se esgota e seu quadro é retirado da pilha. Uma descoberta de destino pode interromper a busca antes da finalização dos quadros ativos.
20. **Como é reconstruído o caminho?** Segue-se `parent` do destino até a origem e inverte-se a lista. O número de arestas é a quantidade de vértices no caminho menos um.
21. **Por que ambas podem obter a mesma cobertura?** Se forem executadas sem destino, ambas continuam até esgotar todos os vértices alcançáveis. Com destino, os critérios de parada produzem visitas parciais diferentes.
22. **O que distingue cobertura de componente fraca?** A cobertura depende da origem e segue o sentido das conexões. A componente fraca reúne paradas após ignorar a orientação. A rede completa tem quatro componentes fracas de tamanhos 20.797, 11, 2 e 2.
23. **Como o GTFS é importado?** O importador seleciona viagens de ônibus ativas na data, ordena paradas de cada viagem por `stop_sequence` e cria as conexões dirigidas. Também associa linha, horários e referências de shape.
24. **Qual é a função do SQLite?** Manter o resultado do pré-processamento entre execuções. Ao iniciar, o Flask carrega as adjacências e os metadados. Os pontos comprimidos dos shapes são buscados quando o itinerário precisa deles.
25. **Por que os algoritmos funcionam sem mapa?** BFS e DFS recebem o grafo e os códigos das paradas. O itinerário, a geometria e o desenho no Leaflet são preparados depois que a busca devolve seu resultado.
26. **O que muda ao trocar de instância?** Mudam as adjacências disponíveis. O recorte local tem 7 vértices e 6 arestas, o de duas linhas tem 177 e 181, e a rede completa tem 20.812 e 27.218. A data de serviço é a mesma.

## Avançada

27. **Como as linhas e viagens são representadas?** A aresta mantém o conjunto de linhas que a atendem. As ocorrências guardam viagem, direção, posições de parada e intervalos no shape. O itinerário tenta continuar na mesma viagem dentro de uma linha.
28. **A rota tem o mínimo global de baldeações?** A otimização de trocas é feita depois da busca e se restringe à sequência de paradas encontrada. Minimizar trocas globalmente exigiria outra função objetivo e um modelo com a linha atual como parte do estado.
29. **O que sustenta os pesos do Dijkstra?** A mediana dos intervalos válidos de tempo programado por aresta. Quando faltam amostras, estima-se tempo por distância reta a 18 km/h, com um valor padrão se faltarem coordenadas. O cálculo estima deslocamento entre paradas.
30. **Como o shape é associado à parada certa?** Com distâncias GTFS consistentes nos dois arquivos, usa-se a posição indicada. No feed apresentado faltam as distâncias em `stop_times.txt`, então as paradas são projetadas sobre os segmentos em ordem. Códigos consecutivos com a mesma coordenada podem compartilhar posição.
31. **Qual é o papel do OSRM?** Refinar certos fragmentos esparsos usando a malha do OpenStreetMap. A aplicação verifica confiança, ordem, deslocamento e corredor antes de usar a proposta. O perfil público de carro pode divergir de corredores exclusivos.
32. **Como o mapa sinaliza dados incertos?** Traços esparsos ou ligações aproximadas aparecem tracejados quando aplicável. Com dois códigos na mesma coordenada, o mapa pode omitir a polilinha e informar que o trajeto de rua está sem confirmação.
33. **Como foi validada a correção dos algoritmos?** Testes com caminhos e ordens esperados, ciclos, direção, empates e uma cadeia de 5.000 vértices, além de casos reais confirmados na API e na interface. A execução final registrou 67 testes aprovados.
34. **É possível concluir que a BFS é mais rápida em geral?** Uma consulta com destino compara o trabalho feito até pontos de parada diferentes. Compare repetições, contagens e modalidade de busca. Ambos os algoritmos têm o mesmo limite assintótico com a representação atual.
35. **O que acontece com uma rede muito maior?** O custo de atravessar a parte alcançável cresce com vértices e arestas. A pilha explícita permite profundidade maior que o limite de recursão. Memória, payload, montagem do itinerário e renderização também devem ser medidos.
36. **Que limitações importam quando alguém tenta usar a rota?** A base usa GTFS estático de uma data de serviço, sem trânsito, espera, caminhada ou confirmação de compatibilidade de horários e transferências. A geometria pode ser aproximada. A API mostra até 200 registros por ordem e conserva o total.
37. **Qual é a diferença entre uma parada inválida e uma parada inalcançável?** A primeira não pertence à instância ou tem formato inválido. A API rejeita a entrada. A segunda é válida e recebe a resposta de busca concluída sem caminho.
38. **O que fica disponível sem acesso externo?** Com o Flask e o navegador no mesmo computador, continuam disponíveis as buscas locais, os itinerários textuais, as estatísticas e as listas de visita. O fundo cartográfico, o grafo interativo e o ajuste viário dependem dos recursos externos correspondentes.

[Guia de estudo](GUIA_ESTUDO_TRANSITGRAPH.md) ·
[Auditoria técnica](AUDITORIA.md) · [Reprodução](ROTEIRO_APRESENTACAO.md)
