
const instance = document.body.dataset.instance;

function apiFetch(path, options) {
    const url = new URL(path, window.location.origin);
    url.searchParams.set("instance", instance);
    return fetch(url, options);
}

const map = window.L ? L.map("map").setView([-23.5505, -46.6333], 11) : null;
let stopLayer = null;

if (map) {
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 19
    }).addTo(map);
    stopLayer = L.layerGroup().addTo(map);
} else {
    document.getElementById("map").textContent = "Mapa indisponível. As buscas locais continuam disponíveis.";
}

let pathLayer = null;
let searchMarker = null;
let mapRequest = null;
let algorithmRequest = null;
let reachability = null;
let discoveryTreeView = null;

async function requestAlgorithm(algorithm, origin, destination) {
    algorithmRequest?.abort();
    clearMapResult();
    const request = new AbortController();
    algorithmRequest = request;

    try {
        const response = await apiFetch(`/api/algorithms/${algorithm}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ origin, destination }),
            signal: request.signal
        });
        const data = await response.json();
        if (!request.signal.aborted) return { response, data };
    } catch (error) {
        if (!request.signal.aborted) throw error;
    } finally {
        if (algorithmRequest === request) algorithmRequest = null;
    }
    return null;
}


function appendResultSummary(container, data) {
    const title = document.createElement("h4");
    title.className = "algorithm-result-title";
    const status = data.found === null ? "Busca concluída" :
        data.found ? "Caminho encontrado" : "Destino inalcançável";
    title.textContent = `${data.algorithm} · ${status}`;

    const metrics = [];
    if (data.distance != null) {
        const unit = data.distance === 1 ? "aresta" : "arestas";
        metrics.push(`${data.distance.toLocaleString("pt-BR")} ${unit} no caminho`);
    }
    metrics.push(
        `${data.processed_count.toLocaleString("pt-BR")} vértices visitados`,
        `${data.discovered_count.toLocaleString("pt-BR")} vértices descobertos`,
        `${data.edges_examined.toLocaleString("pt-BR")} arestas examinadas`
    );
    const time = data.execution_time_ms.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
    metrics.push(`${time} ms de execução`);
    if (data.travel_time_minutes != null) {
        metrics.push(`${data.travel_time_minutes.toLocaleString("pt-BR")} min de viagem estimada`);
    }

    const summary = document.createElement("p");
    summary.textContent = metrics.join(" · ");
    container.append(title, summary);
}


function appendResultDetails(container, label) {
    const details = document.createElement("details");
    details.className = "result-details";
    const summary = document.createElement("summary");
    summary.textContent = label;
    details.append(summary);
    container.append(details);
    return details;
}


function appendVisitOrder(container, data) {
    const section = document.createElement("section");
    section.className = "visit-order";
    appendOrder(
        section,
        data.algorithm === "DFS" ? "Ordem de descoberta" : "Ordem de visita",
        data.visited_order,
        data.visited_order_total,
        data.found === null
    );
    if (data.finish_order) {
        appendOrder(
            section, "Ordem de finalização (retornos)",
            data.finish_order, data.finish_order_total
        );
    }
    container.appendChild(section);
}

function appendOrder(section, label, order, total, open = false) {
    const details = appendResultDetails(section, `${label} · ${total.toLocaleString("pt-BR")}`);
    details.open = open;

    if (order.length === 0) {
        const empty = document.createElement("small");
        empty.textContent = "A busca terminou antes do primeiro retorno.";
        details.append(empty);
    } else {
        const list = document.createElement("ol");
        order.forEach(stopId => {
            const item = document.createElement("li");
            item.textContent = stopId;
            list.appendChild(item);
        });
        details.append(list);
    }

    if (order.length < total) {
        const warning = document.createElement("small");
        warning.textContent = `Exibindo os primeiros ${order.length} registros.`;
        details.append(warning);
    }
}


function appendPath(container, data) {
    if (!data.path || data.path.length === 0) return;

    const details = appendResultDetails(container, "Ver caminho completo");
    const path = document.createElement("div");
    path.className = "algorithm-path";
    path.tabIndex = 0;
    path.setAttribute("role", "region");
    path.setAttribute("aria-label", "Sequência de paradas");
    path.textContent = data.path.join(" → ");
    details.append(path);
}


function appendItinerary(container, itinerary) {
    if (!itinerary || itinerary.legs.length === 0) return;

    const transfers = itinerary.transfer_count.toLocaleString("pt-BR");
    const unit = itinerary.transfer_count === 1 ? "baldeação" : "baldeações";
    const section = appendResultDetails(container, `Itinerário · ${transfers} ${unit}`);
    section.classList.add("itinerary");

    itinerary.legs.forEach((leg, index) => {
        const item = document.createElement("div");
        item.className = "itinerary-leg";

        const badge = document.createElement("span");
        badge.className = `route-color route-color-${index % 5}`;

        const description = document.createElement("div");
        const line = leg.route_short_name || "Linha não identificada";
        const hasTripBreak = leg.geometry_segments?.some(segment =>
            segment.quality?.issues.some(issue => issue.code === "trip-discontinuity"));
        const headsign = leg.headsign && !hasTripBreak ? ` · sentido ${leg.headsign}` : "";
        description.textContent =
            `${line}${headsign} — ${leg.stops.length} paradas`;

        if (hasTripBreak) {
            description.append(document.createElement("br"),
                "Mudança de viagem nesta linha · confira o diagnóstico.");
        }
        item.append(badge, description);
        section.appendChild(item);
    });

    const source = document.createElement("small");
    if (itinerary.uses_road_matching) {
        source.textContent =
            "Trechos ajustados à malha viária do OpenStreetMap, quando disponíveis.";
    } else if (itinerary.uses_gtfs_shapes) {
        source.textContent = "Traçado baseado na geometria do GTFS.";
    } else {
        source.textContent =
            "Geometria GTFS indisponível; exibindo ligação simplificada.";
    }
    if (itinerary.road_matching_status === "fallback-gtfs") {
        source.textContent += " O ajuste viário ficou indisponível para esta rota.";
    }
    if (itinerary.has_approximate_geometry || itinerary.has_sparse_geometry) {
        source.textContent += " Trechos tracejados indicam traçado incerto ou ligação aproximada.";
    }
    section.appendChild(source);
}


// --------------------------------------------------
// CARREGAR ESTATÍSTICAS
// --------------------------------------------------

async function loadStats() {
    try {
        const [statsResponse, connectivityResponse] = await Promise.all([
            apiFetch("/api/stats"),
            apiFetch("/api/connectivity")
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
    if (!map?.hasLayer(stopLayer)) return;

    mapRequest?.abort();
    const request = new AbortController();
    mapRequest = request;
    const bounds = map.getBounds();

    const params = new URLSearchParams({
        south: bounds.getSouth(),
        north: bounds.getNorth(),
        west: bounds.getWest(),
        east: bounds.getEast(),
        limit: 3000
    });

    try {
        const response = await apiFetch(
            `/api/stops/map?${params}`,
            { signal: request.signal }
        );

        if (!response.ok) {
            throw new Error("Erro ao carregar paradas.");
        }

        const data = await response.json();
        if (request.signal.aborted) return;

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
        const response = await apiFetch(
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
                if (!map) return;
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
    const input = document.getElementById(field);
    input.value = `${stop.name || "Parada sem nome"} — ${stop.stop_id}`;
    input.dataset.stopId = stop.stop_id;
    document.getElementById(`${field}-name`).textContent =
        `Código selecionado: ${stop.stop_id}`;
    hideStopSuggestions(field);
}


function hideStopSuggestions(field) {
    const input = document.getElementById(field);
    const suggestions = document.getElementById(`${field}-suggestions`);
    suggestions.replaceChildren();
    input.setAttribute("aria-expanded", "false");
}


function readStopId(field) {
    const input = document.getElementById(field);
    if (input.dataset.stopId) return input.dataset.stopId;
    const value = input.value.trim();
    return /^\d+$/.test(value) ? value : "";
}


function hasUnselectedStopText(field) {
    const input = document.getElementById(field);
    return Boolean(input.value.trim()) && !readStopId(field);
}


function setupStopAutocomplete(field) {
    const input = document.getElementById(field);
    const suggestions = document.getElementById(`${field}-suggestions`);
    let timer = null;
    let controller = null;

    async function search(query) {
        if (controller) controller.abort();
        controller = new AbortController();
        try {
            const response = await apiFetch(
                `/api/stops?q=${encodeURIComponent(query)}&limit=8`,
                { signal: controller.signal }
            );
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Falha ao buscar paradas.");
            if (input.value.trim() !== query || document.activeElement !== input) return;

            suggestions.replaceChildren();
            data.stops.forEach(stop => {
                const option = document.createElement("button");
                option.type = "button";
                option.className = "stop-suggestion";
                option.setAttribute("role", "option");
                const name = document.createElement("strong");
                name.textContent = stop.name || "Parada sem nome";
                const code = document.createElement("small");
                code.textContent = `Código ${stop.stop_id}`;
                option.append(name, code);
                option.addEventListener("mousedown", event => event.preventDefault());
                option.addEventListener("click", () => selectStop(field, stop));
                suggestions.appendChild(option);
            });

            if (!data.stops.length) {
                const empty = document.createElement("div");
                empty.className = "stop-suggestion-empty";
                empty.textContent = "Nenhuma parada encontrada.";
                suggestions.appendChild(empty);
            }
            input.setAttribute("aria-expanded", "true");
        } catch (error) {
            if (error.name !== "AbortError") {
                suggestions.replaceChildren();
                input.setAttribute("aria-expanded", "false");
            }
        }
    }

    input.addEventListener("input", () => {
        input.dataset.stopId = "";
        document.getElementById(`${field}-name`).textContent = "";
        if (timer) clearTimeout(timer);
        controller?.abort();
        const query = input.value.trim();
        if (query.length < 2) {
            hideStopSuggestions(field);
            return;
        }
        timer = setTimeout(() => search(query), 220);
    });

    input.addEventListener("keydown", event => {
        if (event.key === "Escape") hideStopSuggestions(field);
        if (event.key === "Enter" && !input.dataset.stopId) {
            const first = suggestions.querySelector("button[role='option']");
            if (first) {
                event.preventDefault();
                first.click();
            }
        }
    });

    input.addEventListener("blur", () => {
        setTimeout(() => {
            if (!suggestions.contains(document.activeElement)) {
                hideStopSuggestions(field);
            }
        }, 120);
    });
}


// --------------------------------------------------
// EXECUTAR BFS
// --------------------------------------------------

async function executeBFS() {

    const origin = readStopId("origin");
    const destination = readStopId("destination");
    const resultBox = document.getElementById("algorithm-result");

    if (!origin || !destination) {
        resultBox.textContent = hasUnselectedStopText("origin")
            || hasUnselectedStopText("destination")
            ? "Escolha origem e destino nas sugestões de paradas."
            : "Informe a origem e o destino.";
        return;
    }

    resultBox.textContent = "Executando BFS...";

    try {
        const result = await requestAlgorithm("bfs", origin, destination);
        if (!result) return;
        const { response, data } = result;

        if (!response.ok) {
            throw new Error(data.error || "Erro ao executar BFS.");
        }

        resultBox.replaceChildren();
        appendResultSummary(resultBox, data);
        appendPath(resultBox, data);
        appendItinerary(resultBox, data.itinerary);
        appendVisitOrder(resultBox, data);

        if (data.found) drawItinerary(data.itinerary, data.path_stops);

    } catch (error) {
        resultBox.textContent = error.message;
    }
}


// --------------------------------------------------
// DESENHAR CAMINHO DO BFS
// --------------------------------------------------

const geometryDebug = document.getElementById("geometry-debug");
const geometrySelect = document.getElementById("geometry-segment");
const geometryFields = document.getElementById("geometry-debug-data");
let geometryLayers = null;
let geometryEntries = [];

function geometryIsUncertain(segment) {
    return segment.source === "approximate" ||
        (segment.source === "gtfs" && segment.quality?.issues.some(issue =>
            issue.code === "sparse-geometry" || issue.code === "long-detour"));
}

function geometryLabel(segment) {
    if (segment.source === "approximate") return "sem trajeto de rua confirmado";
    if (segment.source === "osrm") return "ajuste OSRM aceito pelas verificações";
    if (geometryIsUncertain(segment)) return "GTFS com traçado incerto";
    return "traçado GTFS";
}

function renderGeometryDebug() {
    geometryLayers?.clearLayers();
    document.getElementById("geometry-debug-instruction").hidden = geometryEntries.length > 0;
    const entry = geometryEntries[geometrySelect.value];
    if (!geometryDebug.open || !entry || !geometryLayers) {
        geometryFields.textContent = "";
        return;
    }
    const {segment, line, stops} = entry;
    const ref = segment.reference ?? {};
    const gtfs = segment.quality ?? {};
    const osrm = segment.osrm ?? {};
    const describeStop = id => {
        const stop = stops.get(id);
        return stop?.name ? stop.name + " (" + id + ")" : id;
    };
    geometryFields.textContent = [
        describeStop(segment.from_stop) + " → " + describeStop(segment.to_stop),
        "Linha " + line + " · viagem " + (ref.trip_id ?? "—") + " · shape " + (ref.shape_id ?? "—"),
        "Sentido GTFS " + (ref.direction_id ?? "—") + " · ocorrências " +
            (ref.from_stop_sequence ?? "—") + " → " + (ref.to_stop_sequence ?? "—"),
        "Fonte final: " + geometryLabel(segment) + " · associação " + (ref.location_method ?? "—"),
        "Intervalo no shape: " + (ref.from_sequence?.toFixed(2) ?? "—") + " → " +
            (ref.to_sequence?.toFixed(2) ?? "—"),
        "GTFS " + (gtfs.distance_m ?? "—") + " m · OSRM " + (osrm.distance_m?.toFixed(1) ?? "—") +
            " m · maior intervalo " + (gtfs.max_gap_m ?? "—") + " m",
        "Erro nas paradas (m): " + (ref.endpoint_error_m?.join(" / ") || "—"),
        "Confiança OSRM: " + (osrm.confidence?.toFixed(3) ?? "—") + " · desvio dos pontos: " +
            (osrm.max_anchor_offset_m ?? "—") + " m",
        "Indicadores: " + (gtfs.issues?.map(issue => Object.entries(issue)
            .map(([key, value]) => key === "code" ? value : key + "=" + value)
            .join(" ")).join(" · ") || "nenhum sinalizado")
    ].join("\n");

    const uncertainDash = geometryIsUncertain(segment) ? "7 7" : null;
    for (const [id, points, color, width, dash] of [
        ["gtfs", segment.gtfs_geometry, "#7c3aed", 10, uncertainDash],
        ["osrm", osrm.geometry, "#00a36c", 7, "9 6"],
        ["final", segment.geometry, "#18243b", 3, uncertainDash || "3 4"]
    ]) {
        if (points?.length >= 2 && document.getElementById("geometry-show-" + id).checked) {
            L.polyline(points, {color, weight: width, dashArray: dash,
                smoothFactor: 0, interactive: false}).addTo(geometryLayers);
        }
    }
}

function focusGeometrySegment() {
    renderGeometryDebug();
    const points = geometryEntries[geometrySelect.value]?.segment.geometry;
    if (points?.length >= 2 && map) {
        map.fitBounds(L.latLngBounds(points), {padding: [40, 40], maxZoom: 18});
    }
}

geometryDebug.addEventListener("toggle", renderGeometryDebug);
geometrySelect.addEventListener("change", focusGeometrySegment);
geometryDebug.querySelectorAll("input[type=checkbox]").forEach(input => {
    input.addEventListener("change", renderGeometryDebug);
});

function clearMapResult() {
    discoveryTreeView?.destroy();
    discoveryTreeView = null;
    document.getElementById("dfs-tree-section").hidden = true;
    document.getElementById("dfs-tree-info").textContent = "";

    if (reachability) {
        reachability.canvas.remove();
        reachability.originMarker?.remove();
        reachability = null;
    }
    document.getElementById("reachability-legend").hidden = true;

    mapRequest?.abort();
    stopLayer?.clearLayers().remove();
    document.getElementById("map-footer").hidden = true;
    searchMarker?.remove();
    searchMarker = null;

    geometryDebug.hidden = true;
    geometryEntries = [];
    document.getElementById("geometry-debug-instruction").hidden = false;
    geometrySelect.replaceChildren();
    geometrySelect.disabled = true;
    geometryFields.textContent = "";
    geometryLayers?.remove();
    geometryLayers = null;
    pathLayer?.remove();
    pathLayer = null;
}


function renderReachability() {
    const { canvas, data } = reachability;
    const size = map.getSize();
    const scale = window.devicePixelRatio || 1;
    canvas.width = Math.round(size.x * scale);
    canvas.height = Math.round(size.y * scale);
    canvas.style.width = `${size.x}px`;
    canvas.style.height = `${size.y}px`;
    L.DomUtil.setPosition(canvas, map.containerPointToLayerPoint([0, 0]));

    const context = canvas.getContext("2d");
    context.scale(scale, scale);
    const bounds = map.getBounds().pad(0.01);
    const south = bounds.getSouth();
    const north = bounds.getNorth();
    const west = bounds.getWest();
    const east = bounds.getEast();
    const zoom = map.getZoom();
    const topLeft = map.getPixelBounds().min;

    // Draw one batch per color. The layer has no per-stop DOM nodes or events.
    for (const [points, color, radius] of [
        [data.unreachable, "#687384", zoom < 12 ? 1.5 : 2],
        [data.reachable, "#2878ed", zoom < 12 ? 1.75 : 2.5]
    ]) {
        context.fillStyle = color;
        context.beginPath();
        for (const [lat, lng] of points) {
            if (lat < south || lat > north || lng < west || lng > east) continue;
            const projected = map.project([lat, lng], zoom);
            const x = Math.round(projected.x) - topLeft.x;
            const y = Math.round(projected.y) - topLeft.y;
            context.moveTo(x + radius, y);
            context.arc(x, y, radius, 0, 2 * Math.PI);
        }
        context.fill();
    }
}


function drawReachability(data) {
    if (!map) return;

    const canvas = L.DomUtil.create(
        "canvas", "reachability-layer leaflet-zoom-hide", map.getPanes().overlayPane
    );
    canvas.setAttribute("aria-hidden", "true");
    const originMarker = data.origin ? L.marker(data.origin, {
        icon: L.divIcon({ className: "reachability-origin-marker", iconSize: [16, 16] }),
        title: "Parada de origem"
    }).addTo(map).bindTooltip("Origem", { direction: "top", offset: [0, -9], permanent: true }) : null;
    reachability = { canvas, originMarker, data };

    document.getElementById("reachability-missing-origin").hidden = Boolean(data.origin);
    document.getElementById("reachability-legend").hidden = false;
    if (data.reachable.length) {
        map.fitBounds(L.latLngBounds(data.reachable), {
            padding: [35, 35], maxZoom: 16, animate: false
        });
    }
    renderReachability();
}


function addDirectionArrows(geometry, color, group) {
    if (!geometry || geometry.length < 2) return;

    const index = Math.floor((geometry.length - 1) / 2);
    let nextIndex = index + 1;
    while (nextIndex < geometry.length
        && geometry[nextIndex][0] === geometry[index][0]
        && geometry[nextIndex][1] === geometry[index][1]) {
        nextIndex += 1;
    }
    if (nextIndex >= geometry.length) return;

    const current = geometry[index];
    const next = geometry[nextIndex];
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

function drawItinerary(itinerary, stops) {
    if (!map || !stops || stops.length === 0) return;

    geometryDebug.hidden = false;
    const colors = ["#e94b64", "#2878ed", "#f59e0b", "#16a085", "#8b5cf6"];
    pathLayer = L.featureGroup().addTo(map);
    let directionArrow = null;
    const stopById = new Map(stops.map(stop => [stop.stop_id, stop]));

    if (itinerary && itinerary.legs.length > 0) {
        itinerary.legs.forEach((leg, index) => {
            const color = colors[index % colors.length];
            const segments = leg.geometry_segments ?? [{geometry: leg.geometry, source: "gtfs"}];
            for (const segment of segments) {
                const geometry = segment.geometry;
                const index = geometryEntries.length;
                const lineName = leg.route_short_name || "Linha não identificada";
                geometryEntries.push({segment, line: lineName, stops: stopById});
                geometrySelect.add(new Option(segment.from_stop + " → " + segment.to_stop +
                    " · " + lineName + (geometryIsUncertain(segment) ? " · incerto" : ""), index));
                if (!geometry || geometry.length < 2) continue;

                if (geometry[0][0] === geometry[geometry.length - 1][0] &&
                    geometry[0][1] === geometry[geometry.length - 1][1] &&
                    segment.source === "approximate") continue;
                const approximate = geometryIsUncertain(segment);
                const line = L.polyline(geometry, {
                    color,
                    weight: 5,
                    opacity: approximate ? 0.65 : 0.9,
                    dashArray: approximate ? "7 7" : null,
                    smoothFactor: 0
                });

                const label = leg.route_short_name || "Linha não identificada";
                const popup = document.createElement("span");
                popup.textContent = "Linha " + label + " · " + geometryLabel(segment);
                const inspect = document.createElement("button");
                inspect.type = "button";
                inspect.textContent = "Diagnosticar trecho";
                inspect.addEventListener("click", () => {
                    geometryDebug.open = true;
                    geometrySelect.value = index;
                    renderGeometryDebug();
                    geometryDebug.scrollIntoView({block: "nearest"});
                });
                popup.append(document.createElement("br"), inspect);
                line.bindPopup(popup);
                pathLayer.addLayer(line);
                if (!approximate && (!directionArrow || geometry.length > directionArrow.geometry.length)) {
                    directionArrow = { geometry, color };
                }
            }
        });
    }

    geometrySelect.disabled = !geometryEntries.length;
    geometryLayers = L.layerGroup().addTo(map);
    for (const {segment} of geometryEntries) {
        if (!segment.quality?.issues.some(issue => issue.code === "trip-discontinuity")) continue;
        const stop = stopById.get(segment.from_stop);
        if (stop?.latitude == null || stop.longitude == null) continue;
        L.circleMarker([stop.latitude, stop.longitude], {
            radius: 5, color: "#ffffff", fillColor: "#7c3aed", fillOpacity: 1
        }).bindTooltip("Mudança de viagem nesta parada").addTo(pathLayer);
    }
    renderGeometryDebug();

    if (directionArrow) {
        addDirectionArrows(
            directionArrow.geometry,
            directionArrow.color,
            pathLayer
        );
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
        if (stop.latitude == null || stop.longitude == null) return;
        pathLayer.addLayer(L.marker(
            [stop.latitude, stop.longitude],
            { icon }
        ));
    });

    const bounds = pathLayer.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [45, 45], animate: false });
}


// --------------------------------------------------
// EXECUTAR DFS
// --------------------------------------------------

async function executeDFS() {

    const origin = readStopId("origin");
    const destination = readStopId("destination");
    const resultBox = document.getElementById("algorithm-result");

    if (!origin) {
        resultBox.textContent = hasUnselectedStopText("origin")
            ? "Escolha a origem nas sugestões de paradas."
            : "Informe a parada de origem.";
        return;
    }
    if (hasUnselectedStopText("destination")) {
        resultBox.textContent = "Escolha o destino nas sugestões de paradas.";
        return;
    }

    resultBox.textContent = "Executando DFS...";

    try {
        const result = await requestAlgorithm("dfs", origin, destination || null);
        if (!result) return;
        const { response, data } = result;

        if (!response.ok) {
            throw new Error(data.error || "Erro ao executar DFS.");
        }

        resultBox.replaceChildren();
        appendResultSummary(resultBox, data);
        if (!data.destination) {
            const description = document.createElement("p");
            const reachable = data.discovered_count;
            const total = data.network_size;
            description.textContent =
                `${reachable.toLocaleString("pt-BR")} de ${total.toLocaleString("pt-BR")} paradas alcançáveis (inclui a origem). ` +
                `${(total - reachable).toLocaleString("pt-BR")} ficam fora da cobertura direcionada desta origem.`;
            resultBox.append(description);
        }

        appendPath(resultBox, data);
        appendItinerary(resultBox, data.itinerary);
        appendVisitOrder(resultBox, data);

        if (data.reachability) {
            const views = document.createElement("div");
            views.className = "dfs-view-actions";
            if (map) {
                drawReachability(data.reachability);
                const viewMap = document.createElement("a");
                viewMap.href = "#map-section";
                viewMap.textContent = "Ver cobertura no mapa";
                views.append(viewMap);
            }
            if (window.cytoscape && data.discovery_tree) {
                const viewTree = document.createElement("button");
                viewTree.type = "button";
                viewTree.className = "secondary-button";
                viewTree.textContent = "Ver árvore de descoberta";
                viewTree.addEventListener("click", () => {
                    showDiscoveryTree(data.discovery_tree, data.origin);
                });
                views.append(viewTree);
            }
            if (views.childElementCount) resultBox.append(views);
        } else if (data.path) {
            drawItinerary(data.itinerary, data.path_stops);
        }

    } catch (error) {
        resultBox.textContent = error.message;
    }
}


async function executeWeightedSearch() {
    const origin = readStopId("origin");
    const destination = readStopId("destination");
    const resultBox = document.getElementById("algorithm-result");

    if (!origin || !destination) {
        resultBox.textContent = hasUnselectedStopText("origin")
            || hasUnselectedStopText("destination")
            ? "Escolha origem e destino nas sugestões de paradas."
            : "Informe a origem e o destino.";
        return;
    }

    resultBox.textContent = "Calculando a rota de menor tempo...";
    try {
        const result = await requestAlgorithm("dijkstra", origin, destination);
        if (!result) return;
        const { response, data } = result;
        if (!response.ok) throw new Error(data.error || "Erro no Dijkstra.");
        resultBox.replaceChildren();
        appendResultSummary(resultBox, data);
        appendPath(resultBox, data);
        appendItinerary(resultBox, data.itinerary);
        appendVisitOrder(resultBox, data);
        if (!data.found) return;

        const weights = appendResultDetails(resultBox, "Detalhes da estimativa de viagem");
        const source = document.createElement("p");
        source.textContent = `Pesos: ${data.weight_source}. Soma dos tempos entre paradas; não inclui espera de baldeação nem trânsito.`;
        weights.append(source);
        if (data.estimated_edges_used > 0) {
            const estimate = document.createElement("small");
            estimate.className = "weight-estimate-note";
            estimate.textContent = `${data.estimated_edges_used} trecho(s) da rota não tinham horário GTFS e receberam estimativa por distância reta a 18 km/h.`;
            weights.append(estimate);
        }
        drawItinerary(data.itinerary, data.path_stops);
    } catch (error) {
        resultBox.textContent = error.message;
    }
}


// --------------------------------------------------
// COMPARAR BFS E DFS
// --------------------------------------------------

async function compareAlgorithms() {

    const origin = readStopId("origin");
    const destination = readStopId("destination");
    const resultBox = document.getElementById("algorithm-result");

    if (!origin || !destination) {
        resultBox.textContent = hasUnselectedStopText("origin")
            || hasUnselectedStopText("destination")
            ? "Escolha origem e destino nas sugestões de paradas."
            : "Informe a origem e o destino.";
        return;
    }

    resultBox.textContent = "Comparando BFS e DFS...";

    try {
        const result = await requestAlgorithm("compare", origin, destination);
        if (!result) return;
        const { response, data } = result;

        if (!response.ok) {
            throw new Error(data.error || "Erro ao comparar algoritmos.");
        }

        resultBox.replaceChildren();

        const comparison = document.createElement("div");
        comparison.className = "algorithm-comparison";

        [data.bfs, data.dfs].forEach(result => {
            const card = document.createElement("article");
            card.className = "algorithm-comparison-card";

            appendResultSummary(card, result);
            appendPath(card, result);
            appendItinerary(card, result.itinerary);
            appendVisitOrder(card, result);
            const method = appendResultDetails(card, "Como a busca funciona");
            const explanation = document.createElement("p");
            explanation.textContent =
                data.explanation[result.algorithm.toLowerCase()];
            method.append(explanation);
            if (result.found && map) {
                const showRoute = document.createElement("button");
                showRoute.type = "button";
                showRoute.textContent = `Ver caminho ${result.algorithm} no mapa`;
                showRoute.addEventListener("click", () => {
                    clearMapResult();
                    drawItinerary(result.itinerary, result.path_stops);
                });
                card.append(showRoute);
            }
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

function initializeSectionNavigation() {
    const items = Array.from(
        document.querySelectorAll("[data-nav-target]")
    );

    const sections = items
        .map(item => document.getElementById(item.dataset.navTarget))
        .filter(Boolean);

    function setActive(targetId) {
        items.forEach(item => {
            const isActive = item.dataset.navTarget === targetId;
            item.classList.toggle("active", isActive);

            if (isActive) {
                item.setAttribute("aria-current", "page");
            } else {
                item.removeAttribute("aria-current");
            }
        });
    }

    items.forEach(item => {
        item.addEventListener("click", event => {
            const target = document.getElementById(item.dataset.navTarget);
            if (!target) return;

            event.preventDefault();
            setActive(item.dataset.navTarget);
            target.scrollIntoView({ behavior: "smooth", block: "start" });
            history.replaceState(null, "", item.getAttribute("href"));
        });
    });

    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver(entries => {
            const visible = entries
                .filter(entry => entry.isIntersecting)
                .sort((first, second) =>
                    second.intersectionRatio - first.intersectionRatio
                );

            if (visible.length > 0) {
                setActive(visible[0].target.id);
            }
        }, {
            rootMargin: "-18% 0px -62% 0px",
            threshold: [0.1, 0.25, 0.5]
        });

        sections.forEach(section => observer.observe(section));
    }
}

initializeSectionNavigation();
setupStopAutocomplete("origin");
setupStopAutocomplete("destination");

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

document.getElementById("weighted-button")
    .addEventListener("click", executeWeightedSearch);

document.getElementById("compare-button")
    .addEventListener("click", compareAlgorithms);

document.getElementById("reverse-stops-button")
    .addEventListener("click", () => {
        const origin = document.getElementById("origin");
        const destination = document.getElementById("destination");
        const originName = document.getElementById("origin-name");
        const destinationName = document.getElementById("destination-name");
        const originId = readStopId("origin");
        const destinationId = readStopId("destination");

        [origin.value, destination.value] = [destination.value, origin.value];
        origin.dataset.stopId = destinationId;
        destination.dataset.stopId = originId;
        [originName.textContent, destinationName.textContent] =
            [destinationName.textContent, originName.textContent];
        hideStopSuggestions("origin");
        hideStopSuggestions("destination");
    });

document.getElementById("clear-stops-button")
    .addEventListener("click", () => {
        algorithmRequest?.abort();
        document.getElementById("algorithm-result").textContent =
            "Selecione as paradas para consultar a ordem de visita e comparar o comportamento dos algoritmos.";
        ["origin", "destination"].forEach(field => {
            const input = document.getElementById(field);
            input.value = "";
            input.dataset.stopId = "";
            document.getElementById(`${field}-name`).textContent = "";
            hideStopSuggestions(field);
        });
        clearMapResult();
        if (map) {
            stopLayer.addTo(map);
            document.getElementById("map-footer").hidden = false;
            geometryDebug.hidden = false;
            loadMapStops();
        }
    });

map?.on("moveend", () => {
    if (reachability) renderReachability();
    else loadMapStops();
});


// --------------------------------------------------
// INICIALIZAÇÃO
// --------------------------------------------------

loadStats();
loadMapStops();



// --------------------------------------------------
// GRAFO INTERATIVO COM CYTOSCAPE.JS
// --------------------------------------------------

let cy = null;

function createGraphView(container) {
    return cytoscape({
        container,

        elements: [],

        style: [
            {
                selector: "node",
                style: {
                    "background-color": "#2878ed",
                    "label": instance === "local" ? "data(id)" : "data(label)",
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
                selector: "node[?isOrigin]",
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
}


function showDiscoveryTree(tree, origin) {
    const section = document.getElementById("dfs-tree-section");
    section.hidden = false;
    if (!discoveryTreeView) {
        discoveryTreeView = createGraphView(document.getElementById("dfs-tree-graph"));
        discoveryTreeView.add(tree.elements);
        discoveryTreeView.layout({
            name: "breadthfirst",
            directed: true,
            roots: discoveryTreeView.getElementById(origin),
            spacingFactor: 1.5,
            padding: 35
        }).run();
    }

    const displayed = tree.edge_count.toLocaleString("pt-BR");
    const total = tree.total_edges.toLocaleString("pt-BR");
    const info = document.getElementById("dfs-tree-info");
    info.textContent = tree.edge_count < tree.total_edges
        ? `Origem ${origin} · ${displayed} de ${total} arestas de descoberta. Recorte de até ${tree.depth_limit} níveis a partir da origem e até ${tree.edge_limit} arestas.`
        : `Origem ${origin} · árvore completa com ${displayed} ${tree.edge_count === 1 ? "aresta de descoberta" : "arestas de descoberta"}.`;
    section.scrollIntoView({ block: "start" });
    document.getElementById("dfs-tree-title").focus({ preventScroll: true });
}


function initializeGraph() {
    if (!window.cytoscape) {
        document.getElementById("graph-info").textContent = "Visualização do grafo indisponível.";
        document.getElementById("load-graph-button").disabled = true;
        return;
    }

    cy = createGraphView(document.getElementById("cy"));

    cy.on("tap", "node", event => {

        const node = event.target;
        const stopId = node.id();

        selectStop("origin", {stop_id: stopId, name: node.data("label")});
        document.getElementById("graph-stop-input").value = stopId;

        const data = node.data();

        if (map && data.latitude !== null && data.longitude !== null) {
            map.setView([data.latitude, data.longitude], 16);
        }
    });
}


async function loadInteractiveGraph() {
    if (!cy) return;

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

        const response = await apiFetch(
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

        const layout = instance === "local" ? {
            name: "breadthfirst",
            directed: true,
            roots: cy.getElementById(stopId),
            spacingFactor: 1.5,
            padding: 35
        } : {
            name: "cose",
            animate: true,
            animationDuration: 500,
            nodeRepulsion: 7000,
            idealEdgeLength: 85,
            gravity: 0.25,
            fit: true,
            padding: 35
        };
        cy.layout(layout).run();

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
