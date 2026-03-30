"""
Módulo de cálculo de rotas para carro.

Implementa e compara dois algoritmos de busca de caminho mínimo:

  - Dijkstra:  explora todos os nós em ordem crescente de custo acumulado.
               Garante o caminho ótimo mas expande mais nós que o necessário.
               Complexidade: O((V + E) log V) com heap binário.

  - A* (A-star): guia a busca com uma heurística admissível h(n), estimando
               o custo restante até o destino via distância Haversine dividida
               pela velocidade máxima permitida (80 km/h).
               Complexidade: O((V + E) log V) no pior caso, mas expande
               significativamente menos nós na prática.

Ambos usam o peso 'tempo_dinamico' calculado com dados reais da CTTU.
"""

import math
import networkx as nx
import osmnx as ox

from src.utils.grafo      import COORDS_ORIGEM, COORDS_DESTINO
from src.utils.benchmark  import medir_tempo, comparar_algoritmos

# Velocidade máxima adotada na heurística A* (km/h → m/s)
# Deve ser >= velocidade real máxima para garantir admissibilidade
VELOCIDADE_MAX_HEURISTICA_MS = 80 / 3.6


def _heuristica_astar(graph, no_destino):
    """
    Cria a função heurística admissível para o A*.

    Usa a distância Haversine entre o nó atual e o destino
    dividida pela velocidade máxima possível no grafo.
    Como h(n) ≤ custo real, a heurística é admissível (nunca
    superestima) e garante que A* encontre o caminho ótimo.

    Parâmetros:
        graph:      grafo viário de carros
        no_destino: ID do nó de destino

    Retorna:
        Função heuristica(u, v) → float (tempo estimado em segundos)
    """
    lat_dest = graph.nodes[no_destino]['y']
    lon_dest = graph.nodes[no_destino]['x']

    def heuristica(u, _v):
        lat_u = graph.nodes[u]['y']
        lon_u = graph.nodes[u]['x']

        # Distância Haversine entre nó atual e destino (em metros)
        R = 6_371_000
        phi1, phi2 = math.radians(lat_u), math.radians(lat_dest)
        dphi    = math.radians(lat_dest - lat_u)
        dlambda = math.radians(lon_dest - lon_u)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        distancia_m = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        # Tempo mínimo possível = distância / velocidade máxima
        return distancia_m / VELOCIDADE_MAX_HEURISTICA_MS

    return heuristica


def _dijkstra(graph, no_origem, no_destino):
    """Executa Dijkstra com peso 'tempo_dinamico'. Retorna lista de nós."""
    return nx.shortest_path(graph, source=no_origem, target=no_destino, weight='tempo_dinamico')


def _astar(graph, no_origem, no_destino):
    """Executa A* com heurística Haversine e peso 'tempo_dinamico'. Retorna lista de nós."""
    h = _heuristica_astar(graph, no_destino)
    return nx.astar_path(graph, source=no_origem, target=no_destino,
                         heuristic=h, weight='tempo_dinamico')


def calcular_rotas_carro(graph):
    """
    Calcula as rotas de carro entre Cine São Luiz e Faculdade Nova Roma,
    comparando Dijkstra e A* em termos de tempo de execução e rota gerada.

    Complexidade:
        Dijkstra:  O((V + E) log V)  — V nós, E arestas
        A*:        O((V + E) log V)  no pior caso; na prática muito mais rápido
                   por expandir apenas os nós na direção do destino

    Parâmetros:
        graph: grafo viário de carros com 'tempo_dinamico' injetado

    Retorna:
        dict com chaves:
            'no_origem', 'no_destino':      nós OSM de origem e destino
            'rota_tempo':                   rota mais rápida (Dijkstra)
            'rota_astar':                   rota mais rápida (A*)
            'rota_distancia':               rota mais curta (por 'length')
            'tempo_seg':                    tempo da rota mais rápida (s)
            'distancia_metros':             distância da rota mais curta (m)
            'benchmark':                    dict com tempos de execução (ms)
    """
    no_origem  = ox.distance.nearest_nodes(graph, X=COORDS_ORIGEM[1],  Y=COORDS_ORIGEM[0])
    no_destino = ox.distance.nearest_nodes(graph, X=COORDS_DESTINO[1], Y=COORDS_DESTINO[0])

    # --- Comparação Dijkstra vs A* (análise empírica) ---
    print("Comparando Dijkstra vs A* (tempo de execução):")
    bench = comparar_algoritmos(
        'Dijkstra', _dijkstra,
        'A*',       _astar,
        graph, no_origem, no_destino
    )

    rota_tempo = bench['resultado_a']   # Dijkstra
    rota_astar = bench['resultado_b']   # A*

    # --- Rota mais curta por distância física ---
    rota_distancia, _ = medir_tempo(
        nx.shortest_path, graph,
        source=no_origem, target=no_destino, weight='length'
    )

    # --- Calcula métricas das rotas ---
    tempo_seg        = nx.shortest_path_length(graph, source=no_origem, target=no_destino, weight='tempo_dinamico')
    distancia_metros = nx.shortest_path_length(graph, source=no_origem, target=no_destino, weight='length')

    print(f"Carro – rota mais rápida (Dijkstra): {tempo_seg / 60:.2f} min")
    print(f"Carro – rota mais curta:             {distancia_metros / 1000:.2f} km\n")

    return {
        'no_origem':        no_origem,
        'no_destino':       no_destino,
        'rota_tempo':       rota_tempo,
        'rota_astar':       rota_astar,
        'rota_distancia':   rota_distancia,
        'tempo_seg':        tempo_seg,
        'distancia_metros': distancia_metros,
        'benchmark': {
            'dijkstra_ms': bench['tempo_ms_a'],
            'astar_ms':    bench['tempo_ms_b'],
        },
    }
