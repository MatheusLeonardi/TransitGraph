# Auditoria geográfica do TransitGraph

Base SPTrans de 01/11/2026. A revisão das pendências ao fim deste documento
registra a validação mais recente dos casos da Rua Rio Bom, da Estrada do Cipó
e da Av. Conde de Frontin. O banco padrão foi reconstruído a partir do ZIP
versionado e verificado com `quick_check` e `foreign_key_check` antes da instalação.
Para reproduzir a comparação histórica, o SQLite anterior está disponível no
Git. A cópia local usada durante a auditoria ficou em `tmp/geography-before.db`.

## Fluxo auditado

| Etapa | Evidência e decisão |
|---|---|
| GTFS original | `routes.txt` identifica a linha. `trips.txt` vincula linha, viagem, direção e shape. `stop_times.txt` ordena ocorrências por `stop_sequence`. `stops.txt` fornece latitude e longitude das paradas. `shapes.txt` fornece os pontos ordenados por `shape_pt_sequence`, com distância acumulada. O `stop_times.txt` do ZIP não inclui essa distância. |
| Importação | Antes, a otimização escolhia pontos discretos com sequência não decrescente, permitindo que duas paradas distintas recebessem o mesmo ponto. Agora, a projeção admite posições fracionárias nos segmentos, usa um custo conjunto com progressão estrita e deixa uma lacuna quando falta uma localização coerente. Feeds com distâncias nas duas tabelas podem usar interpolação pela distância, após verificar ordem, cobertura e proximidade das paradas. |
| SQLite | Antes, a referência única por par de paradas e linha descartava viagens alternativas e passagens repetidas. A tabela `trip_edges` guarda ocorrências comprimidas com viagem, shape, sentido, sequência de parada, intervalo no shape, método e erro de associação. Bancos antigos podem ser lidos, com a indicação `legacy-reference`. |
| Grafo e buscas | A topologia continua sendo o grafo dirigido de paradas. Validei igualdade da ordem das adjacências, paradas, linhas e pesos entre os dois bancos. Resultados completos de BFS e DFS também coincidiram em sete consultas, incluindo alcance e destino inalcançável. |
| Resolução do itinerário | A seleção de linhas mantém a regra de trocas existente. Dentro de cada linha, a seleção de ocorrências minimiza quebras de viagem e depois referências sem geometria. A geometria é recortada na ordem da viagem, interpolando apenas os extremos. Quando é indispensável mudar de viagem na mesma linha, a interface sinaliza a quebra no itinerário e no mapa. |
| OSRM | A integração usa **Match** exclusivamente. A solicitação usa longitude,latitude, e a resposta é convertida para latitude,longitude. A geometria é solicitada com `overview=full`. A validação exige uma única correspondência com todos os pontos de controle associados na ordem, deslocamento máximo de 45 m, confiança mínima 0,5, proporção de comprimento de 0,65 a 1,8 e verificação nos dois sentidos do corredor de 75 m. As coordenadas e a ordem são verificadas em testes independentes de rede. |
| API e Leaflet | A API envia um fragmento por conexão, com geometria GTFS, proposta OSRM quando retornada e geometria selecionada. O Leaflet desenha cada fragmento com `smoothFactor: 0`. Quando o GTFS não resolve o trecho, uma reta entre paradas só aparece tracejada e identificada como ligação aproximada. Fragmentos permanecem independentes. |

