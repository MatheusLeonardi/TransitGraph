# Roteiro da apresentação e demonstração ao vivo

**17/11/2026 · 10 minutos · Demonstração de 4:50 a 8:10**

## Preparar no PowerShell

Use Python 3.14 e a cópia do projeto em `D:\transitgraph`. Na primeira
preparação, instale as dependências com acesso ao índice Python. Se a
`.venv` já estiver pronta, pule a criação e instalação.

```powershell
Set-Location D:\transitgraph
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

Use o SQLite já incluído. Se houver uma cópia antiga do servidor em execução,
encerre-a com **Ctrl+C** no terminal que a iniciou. Abra o PowerShell da
apresentação e rode:

```powershell
Set-Location D:\transitgraph
$env:TRANSITGRAPH_DATABASE = (Resolve-Path .\data\processed\transitgraph.db).Path
$env:TRANSITGRAPH_MAP_MATCHING = "0"
.\.venv\Scripts\python.exe run.py
```

Abra [TransitGraph](http://127.0.0.1:5000) e, em outro terminal, confirme
`Invoke-RestMethod http://127.0.0.1:5000/api/health`. O resultado esperado
é `online`, 20.812 vértices, 27.218 arestas. Deixe a aplicação aberta junto
dos slides.

## Sequência cronometrada

| Relógio | Ação |
|---|---|
| 0:00–2:25 | Slides 1–4. Problema, fonte, instâncias e modelagem. |
| 2:25–4:05 | Slides 5–6. Explique fila e pilha com o exemplo didático. |
| 4:05–4:50 | Slide 7. Mostre 16 e 3.225 arestas no mesmo par de paradas. |
| 4:50–5:55 | Slide 8. Compare na pequena, depois rode DFS sem destino e abra a finalização. |
| 5:55–6:45 | Slide 8. Na intermediária, rode a BFS e mostre a troca de linha. |
| 6:45–8:10 | Slide 8. Na completa, mostre o alcance de uma origem e o caso sem caminho. |
| 8:10–10:00 | Slides 9–10. Testes, resultados e limites do modelo. |

## Consultas na interface

1. **Pequena · Dois níveis na Vila Leopoldina.** Selecione no topo e clique
   **Carregar**. Confirme 7 paradas e 6 conexões. Digite origem `480012875`
   e destino `480014889`. Clique **Comparar BFS × DFS**. Ambas encontram
   duas arestas e o caminho `480012875 → 480014888 → 480014889`. A BFS
   visita `480012875, 480014888, 4811488, 480014889`. A DFS descobre
   `480012875, 480014888, 480014889`.
2. Deixe o **destino em branco** e clique **Analisar alcance (DFS)**. Mostre
   **7 de 7** alcançáveis e expanda **Ordem de finalização (retornos)**. A
   origem aparece por último. A lista é `480014889, 480014888, 4814601,
   480012828, 480012830, 4811488, 480012875`.
3. **Intermediária · Linhas 2025-10 e 172K-10.** Carregue a instância e
   confirme 177 paradas e 181 conexões. Digite `8812664` (Sesc Santana) e
   `940004410` (Av. Júlio Buono, 2007). Clique **Executar BFS**. Mostre as
   **25 arestas** e a troca de `2025-10` para `172K-10`. Se o mapa estiver
   disponível, indique o caminho desenhado. A troca também aparece no texto.
4. **Grande · Rede completa.** Carregue a instância. Digite `560009135`
   (Av. Jaceguava, 1354) e deixe o destino vazio. Clique **Analisar alcance
   (DFS)**. A aplicação mostra **20 de 20.812** alcançáveis. Preencha
   `5506671` (Av. Morumbi, 5595) e clique **Comparar BFS × DFS**.
   As duas buscas exibem ausência de caminho e **20 visitas** cada.

Se houver tempo em perguntas, a rede completa também permite comparar
`480012875 → 480014632`. São **16 arestas** e 640 visitas na BFS, e
**3.225 arestas** e 14.065 visitas na DFS. Essa consulta mais longa fica
registrada no slide 7. Use **Diagnóstico geográfico** para explicar a
diferença entre um recorte de shape e um ajuste viário aceito. As capturas
da Conde de Frontin permitem explicar isso com o OSRM desligado.
[Diagnóstico e capturas](AUDITORIA_GEOMETRIA.md)

## Se os serviços externos falharem

- Continue na interface pelos textos, caminhos, ordens e contagens. O
  navegador testado manteve essas funções com tráfego externo bloqueado.
  Leaflet e Cytoscape.js usam CDN e os tiles vêm do OpenStreetMap.
- Para mostrar a visualização, tenha a [captura da comparação](apresentacao/comparacao-pequena.png)
  e a [captura do grafo pequeno](apresentacao/grafo-pequena.png) abertas.
- Se o navegador não carregar a interface, teste o servidor no terminal
  com o Flask aberto. A resposta esperada contém duas arestas em ambas
  as buscas e as ordens do exemplo pequeno.

```powershell
$entrada = @{ origin = '480012875'; destination = '480014889' } | ConvertTo-Json -Compress
$uri = 'http://127.0.0.1:5000/api/algorithms/compare?instance=local'
$resposta = Invoke-RestMethod -Method Post -Uri $uri -ContentType 'application/json' -Body $entrada
$resposta.bfs | Select-Object distance, path, visited_order
$resposta.dfs | Select-Object distance, path, visited_order, finish_order
```

- Se a porta 5000 estiver ocupada por outro aplicativo, use uma porta livre
  com `.\.venv\Scripts\python.exe -m flask --app backend.app:app run --port 5001`
  e troque a porta nas URLs.

[Conteúdo dos slides](CONTEUDO_SLIDES.md) · [Divisão dos cinco integrantes](DIVISAO_APRESENTACAO.md) ·
[Perguntas do professor](PERGUNTAS_PROFESSOR.md)
