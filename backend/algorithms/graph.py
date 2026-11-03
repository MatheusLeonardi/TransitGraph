
class Graph:

    def __init__(self):
        # Lista de adjacência direcionada
        self.adjacency = {}

        # Informações das paradas
        self.stops = {}

        # Linhas que realizam cada conexão
        self.edge_routes = {}

        # Metadados das linhas GTFS
        self.routes = {}

        # Viagem/shape representativo de cada conexão por linha
        self.edge_shapes = {}

        # Pontos dos shapes são usados na etapa de persistência. O carregamento
        # da aplicação mantém esses pontos apenas no SQLite para economizar RAM.
        self.shape_points = {}

        # Informações da construção (data de serviço, shapes, viagens etc.)
        self.metadata = {}

    def add_route(self, route_id, short_name=None, long_name=None):
        self.routes[route_id] = {
            "route_id": route_id,
            "short_name": short_name,
            "long_name": long_name
        }

    def add_stop(self, stop_id, name=None, latitude=None, longitude=None):

        # Garante que o vértice exista na lista de adjacência
        if stop_id not in self.adjacency:
            self.adjacency[stop_id] = {}

        # Cria os metadados somente na primeira inclusão
        if stop_id not in self.stops:
            self.stops[stop_id] = {
                "stop_id": stop_id,
                "name": name,
                "latitude": latitude,
                "longitude": longitude
            }
        else:
            # Atualiza somente os valores realmente informados.
            # Assim, add_edge() não apaga os metadados existentes.
            if name is not None:
                self.stops[stop_id]["name"] = name

            if latitude is not None:
                self.stops[stop_id]["latitude"] = latitude

            if longitude is not None:
                self.stops[stop_id]["longitude"] = longitude

    def add_edge(self, source, target, route_id=None):

        # Garante que os dois vértices existam
        self.add_stop(source)
        self.add_stop(target)

        # Evita arestas duplicadas
        self.adjacency[source][target] = None

        edge = (source, target)

        if edge not in self.edge_routes:
            self.edge_routes[edge] = set()

        if route_id is not None:
            self.edge_routes[edge].add(route_id)

    def add_edge_shape(
        self,
        source,
        target,
        route_id,
        trip_id,
        shape_id,
        from_sequence,
        to_sequence,
        headsign=None
    ):
        key = (source, target, route_id)

        # Uma referência representativa é suficiente para desenhar a conexão.
        if key not in self.edge_shapes:
            self.edge_shapes[key] = {
                "source": source,
                "target": target,
                "route_id": route_id,
                "trip_id": trip_id,
                "shape_id": shape_id,
                "from_sequence": from_sequence,
                "to_sequence": to_sequence,
                "headsign": headsign
            }

    def get_neighbors(self, stop_id):
        return list(self.adjacency.get(stop_id, {}).keys())

    def get_stop(self, stop_id):
        return self.stops.get(stop_id)

    def vertex_count(self):
        return len(self.adjacency)

    def edge_count(self):
        return sum(
            len(neighbors)
            for neighbors in self.adjacency.values()
        )

    def has_stop(self, stop_id):
        return stop_id in self.adjacency