Referências de formato. [GTFS Schedule](https://gtfs.org/documentation/schedule/reference/) ·
[OSRM Match](https://project-osrm.org/docs/v26.6.1/http#match-service) ·
[Leaflet Polyline](https://leafletjs.com/reference-1.9.4.html#polyline).

## Causas comprovadas e indicadores

- O SQLite anterior tinha **302** referências com a mesma sequência no início
  e no fim. O efeito verificável era a perda do recorte e o uso da ligação
  aproximada, inclusive em trechos com shape disponível.
- Havia **1.746** pares de referências adjacentes da mesma linha com
  `trip_id` diferente. Essa contagem indica risco de mistura, incluindo
  mudanças legítimas de viagem em terminais. A nova seleção verifica
  continuidade pela ocorrência, e não apenas pelo código da parada.
- Na primeira reconstrução, 76.985 de 76.987 ocorrências receberam intervalos
  ordenados e duas ocorrências da linha 6099-10 ficaram sem recorte. A revisão
  abaixo recuperou os dois intervalos e explicitou as conexões entre códigos
  de paradas consecutivos com coordenadas idênticas.
- O diagnóstico registra maior intervalo entre pontos, comprimento do shape
  e distância direta, extremos que se ajustam melhor em ordem inversa,
  lacunas entre shapes, mudanças de viagem e rejeições OSRM. Um longo
  intervalo é um sinal de baixa resolução. Um percurso maior que a distância
  direta pode indicar um retorno legítimo, como mostra o caso da Cruzeiro do
  Sul.
- Configure o sinal de baixa resolução com `TRANSITGRAPH_GEOMETRY_GAP_M`
  (120 m) e a razão de comprimento pelo `TRANSITGRAPH_GEOMETRY_LENGTH_RATIO`
  (5, aplicada a distâncias diretas de pelo menos 25 m).

## Casos antes e depois

| Local e consulta BFS | Antes | Depois, observado no Edge |
|---|---|---|
| Av. Otto Baumgart, `8812626 → 880000949` | A referência do shape 84176 colapsava em um ponto. | Viagem 1016-10-0, progressão 391,88 → 392,23, recorte GTFS de 6,4 m. |
| R. dos Guaianases, `7014506 → 7014507` | A referência do shape 83500 também colapsava. | Viagem 118C-10-1, progressão 40,94 → 41,49, recorte GTFS de 6,5 m. |
| Pça. Mons. Escrivá, `6415321 → 640000436` | As duas conexões usavam sentidos diferentes da linha 1017-10 e eram agrupadas sob a linha. | A troca 1017-10-0 → 1017-10-1 fica explícita em `6415298`. Os fragmentos do GTFS são exibidos separadamente. [Captura](geometria/geography-direction-change.png) |
| Retorno na Av. Cruzeiro do Sul, `570014290 → 570014286` | A referência do shape 61554 colapsava em um ponto. A reta aproximada entre paradas distantes só 37,7 m ocultava o retorno. | O GTFS recupera 491,1 m. O OSRM retorna aproximadamente 494,7 m, confiança 0,985 e desvio máximo de 4 m nos pontos de controle. As sobreposições mostram o retorno na malha viária. [Captura](geometria/geography-uncertain.png) |
| Av. José Pinheiro Borges, `360007115 → 360012314` | Consulta da mesma avenida da imagem enviada. Os códigos exatos da imagem não estão disponíveis. | A consulta seleciona a viagem 2703-10-1 e o shape 85481. O recorte GTFS, com 1.360,2 m, acompanha o corredor no trecho inspecionado. [Captura](geometria/geography-pinheiro-borges.png) |
| Av. Conde de Frontin, consulta `600012584 → 3609172` | Referência do trecho esparsa. | Entre `930012567` e `9308855`, o GTFS ainda tem um intervalo de 240,8 m. No ensaio o OSRM ficou indisponível para o fragmento, e o mapa conservou o GTFS com sinalização de baixa resolução. |

As medições anteriores foram obtidas do SQLite antigo. As inspeções no Edge
usaram o novo SQLite e tiles do OpenStreetMap, com as sobreposições e seleção por
conexão verificadas. As capturas documentam o resultado para as consultas
especificadas.

## Reproduzir e verificar

Abra a aplicação, calcule uma rota e expanda **Diagnóstico geográfico**. Selecione
uma conexão no menu ou use **Diagnosticar trecho** no balão da linha. As três
camadas podem ser ligadas e desligadas. O menu inclui conexões sem linha
desenhável.

```powershell
python scripts/diagnose_geometry.py 570014290 570014286 --output tmp/geometria-gtfs.json
python scripts/diagnose_geometry.py 570014290 570014286 --osrm --output tmp/geometria-osrm.json
python -m pytest -q
```

O diagnóstico de linha de comando pode comparar a mesma consulta com dois
bancos usando `--database`. A suíte inicial incluiu 64 testes executados, com projeção
em curva e passagem repetida, distância GTFS, pontos ausentes e repetidos,
persistência de ocorrências, sentidos opostos, geometrias descontínuas e
respostas simuladas do OSRM com vias paralelas, pontos omitidos e
correspondência em ordem inversa. Os casos de regressão da SPTrans usam o
SQLite versionado e dispensam o OSRM.

## Limitações

Quando não há pontos suficientes ou sobram passagens igualmente plausíveis
em ruas paralelas, a malha de carros não permite inferir com segurança o
trajeto do ônibus. O OSRM fica restrito a shapes esparsos com pelo menos três
pontos, com limite de chamadas por consulta e fallback para o GTFS. O shape
denso oficial tem prioridade, inclusive em corredores exclusivos. A aplicação
descreve conectividade topológica, sem verificar horários, baldeação operacional
ou regras específicas de circulação a partir de observações do veículo.

Apenas os trechos inspecionados receberam validação visual. Um fragmento
sinalizado pode exigir uma versão mais precisa do GTFS ou confirmação da
SPTrans antes de ser apresentado como trajeto exato.


## Revisão das pendências para a apresentação de 17/11/2026

### Cruzamento da imagem em Itaquera

**Situação: corrigido na consulta reproduzida.** O cruzamento é a Rua Rio Bom,
entre a Av. Pires do Rio e a pista da Av. José Pinheiro Borges, junto à Rua
Oscar Wilde e ao posto visíveis na imagem. As duas junções estão próximas de
`-23.5249666, -46.4452921` e `-23.5255279, -46.4441945`. A consulta BFS
`360007756 → 760002817` liga a Av. José Pinheiro Borges, 1284, à R. Rio São
Francisco do Mogiano, 368. Ela passa pelo cruzamento em uma aresta da linha
2734-10, viagem 2734-10-1, shape 70493, ocorrências 7 → 8.

O recorte tem 877,7 m. Os quatro pontos do GTFS na Rua Rio Bom ficaram a até
1,9 m da linha central digitalizada no OSM. A captura no Edge reproduz as duas
curvas da imagem. Com o OSRM ligado ou desligado, o mapa selecionou o mesmo
GTFS. Uma consulta direta ao OSRM sugeriu 1.891 m com confiança zero e foi
rejeitada. O shape oficial já resolve a passagem na geometria atual. A causa
do eventual desvio na versão da imagem não pode ser atribuída sem a resposta
original da API. [Captura do mesmo cruzamento](geometria/followup-rio-bom-false.png) ·
[Rua Rio Bom](https://www.openstreetmap.org/way/158270855) ·
[Av. Pires do Rio](https://www.openstreetmap.org/way/350661640) ·
[Av. José Pinheiro Borges](https://www.openstreetmap.org/way/620666851).

### Estrada do Cipó, linha 6099-10

**Situação: as duas conexões foram corrigidas.** Na viagem 6099-10-0,
shape 80239, os códigos `5614821` e `5614822` têm as mesmas coordenadas e
ocorrem consecutivamente nas posições 49 e 50 de `stop_times.txt`. O shape
percorre a estrada na ida e volta. Obrigar as duas ocorrências a avançar
para pontos distintos podia levar a segunda ao ramo de volta, na posição
734 do shape. A parada 51 perdia a possibilidade de avançar até a posição
seguinte na ida. O importador agora permite posição compartilhada para
códigos consecutivos com coordenadas idênticas quando faltam distâncias GTFS
válidas que distingam as ocorrências.

| Conexão e local | GTFS recuperado | Validação |
|---|---|---|
| `5614822 → 5614776`, Estrada do Cipó, 330 → Estrada do Cipó | Sequência 618 → 621,35. Extremos a 8,8 m e 14,7 m das paradas. Comprimento 329,1 m. | GTFS tracejado com OSRM desligado por causa do intervalo de 187,5 m. Com OSRM, 329,0 m, confiança 0,980 e desvio de até 2,8 m. [Captura](geometria/followup-cipo-a-true.png) |
| `5614776 → 5614702`, Estrada do Cipó → Estrada do Cipó, 2150 | Sequência 621,35 → 657,44. Extremos a 14,7 m e 3,6 m das paradas. Comprimento 1.662,2 m. | GTFS tracejado com OSRM desligado por causa do intervalo de 168,7 m. Com OSRM, 1.661,9 m, confiança 0,984 e desvio de até 7,1 m. [Captura](geometria/followup-cipo-b-true.png) |
| `5614821 → 5614822`, Estrada do Cipó, 330 | Ambos os códigos estão na posição 618 do shape. | **Pendente como trajeto físico.** A conexão permanece no grafo. A interface mostra “sem trajeto de rua confirmado” e não cria polilinha para a ligação de distância zero. [Captura](geometria/followup-cipo-colocated-true.png) |

A regra removeu a necessidade de inferir um deslocamento para 13 ocorrências
com coordenadas idênticas no feed. O banco padrão agora tem 76.974
ocorrências com intervalos utilizáveis e 76.698 chaves de aresta e linha com
referência utilizável.

### Av. Conde de Frontin, intervalo de 240,8 m

**Situação: parcialmente corrigido.** O GTFS original contém o intervalo
entre `(-23.532125, -46.527030)` e `(-23.531855, -46.524686)`, sem pontos
intermediários, na conexão `930012567 → 9308855`. A lacuna aparece nos
shapes 84499, 84516, 81975 e 63536. A BFS direta seleciona a linha 3539-10,
viagem 3539-10-1 e shape 84499. Na consulta original
`600012584 → 3609172`, com 34 arestas, o mesmo fragmento pertence à
linha 407P-10, viagem 407P-10-1 e shape 84516.

O servidor público do OSRM recebeu a consulta com 17 pontos e respondeu
HTTP 400 com código `TooBig`. A versão anterior classificava esse erro como
indisponibilidade. A aplicação agora detecta o limite explícito e tenta
novamente com 10 pontos, mantendo os extremos, a ordem e a validação contra
o GTFS completo. A resposta válida teve confiança 0,981 e desvio máximo
de 2,7 m. O comprimento passou de 830,2 m no GTFS para 830,8 m no OSRM, e
o maior intervalo caiu de 240,8 m para 102,8 m. O resultado acompanha a pista
visível no OSM na inspeção. A lacuna permanece na fonte oficial. Sem o OSRM,
o mapa exibe o fragmento tracejado com a indicação “GTFS com traçado incerto”.
[OSRM ligado](geometria/followup-frontin-true.png) ·
[OSRM desligado](geometria/followup-frontin-false.png).

### Validação de estabilidade

- Edge com rede e tiles do OSM, em duas instâncias do Flask. Foram verificadas
  cinco consultas com cada configuração do OSRM, dez execuções no total.
  A verificação incluiu o seletor, o painel, a polilinha tracejada e o texto
  explícito no balão. A conexão com paradas na mesma coordenada não teve
  polilinha nos dois modos.
- Antes e depois da reconstrução, comparei todas as paradas, as listas
  ordenadas de adjacência, as linhas e os pesos. Os resultados completos de
  BFS e DFS foram iguais nas nove consultas, incluindo a consulta sem
  destino e uma inalcançável. A reconstrução manteve 20.812 vértices e
  27.218 arestas.
- 67 testes passaram no ambiente virtual. As regressões exercitam as duas
  conexões 6099-10, as ocorrências colocalizadas e o tratamento de
  `TooBig`. O SQLite atualizado também passou em `quick_check` e
  `foreign_key_check`.

Para a apresentação, reinicie o Flask para carregar o banco atualizado. Os exemplos
da Estrada do Cipó e da Av. Conde de Frontin demonstram a diferença entre
geometria oficial esparsa e ajuste cartográfico aceito. A verificação visual
confere a geometria com a malha do OSM. A base segue sem confirmação
operacional de circulação obtida diretamente do veículo.
