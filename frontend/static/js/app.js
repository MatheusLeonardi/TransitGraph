
const map = L.map("map").setView([-23.5505, -46.6333], 11);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19
}).addTo(map);

const stopLayer = L.layerGroup().addTo(map);

let pathLayer = null;
let searchMarker = null;
let mapRequest = null;


// --------------------------------------------------
// CARREGAR ESTATÍSTICAS
// --------------------------------------------------

async function loadStats() {
    try {
        const [statsResponse, connectivityResponse] = await Promise.all([
            fetch("/api/stats"),
            fetch("/api/connectivity")
        ]);

        if (!statsResponse.ok || !connectivityResponse.ok) {
            throw new Error("Falha ao carregar estatísticas.");
        }

        const stats = await statsResponse.json();
        const connectivity = await connectivityResponse.json();

        document.getElementById("total-stops").textContent =
            stats.vertices.toLocaleString("pt-BR");

        document.getElementById("total-edges").textContent =
            stats.edges.toLocaleString("pt-BR");

        document.getElementById("total-routes").textContent =
            stats.edge_routes.toLocaleString("pt-BR");

        document.getElementById("total-components").textContent =
            connectivity.component_count;

        document.getElementById("connectivity-info").innerHTML = `
            <div>
                Componentes
                <strong>${connectivity.component_count}</strong>
            </div>
            <div>
                Maior componente
                <strong>${connectivity.largest_component_size.toLocaleString("pt-BR")}</strong>
            </div>
            <div>
                Paradas isoladas
                <strong>${connectivity.isolated_stops.length}</strong>
            </div>
            <div>
                Tamanhos dos componentes
                <strong>${connectivity.component_sizes.join(" / ")}</strong>
            </div>
        `;

    } catch (error) {
        console.error(error);
        document.getElementById("connectivity-info").textContent =
            "Não foi possível carregar as estatísticas.";
    }
}


// --------------------------------------------------
// CARREGAR PARADAS DA REGIÃO VISÍVEL DO MAPA
// --------------------------------------------------

async function loadMapStops() {

    if (mapRequest) {
        mapRequest.abort();
    }

    mapRequest = new AbortController();

    const bounds = map.getBounds();

    const params = new URLSearchParams({
        south: bounds.getSouth(),
        north: bounds.getNorth(),
        west: bounds.getWest(),
        east: bounds.getEast(),
        limit: 3000
    });

    try {
        const response = await fetch(
            `/api/stops/map?${params}`,
            { signal: mapRequest.signal }
        );

        if (!response.ok) {
            throw new Error("Erro ao carregar paradas.");
        }

        const data = await response.json();

        stopLayer.clearLayers();

        data.stops.forEach(stop => {

            const marker = L.circleMarker(
                [stop.latitude, stop.longitude],
                {
                    radius: 3,
                    color: "#ffffff",
                    weight: 1,
                    fillColor: "#2878ed",
                    fillOpacity: 0.85
                }
            );

            const popup = document.createElement("div");
            const name = document.createElement("strong");
            const code = document.createElement("div");

            name.textContent = stop.name || "Parada sem nome";
            code.textContent = `Código: ${stop.stop_id}`;

            popup.append(name, code);
            marker.bindPopup(popup);

            stopLayer.addLayer(marker);
        });

        document.getElementById("map-count").textContent =
            `${data.count.toLocaleString("pt-BR")} paradas nesta área`;

    } catch (error) {
        if (error.name !== "AbortError") {
            console.error(error);
            document.getElementById("map-count").textContent =
                "Erro ao carregar paradas.";
        }
    }
}


// --------------------------------------------------
// PESQUISAR PARADAS
// --------------------------------------------------

