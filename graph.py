# -*- coding: utf-8 -*-

from qgis.core import *

class Graph():
    # init graph object
    # if None or empty dict, use empty dict
    def __init__(self, graph_dict=None):
        if graph_dict == None:
            graph_dict = {}
        self.__graph_dict = graph_dict

    # returns the graph
    def get_graph(self):
        return self.__graph_dict

    # create set
    def make_set(self, parent, rank, vertice):
        parent[vertice] = vertice
        rank[vertice] = 0

    # find vertice parent
    def find(self, parent, vertice):
        if parent[vertice] != vertice:
            parent[vertice] = self.find(parent, parent[vertice])
        return parent[vertice]

    # union sets
    def union(self, parent, rank, vertice1, vertice2):
        root1 = self.find(parent, vertice1)
        root2 = self.find(parent, vertice2)
        if root1 != root2:
            if rank[root1] > rank[root2]:
                parent[root2] = root1
            else:
                parent[root1] = root2
            if rank[root1] == rank[root2]: rank[root2] += 1

    # Kruskal algorithm downloaded from https://gist.github.com/hayderimran7/09960ca438a65a9bd10d0254b792f48f
    def kruskal(self, parent, rank, graph):
        for vertice in graph['vertices']:
            self.make_set(parent, rank, vertice)
        minimum_spanning_tree = set()
        edges = list(graph['edges'])
        edges.sort()
        for edge in edges:
            weight, vertice1, vertice2 = edge
            if self.find(parent, vertice1) != self.find(parent, vertice2):
                self.union(parent, rank, vertice1, vertice2)
                minimum_spanning_tree.add(edge)

        return sorted(minimum_spanning_tree)

    # creating graph as dictionary
    def create_graph(self, shaft_layer, edges_layer):
        d = QgsDistanceArea()

        vertices = []
        for shaft_feat in shaft_layer.getFeatures():
            vertices.append(str(shaft_feat['ID']))

        edges = set()
        # save every edge
        for edge in edges_layer.getFeatures():
            shaft_1 = self.filter_by_id(edge['Shaft_1'], shaft_layer)
            shaft_2 = self.filter_by_id(edge['Shaft_2'], shaft_layer)
            if shaft_1.geometry() != None:
                if shaft_2.geometry() != None:
                    shaft_1_point = QgsPoint(shaft_1.geometry().asPoint()[0], shaft_1.geometry().asPoint()[1])
                    shaft_2_point = QgsPoint(shaft_2.geometry().asPoint()[0], shaft_2.geometry().asPoint()[1])

                    distance = d.measureLine(shaft_1_point, shaft_2_point)
                    edges.add((int(distance), str(edge['Shaft_1']), str(edge['Shaft_2'])))
                    edges.add((int(distance), str(edge['Shaft_2']), str(edge['Shaft_1'])))

        graph = {'vertices': vertices, 'edges': edges}
        return graph

    # filter by id()
    def filter_by_id(self, fid, layer):
        feature = QgsFeature()
        feats = layer.getFeatures()
        for feat in feats:
            if feat['ID'] == fid:
                feature = feat
        #iterator = layer.getFeatures(QgsFeatureRequest().setFilterFid(fid))
        #feature = next(iterator)

        return feature

    def union2(self, dict1, dict2):
        return dict(list(dict1.items()) + list(dict2.items()))

    def change_graph_repre(self, graph):

        g = {}
        for d, n1, n2 in graph['edges']:
            g[n1] = {}
            g[n2] = {}

        for d, n1, n2 in graph['edges']:
            g[n1] = self.union2(g[n1], {n2: d})
            g[n2] = self.union2(g[n2], {n1: d})

        return g

    # algorithm downloaded from https://gist.github.com/ngenator/6178728
    def bellman_ford(self, graph, source):
        # Step 1: Prepare the distance and predecessor for each node
        distance, predecessor = dict(), dict()
        for node in graph:
            distance[node], predecessor[node] = float('inf'), None
        distance[source] = 0

        # Step 2: Relax the edges
        for _ in range(len(graph) - 1):
            for node in graph:
                for neighbour in graph[node]:
                    # If the distance between the node and the neighbour is lower than the current, store it
                    if distance[neighbour] > distance[node] + graph[node][neighbour]:
                        distance[neighbour], predecessor[neighbour] = distance[node] + graph[node][neighbour], node

        # Step 3: Check for negative weight cycles
        for node in graph:
            for neighbour in graph[node]:
                assert distance[neighbour] <= distance[node] + graph[node][neighbour], "Negative weight cycle."

        return distance, predecessor

    # From https://stackoverflow.com/questions/22897209/dijkstras-algorithm-in-python second answer
    def dijkstra(self, distances, nodes, current):
        unvisited = {node: None for node in nodes}  # using None as +inf
        visited = {}
        currentDistance = 0
        unvisited[current] = currentDistance

        while True:
            for neighbour, distance in distances[current].items():
                if neighbour not in unvisited: continue
                newDistance = currentDistance + distance
                if unvisited[neighbour] is None or unvisited[neighbour] > newDistance:
                    unvisited[neighbour] = newDistance
            visited[current] = currentDistance
            del unvisited[current]
            if not unvisited: break
            candidates = [node for node in unvisited.items() if node[1]]
            current, currentDistance = sorted(candidates, key=lambda x: x[1])[0]

        return visited
    """
    def jarnikAlgorithm(self, graph, weight):
        q = graph['vertices'] #pridej vsechny uzly do fronty

        distances = [] #pole vzdalenosti
        for i in len(graph['edges']):
            distances[i] = sys.maxint #uzly jsou nekonecne daleko
        distances[0] = 0  #koren

        predecessors = graph['vertices'] #pole predchudcu
        predecessors[0] = None #koren nema predchudce

        while q: #dokud neni fronta prazdna
        u = queue.extractMin() // vrat prvek v minimalni vzdalenosti
        for node in descendants(u) do // pro vsechny potomky u
            if queue.contains(node) AND weight(u, node) < d[node] // pokud se nektery z potomku priblizil k dosud postavene kostre
                then predecessors[node] = u // u je tedy jeho predek
                d[node] = weight(u, node) // nastav novou vzdalenost

        return predecessors // vrat pole predchudcu
    """