# Atualizacoes necessarias no relatorio tecnico

Este arquivo registra o estado verificado do TransitGraph em 02/11/2026. Ele
serve como base para atualizar o documento editavel antes de gerar o PDF final.

## 1. Numeros verificados

Banco `data/processed/transitgraph.db`, data de servico 01/11/2026:

| Medida | Valor |
| --- | ---: |
| Paradas no grafo | 20.812 |
| Arestas direcionadas | 27.218 |
| Associacoes linha-aresta | 76.711 |
| Viagens ativas processadas | 1.774 |
| Shapes ativos | 1.774 |
| Associacoes linha-aresta com geometria validada | 76.651 |
| Associacoes rejeitadas por distancia ao shape | 60 |
| Componentes fracamente conexas | 4 |
| Tamanho da maior componente | 20.797 |

## 2. Correcao da secao sobre shapes e ruas

Substituir a afirmacao de que `shapes.txt` nao e usado pelo texto abaixo:

> O arquivo `shapes.txt` fornece a geometria oficial dos itinerarios. Para cada
> viagem ativa, as paradas sao associadas aos pontos do shape em ordem de
> percurso por programacao dinamica. Associacoes cuja parada fica a mais de 150
> metros do ponto selecionado sao rejeitadas. Depois que BFS ou DFS determina o
> caminho no grafo de paradas, a aplicacao usa essas geometrias somente para
> desenhar o itinerario; elas nao alteram a ordem nem a corretude da busca.

Acrescentar a explicacao sobre o refinamento viario:

> Em trechos nos quais o shape possui intervalos maiores que 60 metros, a
> aplicacao pode consultar o OSRM para ajustar a polilinha a malha viaria do
> OpenStreetMap. O resultado so e aceito quando respeita limites de confianca,
> comprimento e proximidade com a geometria GTFS. Falhas, resultados incoerentes
> ou indisponibilidade do servico preservam integralmente o shape oficial. Os
> resultados aceitos e rejeitados sao armazenados em cache no SQLite.

Evitar afirmar que a aplicacao garante todas as regras de mao de direcao. A
direcao das arestas vem da ordem das paradas nas viagens GTFS. O OSRM melhora a
geometria visual, mas nao substitui a topologia oficial nem a busca BFS/DFS.

## 3. Ordem de visita

Remover a pendencia que afirma que a interface exibe apenas contagens. A versao
atual mostra:

- ordem de processamento dos vertices;
- quantidade processada e descoberta;
- caminho encontrado e distancia em arestas;
- comparacao lado a lado entre BFS e DFS;
- limite visual das primeiras 200 visitas, mantendo o total no resultado.

## 4. Execucao e testes

O comando correto e:

```powershell
python run.py
```

O `run.py` nao esta mais vazio. A verificacao atual da suite e:

```text
30 passed
```

Os testes cobrem BFS, DFS, ordem de visita, grafo direcionado, componentes
fracas, API, importacao GTFS, SQLite, shapes e refinamento viario.

## 5. Desempenho reproduzivel

Os resultados devem ser regenerados com:

```powershell
python scripts/benchmark.py --output docs/BENCHMARK_RESULTADOS.md
```

Na execucao de 02/11/2026, em Windows 11, Python 3.14 e processador AMD64 Family
25 Model 33, foram obtidas as seguintes medianas:

| Instancia | V | E | BFS | DFS completa |
| --- | ---: | ---: | ---: | ---: |
| Grafo real | 20.812 | 27.218 | 6,54 ms | 12,58 ms |
| Sintetico | 1.000 | 1.997 | 0,45 ms | 0,51 ms |
| Sintetico | 5.000 | 9.997 | 2,63 ms | 2,93 ms |
| Sintetico | 20.000 | 39.997 | 10,91 ms | 11,73 ms |
| Sintetico | 50.000 | 99.997 | 26,72 ms | 30,20 ms |
| Sintetico | 100.000 | 199.997 | 56,85 ms | 67,07 ms |
| Sintetico | 200.000 | 399.997 | 134,78 ms | 164,84 ms |

Esses tempos nao devem ser apresentados como universais. O relatorio precisa
informar maquina, sistema, versao do Python, quantidade de repeticoes e semente.

## 6. Escopo de Tarjan e selecao de instancias

Tarjan nao faz parte dos algoritmos obrigatorios do Tema 1 fornecido ao grupo,
que exige BFS e DFS. Se pontos de articulacao, pontes ou simulacao de fechamento
constarem na proposta aprovada, o grupo deve escolher uma destas opcoes:

1. implementar e demonstrar a extensao; ou
2. registrar que o escopo foi ajustado, mantendo BFS e DFS como partes
   essenciais e completas da solucao, e comunicar isso ao professor.

O mesmo vale para o seletor de instancias: confirmar a exigencia no enunciado
completo antes de acrescentar uma funcionalidade que nao aparece no trecho do
Tema 1 disponibilizado.

## 7. Campos que o grupo precisa fornecer

- nome completo e RA dos cinco integrantes;
- frente e contribuicoes concretas de cada integrante;
- confirmacao de que todos conseguem explicar sua parte;
- historico Git com contribuicoes dos integrantes;
- decisao registrada sobre Tarjan e seletor de instancias;
- capturas atuais da interface;
- revisao final dos resultados na maquina da apresentacao.

## 8. Declaracao de uso de IA

O documento deve declarar de forma transparente o uso das ferramentas. Texto
sugerido para o uso do Codex:

> Codex (OpenAI) - apoio na revisao do repositorio, implementacao e teste da
> exibicao da ordem de visita, persistencia de shapes, refinamento viario,
> validacoes, documentacao e benchmark. As alteracoes foram revisadas pelo grupo
> por leitura do codigo, execucao da suite automatizada e verificacao visual da
> interface.

Cada integrante deve conseguir explicar o codigo produzido ou revisado com
auxilio de IA. A declaracao deve citar somente verificacoes que o grupo de fato
realizou.

## 9. Ajustes visuais no PDF

- substituir as capturas antigas por imagens da interface atual;
- mostrar a comparacao BFS x DFS e a ordem de visita;
- incluir uma captura de itinerario usando shape/OSRM;
- impedir a divisao da tabela de IA entre duas paginas;
- evitar uma ultima pagina quase vazia;
- separar melhor as referencias Leaflet e Flask;
- remover todos os blocos amarelos `[PENDENTE]` da versao final.
