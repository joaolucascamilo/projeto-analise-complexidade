"""
Módulo de cálculo de rotas para bicicleta.

Calcula três rotas entre Cine São Luiz e Faculdade Nova Roma,
correspondendo aos trajetos reais identificados no Google Maps:

  Rota 1 - Via Mangue        (~34 min)
  Rota 2 - Av. Boa Viagem    (~33 min)
  Rota 3 - R. Arq. Luiz Nunes (~39 min)

Usa o grafo de pedestres (network_type='walk') como base,
pois inclui ciclovias, calçadas e caminhos que o grafo
de carros não contém.
"""

import networkx as nx
import osmnx as ox

from src.utils.grafo   import COORDS_ORIGEM, COORDS_DESTINO
from src.utils.helpers import no_na_rua, rota_via_waypoints, tempo_rota


def calcular_rotas_bicicleta(graph_bike):
    """
    Calcula as três rotas de bicicleta usando o algoritmo de Dijkstra
    com o peso 'tempo_bicicleta' (distância / velocidade de 20 km/h).

    Parâmetros:
        graph_bike: grafo de pedestres com o atributo 'tempo_bicicleta' injetado

    Retorna:
        Lista de dicts, cada um com:
            'nome':      nome descritivo da rota
            'rota':      lista de nós OSM do caminho completo
            'tempo_seg': tempo total estimado em segundos
            'tempo_min': tempo total estimado em minutos
    """
    # Localiza os nós mais próximos das coordenadas de origem e destino
    no_origem  = ox.distance.nearest_nodes(graph_bike, X=COORDS_ORIGEM[1],  Y=COORDS_ORIGEM[0])
    no_destino = ox.distance.nearest_nodes(graph_bike, X=COORDS_DESTINO[1], Y=COORDS_DESTINO[0])

    rotas = []

    # Rota 1 - Via Mangue (~34 min)
    # Percurso: Centro -> Via Mangue (PE-015) -> Av. Herculano Bandeira
    #           -> Av. Conselheiro Aguiar -> Faculdade Nova Roma
   
    wp_via_mangue = no_na_rua(graph_bike, 'Via Mangue', lat_ref=-8.090, lon_ref=-34.895)

    if wp_via_mangue:
        waypoints_rota1 = [no_origem, wp_via_mangue, no_destino]
    else:
        print("   [aviso] Via Mangue não encontrada no grafo OSM - usando rota direta.")
        waypoints_rota1 = [no_origem, no_destino]

    rota1       = rota_via_waypoints(graph_bike, waypoints_rota1, weight='tempo_bicicleta')
    tempo1_seg  = tempo_rota(graph_bike, rota1, weight='tempo_bicicleta')
    rotas.append({
        'nome':      'Via Mangue',
        'rota':      rota1,
        'tempo_seg': tempo1_seg,
        'tempo_min': tempo1_seg / 60,
    })
    print(f"Bicicleta - Rota 1 (Via Mangue):          {tempo1_seg / 60:.0f} min")

    # Rota 2 - Av. Boa Viagem (~33 min)
    # Percurso: Centro -> Av. Boa Viagem (orla) -> Faculdade Nova Roma
    # É a rota mais rápida pois acompanha a orla com poucas interrupções
    
    wp_boa_viagem = no_na_rua(graph_bike, 'Boa Viagem', lat_ref=-8.107, lon_ref=-34.900)

    if wp_boa_viagem:
        waypoints_rota2 = [no_origem, wp_boa_viagem, no_destino]
    else:
        print("   [aviso] Av. Boa Viagem não encontrada no grafo OSM - usando rota direta.")
        waypoints_rota2 = [no_origem, no_destino]

    rota2       = rota_via_waypoints(graph_bike, waypoints_rota2, weight='tempo_bicicleta')
    tempo2_seg  = tempo_rota(graph_bike, rota2, weight='tempo_bicicleta')
    rotas.append({
        'nome':      'Av. Boa Viagem',
        'rota':      rota2,
        'tempo_seg': tempo2_seg,
        'tempo_min': tempo2_seg / 60,
    })
    print(f"Bicicleta - Rota 2 (Av. Boa Viagem):      {tempo2_seg / 60:.0f} min")

    # Rota 3 - Rua Arquiteto Luiz Nunes (~39 min)
    # Percurso: Centro -> interior de Boa Viagem -> R. Arq. Luiz Nunes
    #           -> Faculdade Nova Roma
    # Rota alternativa mais interna, com mais cruzamentos
   
    wp_luiz_nunes = no_na_rua(graph_bike, 'Luiz Nunes', lat_ref=-8.112, lon_ref=-34.902)

    if wp_luiz_nunes:
        waypoints_rota3 = [no_origem, wp_luiz_nunes, no_destino]
    else:
        print("   [aviso] R. Arq. Luiz Nunes não encontrada no grafo OSM - usando rota direta.")
        waypoints_rota3 = [no_origem, no_destino]

    rota3       = rota_via_waypoints(graph_bike, waypoints_rota3, weight='tempo_bicicleta')
    tempo3_seg  = tempo_rota(graph_bike, rota3, weight='tempo_bicicleta')
    rotas.append({
        'nome':      'R. Arq. Luiz Nunes',
        'rota':      rota3,
        'tempo_seg': tempo3_seg,
        'tempo_min': tempo3_seg / 60,
    })
    print(f"Bicicleta - Rota 3 (R. Arq. Luiz Nunes):  {tempo3_seg / 60:.0f} min")

    # Identifica a rota mais rápida
    mais_rapida = min(rotas, key=lambda r: r['tempo_seg'])
    print(f"\n  Melhor rota de bicicleta: '{mais_rapida['nome']}' "
          f"({mais_rapida['tempo_min']:.0f} min)\n")

    return rotas
