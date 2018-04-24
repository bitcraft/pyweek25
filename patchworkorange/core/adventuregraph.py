import yaml
import re

from logging import getLogger

logger = getLogger(__name__)

# Vertex IDs must be all uppercase or numbers and at least 1 character long
VALID_VERTEX_ID_RE = re.compile("^[A-Z0-9]+$")


class MissingVertexException(Exception):
    pass


class NoStartVertexException(Exception):
    pass


class InvalidVertexIDException(Exception):
    pass


class InvalidEdgeException(Exception):
    pass


def build_graph_from_yaml_data(yaml_data):
    unlinked_graph = create_unlinked_graph(yaml_data)
    verify_graph_has_start_vertex(unlinked_graph)
    linked_graph = link_graph_edges(unlinked_graph)
    return linked_graph


def load_yaml_data(filepath):
    with open(filepath) as fob:
        return yaml.load(fob)


def create_unlinked_graph(yaml_data):
    graph = Graph()
    for vertex_id, vertex_data in yaml_data.items():
        if vertex_id != "GLOBAL":
            validate_vertex_id(vertex_id)
            vertex = Vertex()
            vertex.vertex_id = vertex_id
            vertex.name = vertex_data["name"]
            vertex.icon = vertex_data.get("icon", "vertex.png")
            vertex.mini_game_name = vertex_data.get("mini-game-name", None)
            vertex.mini_game_kwargs = vertex_data.get("mini-game-kwargs")
            vertex.description = vertex_data["description"].strip()
            coords = vertex_data.get("coordinates")
            vertex.cleared = vertex_data.get("cleared")
            vertex.coordinates = (coords["x"], coords["y"])
            vertex.context.update(vertex_data.get("context", {}))
            vertex.activation = vertex_data.get("activation")

            for pre_req in vertex_data.get("activation-pre-requisites", []):
                vertex.activation_pre_requisites.append(pre_req["key"], pre_req["value"], pre_req["hint"])

            for edge_data in vertex_data.get("edges", list()):
                # temporarily set the to_vertex to the ID, we'll link these up later
                edge = Edge(vertex, edge_data["vertex-id"])
                for pre_req in edge_data.get("pre-requisites", []):
                    edge.traversal_pre_requisites.append(pre_req["name"], pre_req["value"], pre_req["hint"])
                vertex.edges.append(edge)
            graph.vertex_index[vertex_id] = vertex
        else:
            graph.background = vertex_data["background"]
    return graph


def validate_vertex_id(vertex_id):
    if not VALID_VERTEX_ID_RE.match(vertex_id):
        raise InvalidVertexIDException("\"%s\" is an invalid vertex ID. Must be all upper case letters or numbers." %
                                       vertex_id)


def verify_graph_has_start_vertex(graph):
    if "START" not in graph.vertex_index:
        raise NoStartVertexException()


def link_graph_edges(unlinked_graph):
    """Link the edges in the vertices of the graph.

    WARNING: This does an in-place operation and mutates the passed in graph object! It replaces the vertex_id strings
    with references to the actual vertex instances.
    """
    for vertex in unlinked_graph.vertex_index.values():
        for edge in vertex.edges:
            try:
                to_vertex_id = edge.to_vertex
                edge.to_vertex = unlinked_graph.vertex_index[to_vertex_id]
            except KeyError:
                vertex_ids = (vertex.vertex_id, edge.to_vertex)
                raise MissingVertexException("Could not find vertex \"%s\" while linking edges on vertex \"%s\"" %
                                             vertex_ids)
    return unlinked_graph


class Graph:

    def __init__(self):
        self.start_vertex = None
        self.vertex_index = dict()
        self.background = None

    def __getitem__(self, vertex_id):
        if isinstance(vertex_id, str) and vertex_id.upper() == vertex_id and vertex_id in self.vertex_index:
            return self.vertex_index[vertex_id]
        else:
            raise IndexError("Vertex with ID \"%s\" not present in graph" % vertex_id)


class PreRequisite:
    class NotMetException(Exception):
        pass

    def __init__(self, key, value, hint):
        self.key = key
        self.value = value
        self.hint = hint

    def check(self, context):
        return context.get(self.key) == self.value


class PreRequisiteList:

    def __init__(self):
        self.pre_reqs = list()

    def get_failing_pre_requisites(self, context):
        return [pre_req for pre_req in self.pre_reqs if not pre_req.check(context)]

    def append(self, key, value, hint):
        self.pre_reqs.append(PreRequisite(key, value, hint))

    def __iter__(self):
        yield from self.pre_reqs


class Activation:

    def __init__(self, command, keyword_args):
        self.command = command
        self.kwargs = keyword_args


class FailedActivation:

    def __init__(self, command, keyword_args, failed_pre_reqs):
        self.command = command
        self.keyword_args = keyword_args
        self.failed_pre_reqs = failed_pre_reqs

    @staticmethod
    def from_activation(activation, failed_pre_reqs):
        return FailedActivation(activation.command, activation.keyword_args, failed_pre_reqs)


class Vertex:

    def __init__(self):
        self.context = dict()
        self.coordinates = (0, 0)
        self.description = None
        self.edges = list()
        self.icon = None
        self.cleared = None
        self.name = None
        self.mini_game_name = None
        self.mini_game_kwargs = tuple()
        self.activation_pre_requisites = PreRequisiteList()
        self.vertex_id = None
        self.activation = None

    def get_edge_by_to_vertex_id(self, to_vertex_id):
        for edge in self.edges:
            if edge.to_vertex.vertex_id == to_vertex_id:
                return edge
        raise InvalidEdgeException("Vertex \"%s\" is not connected to vertex \"%s\" or this vertex does not exist" %
                                   (self.vertex_id, to_vertex_id))

    @property
    def is_activatable(self):
        return self.activation is not None

    def can_activate(self, context):
        return self.is_activatable and len(self.activation_pre_requisites.get_failing_pre_requisites(context)) == 0

    def activate(self, context):
        if not self.is_activatable:
            return None

        failing_pre_requisites = self.activation_pre_requisites.get_failing_pre_requisites(context)
        if failing_pre_requisites:
            return FailedActivation.from_activation(self.activation, failing_pre_requisites)
        else:
            return self.activation


class Edge:

    def __init__(self, from_vertex, to_vertex):
        self.from_vertex = from_vertex
        self.to_vertex = to_vertex
        self.traversal_pre_requisites = PreRequisiteList()  # can we visit the vertex?

    def can_traverse(self, context):
        return len(self.traversal_pre_requisites.get_failing_pre_requisites(context)) == 0


class Visitor:

    def __init__(self, graph, game_context):
        self.graph = graph
        self.context = game_context
        self.current_vertex = None

    @staticmethod
    def visit_graph(graph, game_context):
        visitor = Visitor(graph, game_context)
        visitor.go_to_vertex("START")
        return visitor

    def go_to_vertex(self, vertex_id):
        """Set the visitor on specific vertex by its ID. Use sparingly and with caution, it could invalidate an
        assumption made by the graph authors."""
        self.current_vertex = self.graph[vertex_id]
        self.context.update(self.current_vertex.context)

    def traverse_edge(self, to_vertex_id):
        edge = self.current_vertex.get_edge_by_to_vertex_id(to_vertex_id)
        if edge.can_traverse(self.context):
            self.current_vertex = edge.to_vertex

    def activate_current_vertex(self):
        return self.current_vertex.activate(self.context)