async function searchStops() {

    const query = document.getElementById("search-input").value.trim();
    const results = document.getElementById("search-results");

    if (!query) {
        results.textContent = "Digite um nome ou código.";
        return;
    }

    results.textContent = "Pesquisando...";

    try {
        const response = await fetch(
            `/api/stops?q=${encodeURIComponent(query)}&limit=30`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Erro na pesquisa.");
        }

        results.replaceChildren();

        if (data.stops.length === 0) {
            results.textContent = "Nenhuma parada encontrada.";
            return;
        }

        data.stops.forEach(stop => {

            const button = document.createElement("button");
            button.className = "search-result";

            const title = document.createElement("strong");
            title.textContent = stop.name || "Parada sem nome";

            const details = document.createElement("small");
            details.textContent = `Código: ${stop.stop_id}`;

            button.append(title, details);

            button.addEventListener("click", () => {

                document.getElementById("origin").value = stop.stop_id;

                map.setView(
                    [stop.latitude, stop.longitude],
                    17
                );

                if (searchMarker) {
                    map.removeLayer(searchMarker);
                }

                searchMarker = L.marker([
                    stop.latitude,
                    stop.longitude
                ]).addTo(map);

                const popup = document.createElement("div");
                popup.textContent = `${stop.name} (${stop.stop_id})`;
                searchMarker.bindPopup(popup).openPopup();
            });

            results.appendChild(button);
        });

    } catch (error) {
        results.textContent = error.message;
    }
}


// --------------------------------------------------
// EXECUTAR BFS
// --------------------------------------------------

async function executeBFS() {

    const origin = document.getElementById("origin").value.trim();
    const destination = document.getElementById("destination").value.trim();
    const resultBox = document.getElementById("algorithm-result");

    if (!origin || !destination) {
        resultBox.textContent = "Informe a origem e o destino.";
        return;
    }

    resultBox.textContent = "Executando BFS...";

    try {
        const response = await fetch("/api/algorithms/bfs", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ origin, destination })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Erro ao executar BFS.");
        }

        if (!data.found) {
            resultBox.textContent =
                "Não foi encontrado um caminho entre essas paradas.";
            clearPath();
            return;
        }

        resultBox.replaceChildren();

        const title = document.createElement("strong");
        title.textContent = "Caminho encontrado!";

        const distance = document.createElement("div");
        distance.textContent = `Distância: ${data.distance} arestas`;

        const visited = document.createElement("div");
        visited.textContent =
            `Paradas visitadas: ${data.visited_count}`;

        const path = document.createElement("div");
        path.textContent =
            `Caminho: ${data.path.join(" → ")}`;

        resultBox.append(title, distance, visited, path);

        drawPath(data.path_stops);

    } catch (error) {
        resultBox.textContent = error.message;
    }
}


// --------------------------------------------------
// DESENHAR CAMINHO DO BFS
// --------------------------------------------------

function clearPath() {
    if (pathLayer) {
        map.removeLayer(pathLayer);
        pathLayer = null;
    }
}

function drawPath(stops) {

    clearPath();

    if (!stops || stops.length === 0) return;

    const coordinates = stops.map(stop => [
        stop.latitude,
        stop.longitude
    ]);

    pathLayer = L.polyline(coordinates, {
        color: "#e94b64",
        weight: 5,
        opacity: 0.9
    }).addTo(map);

    map.fitBounds(pathLayer.getBounds(), {
        padding: [45, 45]
    });
}


// --------------------------------------------------
// EXECUTAR DFS
// --------------------------------------------------

async function executeDFS() {

    const origin = document.getElementById("origin").value.trim();
    const resultBox = document.getElementById("algorithm-result");

    if (!origin) {
        resultBox.textContent = "Informe a parada de origem.";
        return;
    }

    resultBox.textContent = "Executando DFS...";

    try {
        const response = await fetch("/api/algorithms/dfs", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ origin })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Erro ao executar DFS.");
        }

        clearPath();

        resultBox.replaceChildren();

        const title = document.createElement("strong");
        title.textContent = "DFS concluída!";

        const visited = document.createElement("div");
        visited.textContent =
            `Paradas alcançáveis: ${data.visited_count.toLocaleString("pt-BR")}`;

        const description = document.createElement("div");
        description.textContent =
            "A busca percorreu as conexões direcionadas a partir da origem.";

        resultBox.append(title, visited, description);

    } catch (error) {
        resultBox.textContent = error.message;
    }
}


// --------------------------------------------------
// EVENTOS
// --------------------------------------------------

