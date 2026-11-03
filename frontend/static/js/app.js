
const map = L.map("map").setView([-23.5505, -46.6333], 11);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19
}).addTo(map);

const stopLayer = L.layerGroup().addTo(map);

let pathLayer = null;
let searchMarker = null;
let mapRequest = null;


function appendVisitOrder(container, data) {

    const section = document.createElement("section");
    section.className = "visit-order";

    const heading = document.createElement("strong");
    heading.textContent = `Ordem de visita — ${data.algorithm}`;

    const summary = document.createElement("small");
    summary.textContent =
        `${data.processed_count.toLocaleString("pt-BR")} processadas · ` +
        `${data.discovered_count.toLocaleString("pt-BR")} descobertas`;

    const list = document.createElement("ol");

    data.visited_order.forEach(stopId => {
        const item = document.createElement("li");
        item.textContent = stopId;
        list.appendChild(item);
    });

    section.append(heading, summary, list);

    if (data.visited_order_truncated) {
        const warning = document.createElement("small");
        warning.textContent =
            `Exibindo as primeiras ${data.visited_order.length} de ` +
            `${data.visited_order_total.toLocaleString("pt-BR")} visitas.`;
        section.appendChild(warning);
    }

    container.appendChild(section);
}


function appendPath(container, data) {
    if (!data.path || data.path.length === 0) return;

    const path = document.createElement("div");
    path.className = "algorithm-path";
    path.textContent =
        `Caminho (${data.distance} arestas): ${data.path.join(" → ")}`;
    container.appendChild(path);
}


function appendItinerary(container, itinerary) {
    if (!itinerary || itinerary.legs.length === 0) return;

    const section = document.createElement("section");
    section.className = "itinerary";

    const heading = document.createElement("strong");
    heading.textContent =
        `Itinerário · ${itinerary.transfer_count} baldeação(ões)`;
    section.appendChild(heading);

    itinerary.legs.forEach((leg, index) => {
        const item = document.createElement("div");
        item.className = "itinerary-leg";

        const badge = document.createElement("span");
        badge.className = `route-color route-color-${index % 5}`;

        const description = document.createElement("div");
        const line = leg.route_short_name || "Linha não identificada";
        const headsign = leg.headsign ? ` · sentido ${leg.headsign}` : "";
        description.textContent =
            `${line}${headsign} — ${leg.stops.length} paradas`;

        item.append(badge, description);
        section.appendChild(item);
    });

    const source = document.createElement("small");
    if (itinerary.uses_road_matching) {
        source.textContent =
            "Shape GTFS refinado sobre a malha viária do OpenStreetMap.";
    } else if (itinerary.uses_gtfs_shapes) {
        source.textContent = "Traçado exibido com a geometria oficial do GTFS.";
    } else {
        source.textContent =
            "Geometria GTFS indisponível; exibindo ligação simplificada.";
    }
    section.appendChild(source);
    container.appendChild(section);
}


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

        if (stats.service_date) {
            const [year, month, day] = stats.service_date.split("-");
            document.getElementById("data-date").textContent =
                `REDE DE ${day}/${month}/${year}`;
        }

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

            const result = document.createElement("div");
            result.className = "search-result";

            const title = document.createElement("strong");
            title.textContent = stop.name || "Parada sem nome";

            const details = document.createElement("small");
            details.textContent = `Código: ${stop.stop_id}`;

            const actions = document.createElement("div");
            actions.className = "search-result-actions";

            const originButton = document.createElement("button");
            originButton.textContent = "Usar como origem";

            const destinationButton = document.createElement("button");
            destinationButton.textContent = "Usar como destino";

            function focusStop() {
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
            }

            originButton.addEventListener("click", () => {
                selectStop("origin", stop);
                focusStop();
            });

            destinationButton.addEventListener("click", () => {
                selectStop("destination", stop);
                focusStop();
            });

            actions.append(originButton, destinationButton);
            result.append(title, details, actions);
            results.appendChild(result);
        });

    } catch (error) {
        results.textContent = error.message;
    }
}


