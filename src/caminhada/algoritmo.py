"""
Módulo de cálculo de rotas a pé (caminhada).

Calcula duas rotas entre Cine São Luiz e Faculdade Nova Roma:

  Rota 1 - Av. Domingos Ferreira         (~2h)
  Rota 2 - Av. Sul Gov. Cid Sampaio /
            Av. Mal. Mascarenhas de Morais (~2h 1min)

Usa o grafo de pedestres (network_type='walk') com velocidade
média de 5 km/h.
"""

import osmnx as ox

from src.utils.grafo   import COORDS_ORIGEM, COORDS_DESTINO
from src.utils.helpers import no_na_rua, rota_via_waypoints, tempo_rota


def calcular_rotas_caminhada(graph_walk):
    """
    Calcula as duas rotas de caminhada usando Dijkstra com o peso
    'tempo_caminhada' (distância / 5 km/h).

    Parâmetros:
        graph_walk: grafo de pedestres com o atributo 'tempo_caminhada' injetado

    Retorna:
        Lista de dicts, cada um com:
            'nome':      nome descritivo da rota
            'rota':      lista de nós OSM do caminho completo
            'tempo_seg': tempo total estimado em segundos
            'tempo_min': tempo total estimado em minutos
    """
    # Localiza os nós mais próximos das coordenadas de origem e destino
    no_origem  = ox.distance.nearest_nodes(graph_walk, X=COORDS_ORIGEM[1],  Y=COORDS_ORIGEM[0])
    no_destino = ox.distance.nearest_nodes(graph_walk, X=COORDS_DESTINO[1], Y=COORDS_DESTINO[0])

    rotas = []

    # ------------------------------------------------------------------
    # Rota 1 - Av. Eng. Domingos Ferreira (~2h)
    # Percurso: Cinco Pontas → Av. José Estelita → Av. Saturnino de Brito
    #           → Ponte Paulo Guerra → Av. Herculano Bandeira
    #           → Av. Eng. Domingos Ferreira
    # ------------------------------------------------------------------
    wp_domingos = no_na_rua(graph_walk, 'Domingos Ferreira', lat_ref=-8.108, lon_ref=-34.900)

    if wp_domingos:
        waypoints_rota1 = [no_origem, wp_domingos, no_destino]
    else:
        print("   [aviso] Av. Domingos Ferreira não encontrada no grafo OSM - usando rota direta.")
        waypoints_rota1 = [no_origem, no_destino]

    rota1      = rota_via_waypoints(graph_walk, waypoints_rota1, weight='tempo_caminhada')
    tempo1_seg = tempo_rota(graph_walk, rota1, weight='tempo_caminhada')
    rotas.append({
        'nome':      'Av. Domingos Ferreira',
        'rota':      rota1,
        'tempo_seg': tempo1_seg,
        'tempo_min': tempo1_seg / 60,
    })
    print(f"Caminhada - Rota 1 (Av. Domingos Ferreira):           {tempo1_seg / 3600:.2f} h  "
          f"({tempo1_seg / 60:.0f} min)")

    # ------------------------------------------------------------------
    # Rota 2 - Av. Sul Gov. Cid Sampaio / Av. Mal. Mascarenhas de Morais (~2h 1min)
    # Percurso: R. da Concórdia → R. Imperial → Av. Sul Gov. Cid Sampaio
    #           → Ponte Motocolombó / PE-008
    #           → Av. Mal. Mascarenhas de Morais → R. Padre Carapuceiro
    # ------------------------------------------------------------------
    wp_av_sul      = no_na_rua(graph_walk, 'Cid Sampaio',           lat_ref=-8.090, lon_ref=-34.895)
    wp_mascarenhas = no_na_rua(graph_walk, 'Mascarenhas de Morais', lat_ref=-8.106, lon_ref=-34.899)

    avisos = []
    if wp_av_sul      is None: avisos.append('Av. Sul Gov. Cid Sampaio')
    if wp_mascarenhas is None: avisos.append('Av. Mal. Mascarenhas de Morais')
    if avisos:
        print(f"   [aviso] Não encontrado no grafo OSM: {', '.join(avisos)}")

    waypoints_rota2 = [no_origem]
    if wp_av_sul:      waypoints_rota2.append(wp_av_sul)
    if wp_mascarenhas: waypoints_rota2.append(wp_mascarenhas)
    waypoints_rota2.append(no_destino)

    rota2      = rota_via_waypoints(graph_walk, waypoints_rota2, weight='tempo_caminhada')
    tempo2_seg = tempo_rota(graph_walk, rota2, weight='tempo_caminhada')
    rotas.append({
        'nome':      'Av. Sul / Mascarenhas de Morais',
        'rota':      rota2,
        'tempo_seg': tempo2_seg,
        'tempo_min': tempo2_seg / 60,
    })
    print(f"Caminhada - Rota 2 (Av. Sul / Mascarenhas de Morais): {tempo2_seg / 3600:.2f} h  "
          f"({tempo2_seg / 60:.0f} min)\n")

    return rotas