document.getElementById("search-button")
    .addEventListener("click", searchStops);

document.getElementById("search-input")
    .addEventListener("keydown", event => {
        if (event.key === "Enter") searchStops();
    });

document.getElementById("bfs-button")
    .addEventListener("click", executeBFS);

document.getElementById("dfs-button")
    .addEventListener("click", executeDFS);

map.on("moveend", loadMapStops);


// --------------------------------------------------
// INICIALIZAÇÃO
// --------------------------------------------------

loadStats();
loadMapStops();



// --------------------------------------------------
// GRAFO INTERATIVO COM CYTOSCAPE.JS
// --------------------------------------------------

let cy = null;

function initializeGraph() {

    cy = cytoscape({
        container: document.getElementById("cy"),

        elements: [],

        style: [
            {
                selector: "node",
                style: {
                    "background-color": "#2878ed",
                    "label": "data(label)",
                    "color": "#26344b",
                    "font-size": "9px",
                    "text-wrap": "wrap",
                    "text-max-width": "120px",
                    "text-valign": "bottom",
                    "text-margin-y": 7,
                    "width": 26,
                    "height": 26,
                    "border-width": 2,
                    "border-color": "#ffffff"
                }
            },
            {
                selector: "node[isOrigin]",
                style: {
                    "background-color": "#e94b64",
                    "width": 34,
                    "height": 34,
                    "border-width": 3,
                    "border-color": "#ffd5dc",
                    "font-weight": "bold"
                }
            },
            {
                selector: "edge",
                style: {
                    "width": 1.5,
                    "line-color": "#8795a9",
                    "target-arrow-color": "#8795a9",
                    "target-arrow-shape": "triangle",
                    "curve-style": "bezier",
                    "arrow-scale": 0.9
                }
            },
            {
                selector: "edge:selected",
                style: {
                    "line-color": "#e94b64",
                    "target-arrow-color": "#e94b64",
                    "width": 3
                }
            }
        ],

        layout: {
            name: "grid"
        },

        minZoom: 0.2,
        maxZoom: 3,
        wheelSensitivity: 0.2
    });

    cy.on("tap", "node", event => {

        const node = event.target;
        const stopId = node.id();

        document.getElementById("origin").value = stopId;
        document.getElementById("graph-stop-input").value = stopId;

        const data = node.data();

        if (data.latitude !== null && data.longitude !== null) {
            map.setView([data.latitude, data.longitude], 16);
        }
    });
}


async function loadInteractiveGraph() {

    const stopId = document
        .getElementById("graph-stop-input")
        .value.trim();

    const depth = document
        .getElementById("graph-depth")
        .value;

    const info = document.getElementById("graph-info");

    if (!stopId) {
        info.textContent = "Informe o código de uma parada.";
        return;
    }

    info.textContent = "Construindo visualização do grafo...";

    try {

        const params = new URLSearchParams({
            stop_id: stopId,
            depth: depth,
            limit: 300
        });

        const response = await fetch(
            `/api/graph/neighborhood?${params}`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Erro ao carregar grafo.");
        }

        const elements = data.elements.map(element => {

        if (element.data.source === undefined) {

         const nodeData = { ...element.data };

         if (nodeData.id === stopId) {
             nodeData.isOrigin = true;
         }

        return { data: nodeData };
    }

    return element;
});

        cy.elements().remove();
        cy.add(elements);

        cy.layout({
            name: "cose",
            animate: true,
            animationDuration: 500,
            nodeRepulsion: 7000,
            idealEdgeLength: 85,
            gravity: 0.25,
            fit: true,
            padding: 35
        }).run();

        info.textContent =
            `${data.node_count} paradas e ${data.edge_count} conexões ` +
            `visualizadas a partir da parada ${data.origin}.`;

    } catch (error) {

        info.textContent = error.message;
        console.error(error);
    }
}


// Inicialização do grafo
initializeGraph();

document
    .getElementById("load-graph-button")
    .addEventListener("click", loadInteractiveGraph);

document
    .getElementById("graph-stop-input")
    .addEventListener("keydown", event => {
        if (event.key === "Enter") {
            loadInteractiveGraph();
        }
    });