function selectStop(field, stop) {
    document.getElementById(field).value = stop.stop_id;
    document.getElementById(`${field}-name`).textContent =
        stop.name || "Parada sem nome";
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

        resultBox.append(title, distance);
        appendPath(resultBox, data);
        appendItinerary(resultBox, data.itinerary);
        appendVisitOrder(resultBox, data);

        drawItinerary(data.itinerary, data.path_stops);

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


function addDirectionArrows(geometry, color, group) {
    if (!geometry || geometry.length < 2) return;

    const arrowCount = Math.min(4, Math.max(1, Math.floor(geometry.length / 35)));

    for (let arrow = 1; arrow <= arrowCount; arrow += 1) {
        const index = Math.min(
            Math.floor((geometry.length - 1) * arrow / (arrowCount + 1)),
            geometry.length - 2
        );
        const current = geometry[index];
        const next = geometry[index + 1];
        const screenX = next[1] - current[1];
        const screenY = -(next[0] - current[0]);
        const angle = Math.atan2(screenY, screenX) * 180 / Math.PI;

        const icon = L.divIcon({
            className: "route-arrow-icon",
            html: `<span style="color:${color};transform:rotate(${angle}deg)">➤</span>`,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });

        group.addLayer(L.marker(current, {
            icon,
            interactive: false,
            keyboard: false
        }));
    }
}

function drawItinerary(itinerary, stops) {

    clearPath();

    if (!stops || stops.length === 0) return;

    const colors = ["#e94b64", "#2878ed", "#f59e0b", "#16a085", "#8b5cf6"];
    pathLayer = L.featureGroup().addTo(map);

    if (itinerary && itinerary.legs.length > 0) {
        itinerary.legs.forEach((leg, index) => {
            if (!leg.geometry || leg.geometry.length < 2) return;

            const line = L.polyline(leg.geometry, {
                color: colors[index % colors.length],
                weight: 5,
                opacity: 0.9
            });

            const label = leg.route_short_name || "Linha não identificada";
            line.bindPopup(`Linha ${label}`);
            pathLayer.addLayer(line);
            addDirectionArrows(
                leg.geometry,
                colors[index % colors.length],
                pathLayer
            );
        });
    }

    if (pathLayer.getLayers().length === 0) {
        const coordinates = stops.map(stop => [
            stop.latitude,
            stop.longitude
        ]);

        pathLayer.addLayer(L.polyline(coordinates, {
            color: colors[0],
            weight: 5,
            opacity: 0.9
        }));
    }

    const origin = stops[0];
    const destination = stops[stops.length - 1];

    [
        [origin, "A", "route-endpoint-origin"],
        [destination, "B", "route-endpoint-destination"]
    ].forEach(([stop, label, className]) => {
        const icon = L.divIcon({
            className: `route-endpoint ${className}`,
            html: `<span>${label}</span>`,
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        });
        pathLayer.addLayer(L.marker(
            [stop.latitude, stop.longitude],
            { icon }
        ));
    });

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
            body: JSON.stringify({
                origin,
                destination: document
                    .getElementById("destination")
                    .value.trim() || null
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Erro ao executar DFS.");
        }

        clearPath();

        resultBox.replaceChildren();

        const title = document.createElement("strong");
        title.textContent = "DFS concluída!";

        const description = document.createElement("div");
        description.textContent =
            data.destination
                ? "A DFS aprofundou cada ramo até localizar o destino."
                : "A DFS percorreu todas as conexões direcionadas alcançáveis.";

        resultBox.append(title, description);
        appendPath(resultBox, data);
        appendItinerary(resultBox, data.itinerary);
        appendVisitOrder(resultBox, data);

        if (data.path) {
            drawItinerary(data.itinerary, data.path_stops);
        }

    } catch (error) {
        resultBox.textContent = error.message;
    }
}


// --------------------------------------------------
// COMPARAR BFS E DFS
// --------------------------------------------------

async function compareAlgorithms() {

    const origin = document.getElementById("origin").value.trim();
    const destination = document.getElementById("destination").value.trim();
    const resultBox = document.getElementById("algorithm-result");

    if (!origin || !destination) {
        resultBox.textContent = "Informe a origem e o destino.";
        return;
    }

    resultBox.textContent = "Comparando BFS e DFS...";

    try {
        const response = await fetch("/api/algorithms/compare", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ origin, destination })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Erro ao comparar algoritmos.");
        }

        resultBox.replaceChildren();

        const comparison = document.createElement("div");
        comparison.className = "algorithm-comparison";

        [data.bfs, data.dfs].forEach(result => {
            const card = document.createElement("article");
            card.className = "algorithm-comparison-card";

            const title = document.createElement("h4");
            title.textContent = result.algorithm;

            const explanation = document.createElement("p");
            explanation.textContent =
                data.explanation[result.algorithm.toLowerCase()];

            const metrics = document.createElement("div");
            metrics.className = "algorithm-metrics";
            metrics.textContent =
                `${result.processed_count.toLocaleString("pt-BR")} processadas · ` +
                `${result.execution_time_ms.toLocaleString("pt-BR")} ms`;

            card.append(title, explanation, metrics);
            appendPath(card, result);
            appendItinerary(card, result.itinerary);
            appendVisitOrder(card, result);
            comparison.appendChild(card);
        });

        resultBox.appendChild(comparison);
        drawItinerary(data.bfs.itinerary, data.bfs.path_stops);

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

document.getElementById("compare-button")
    .addEventListener("click", compareAlgorithms);

document.getElementById("reverse-stops-button")
    .addEventListener("click", () => {
        const origin = document.getElementById("origin");
        const destination = document.getElementById("destination");
        const originName = document.getElementById("origin-name");
        const destinationName = document.getElementById("destination-name");

        [origin.value, destination.value] = [destination.value, origin.value];
        [originName.textContent, destinationName.textContent] =
            [destinationName.textContent, originName.textContent];
    });

document.getElementById("clear-stops-button")
    .addEventListener("click", () => {
        ["origin", "destination"].forEach(field => {
            document.getElementById(field).value = "";
            document.getElementById(`${field}-name`).textContent = "";
        });
        clearPath();
    });

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
