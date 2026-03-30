"""
Funções auxiliares reutilizadas por todos os módulos de rota.

Inclui utilitários para localizar nós em ruas específicas,
montar rotas com waypoints e calcular tempos de percurso.
"""

import math
import networkx as nx


def no_na_rua(graph, nome_rua, lat_ref, lon_ref):
    """
    Encontra o nó do grafo que pertence a uma rua específica e
    está mais próximo de uma coordenada de referência.

    Parâmetros:
        graph:    grafo MultiDiGraph do OSMnx
        nome_rua: nome (ou parte do nome) da rua desejada
        lat_ref:  latitude de referência para escolher o nó mais próximo
        lon_ref:  longitude de referência

    Retorna:
        ID do nó mais próximo na rua, ou None se não encontrada
    """
    nome_lower = nome_rua.lower()
    candidatos = set()

    for u, v, data in graph.edges(data=True):
        name = data.get('name', '')
        nomes = [name] if isinstance(name, str) else (name if isinstance(name, list) else [])
        if any(nome_lower in n.lower() for n in nomes):
            candidatos.add(u)
            candidatos.add(v)

    if not candidatos:
        return None

    def distancia(node):
        nd = graph.nodes[node]
        return math.hypot(nd['y'] - lat_ref, nd['x'] - lon_ref)

    return min(candidatos, key=distancia)


def rota_via_waypoints(graph, waypoints, weight):
    """
    Calcula uma rota completa passando por uma sequência de waypoints.

    Une sub-rotas consecutivas em um único caminho, evitando
    duplicação de nós nas junções.

    Parâmetros:
        graph:     grafo MultiDiGraph do OSMnx
        waypoints: lista de IDs de nós [origem, ..., destino]
        weight:    atributo de peso das arestas (ex: 'tempo_caminhada')

    Retorna:
        Lista de IDs de nós formando a rota completa
    """
    rota_completa = []
    for origem_wp, destino_wp in zip(waypoints[:-1], waypoints[1:]):
        trecho = nx.shortest_path(graph, source=origem_wp, target=destino_wp, weight=weight)
        if rota_completa:
            trecho = trecho[1:]  # Remove nó duplicado na junção entre trechos
        rota_completa.extend(trecho)
    return rota_completa


def tempo_rota(graph, rota, weight):
    """
    Calcula o tempo total de uma rota somando o peso de cada aresta.

    Usa sempre a aresta de menor custo quando há paralelas entre dois nós.

    Parâmetros:
        graph:  grafo MultiDiGraph do OSMnx
        rota:   lista de IDs de nós
        weight: atributo de peso das arestas (ex: 'tempo_bicicleta')

    Retorna:
        Tempo total em segundos (float)
    """
    total = 0.0
    for u, v in zip(rota[:-1], rota[1:]):
        edge_data = graph.get_edge_data(u, v)
        if edge_data:
            melhor = min(edge_data.values(), key=lambda d: d.get(weight, float('inf')))
            total += melhor.get(weight, 0)
    return total


def rota_para_latlng(graph, rota):
    """
    Converte uma rota de IDs de nós em lista de coordenadas (lat, lon).

    Usa a geometria real da aresta quando disponível, garantindo que
    a linha no mapa siga o traçado real da rua.

    Parâmetros:
        graph: grafo MultiDiGraph do OSMnx
        rota:  lista de IDs de nós

    Retorna:
        Lista de tuplas (lat, lon)
    """
    coords = []
    for u, v in zip(rota[:-1], rota[1:]):
        data = min(graph.get_edge_data(u, v).values(), key=lambda d: d.get('length', 0))
        if 'geometry' in data:
            # A geometria LineString armazena (lon, lat); invertemos para (lat, lon)
            coords.extend([(y, x) for x, y in data['geometry'].coords])
        else:
            # Sem geometria: usa as coordenadas dos nós diretamente
            coords.append((graph.nodes[u]['y'], graph.nodes[u]['x']))
            coords.append((graph.nodes[v]['y'], graph.nodes[v]['x']))
    return coords
