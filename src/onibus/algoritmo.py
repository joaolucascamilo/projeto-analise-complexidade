"""
Módulo de cálculo de rotas de transporte público (Ônibus/BRT).
"""
import os
import pandas as pd
import networkx as nx
import osmnx as ox
from osmnx.distance import great_circle

# ==========================================
# CONSTANTES DE CONFIGURAÇÃO
# ==========================================
TARIFA_ANEL_A = 4.10
TEMPO_ESPERA_PADRAO = 300       # 5 minutos
PENALIDADE_TRANSBORDO = 720     # 12 minutos (Dor de trocar de ônibus)
FATOR_FADIGA_CAMINHADA = 3.5    # Multiplicador de cansaço
VELOCIDADE_CAMINHADA_MS = 1.2   # ~4.3 km/h

_GRAFO_ONIBUS_CACHE = None
_DICIONARIO_LINHAS_CACHE = None

# Função caçadora de diretórios (Blinda o sistema contra erros de caminho)
def obter_caminho_arquivo(nome_arquivo):
    for pasta in ['./', './data/', '../', '../../']:
        caminho = os.path.join(pasta, nome_arquivo)
        if os.path.exists(caminho):
            return caminho
    raise FileNotFoundError(f"Arquivo GTFS não encontrado: {nome_arquivo}")

# ==========================================
# FUNÇÕES MATEMÁTICAS
# ==========================================
def calcular_peso_aresta(atributos):
    # Se a aresta não tiver tempo pré-calculado, calcula na hora usando os metros
    tempo = atributos.get('tempo_dinamico')
    if tempo is None:
        tempo = atributos.get('length', 1) / VELOCIDADE_CAMINHADA_MS
        
    modal = atributos.get('modal', 'calcada')
    
    peso = tempo
    if modal in ['pedestre/calcada', 'caminhada', 'calcada']:
        peso = tempo * FATOR_FADIGA_CAMINHADA 
    elif modal == 'embarque':
        peso += PENALIDADE_TRANSBORDO 
        
    return peso

def peso_multiobjetivo(u, v, d):
    return min(calcular_peso_aresta(attr) for attr in d.values())

def carregar_dicionario_linhas():
    global _DICIONARIO_LINHAS_CACHE
    if _DICIONARIO_LINHAS_CACHE is not None: return _DICIONARIO_LINHAS_CACHE
        
    mapa_linhas = {}
    try:
        df_trips = pd.read_csv(obter_caminho_arquivo('trips.txt'), usecols=['trip_id', 'route_id'])
        df_routes = pd.read_csv(obter_caminho_arquivo('routes.txt'), usecols=['route_id', 'route_short_name', 'route_long_name'])
        df_linhas_nomes = pd.merge(df_trips, df_routes, on='route_id')
        
        for row in df_linhas_nomes.itertuples():
            curto = str(row.route_short_name) if pd.notna(row.route_short_name) else ""
            longo = str(row.route_long_name) if pd.notna(row.route_long_name) else ""
            mapa_linhas[row.trip_id] = f"{curto} - {longo}".strip(" -")
            
        _DICIONARIO_LINHAS_CACHE = mapa_linhas
    except Exception as e:
        print(f"Aviso [Ônibus]: Erro lendo nomes das linhas: {e}")
    return mapa_linhas

def construir_grafo_transporte(graph_base):
    global _GRAFO_ONIBUS_CACHE
    if _GRAFO_ONIBUS_CACHE is not None: return _GRAFO_ONIBUS_CACHE
        
    print("\n[Ônibus] Construindo Grafo Expandido no Tempo...")
    graph = graph_base.copy()
    
    try:
        df_stops = pd.read_csv(obter_caminho_arquivo('stops.txt'))
        gdf_nodes = ox.graph_to_gdfs(graph, edges=False)
        lon_min, lon_max = gdf_nodes['x'].min(), gdf_nodes['x'].max()
        lat_min, lat_max = gdf_nodes['y'].min(), gdf_nodes['y'].max()
        
        df_stops_filtrado = df_stops[
            (df_stops['stop_lat'] >= lat_min) & (df_stops['stop_lat'] <= lat_max) &
            (df_stops['stop_lon'] >= lon_min) & (df_stops['stop_lon'] <= lon_max)
        ]
        
        lons_paradas = df_stops_filtrado['stop_lon'].tolist()
        lats_paradas = df_stops_filtrado['stop_lat'].tolist()
        stop_ids = df_stops_filtrado['stop_id'].tolist()
        
        nos_rua_proximos = ox.distance.nearest_nodes(graph, X=lons_paradas, Y=lats_paradas)
        for i in range(len(stop_ids)):
            stop_id_grafo = f"stop_{stop_ids[i]}" 
            lon, lat, no_rua = lons_paradas[i], lats_paradas[i], nos_rua_proximos[i]

            graph.add_node(stop_id_grafo, x=lon, y=lat, tipo='parada_onibus')
            rua_lon, rua_lat = graph.nodes[no_rua]['x'], graph.nodes[no_rua]['y']
            dist_metros = great_circle(lat, lon, rua_lat, rua_lon)
            t_caminhada = dist_metros / VELOCIDADE_CAMINHADA_MS

            graph.add_edge(no_rua, stop_id_grafo, length=dist_metros, tempo_dinamico=t_caminhada, modal='caminhada')
            graph.add_edge(stop_id_grafo, no_rua, length=dist_metros, tempo_dinamico=t_caminhada, modal='caminhada')

        df_st = pd.read_csv(obter_caminho_arquivo('stop_times.txt'))
        
        def time_to_seconds(t):
            h, m, s = map(int, str(t).split(':'))
            return h * 3600 + m * 60 + s
            
        df_st['arrival_sec'] = df_st['arrival_time'].apply(time_to_seconds)
        df_st = df_st.sort_values(['trip_id', 'stop_sequence'])
        
        df_st['next_stop_id'] = df_st.groupby('trip_id')['stop_id'].shift(-1)
        df_st['next_arrival_sec'] = df_st.groupby('trip_id')['arrival_sec'].shift(-1)
        df_edges = df_st.dropna(subset=['next_stop_id'])
        
        set_paradas_validas = set(stop_ids)
        df_edges_filtrado = df_edges[
            df_edges['stop_id'].isin(set_paradas_validas) & 
            df_edges['next_stop_id'].isin(set_paradas_validas)
        ]
        
        set_embarques, set_desembarques = set(), set()
        
        for row in df_edges_filtrado.itertuples():
            stop_origem = f"stop_{int(row.stop_id) if isinstance(row.stop_id, float) else row.stop_id}"
            stop_destino = f"stop_{int(row.next_stop_id) if isinstance(row.next_stop_id, float) else row.next_stop_id}"
            
            no_origem = f"{stop_origem}_{row.trip_id}"
            no_destino = f"{stop_destino}_{row.trip_id}"
            tempo_viagem = max(60, row.next_arrival_sec - row.arrival_sec)
            
            lon_orig, lat_orig = graph.nodes[stop_origem]['x'], graph.nodes[stop_origem]['y']
            lon_dest, lat_dest = graph.nodes[stop_destino]['x'], graph.nodes[stop_destino]['y']
                
            if no_origem not in set_embarques:
                graph.add_node(no_origem, x=lon_orig, y=lat_orig, tipo='virtual_embarque')
                graph.add_edge(stop_origem, no_origem, tempo_dinamico=TEMPO_ESPERA_PADRAO, modal='embarque', trip_id=row.trip_id)
                set_embarques.add(no_origem)
                
            if no_destino not in set_desembarques:
                graph.add_node(no_destino, x=lon_dest, y=lat_dest, tipo='virtual_desembarque')
                graph.add_edge(no_destino, stop_destino, tempo_dinamico=0, modal='desembarque', trip_id=row.trip_id)
                set_desembarques.add(no_destino)

            graph.add_edge(no_origem, no_destino, tempo_dinamico=tempo_viagem, modal='onibus', trip_id=row.trip_id)

        arestas_tp = [(u, v, k) for u, v, k, d in graph.edges(keys=True, data=True) if d.get('modal') != 'carro/rua']
        grafo_transporte = graph.edge_subgraph(arestas_tp)
        
        print("[Ônibus] Malha de transporte montada!")
        _GRAFO_ONIBUS_CACHE = grafo_transporte
        return grafo_transporte
    except Exception as e:
        print(f"ERRO CRÍTICO GTFS: {e}")
        return None

# ==========================================
# CÁLCULO FINAL
# ==========================================
def calcular_rotas_onibus(graph_walk, coords_origem, coords_destino):
    grafo_tp = construir_grafo_transporte(graph_walk)
    if not grafo_tp:
        return {'tempo_seg': 0, 'custo': 0, 'erro': 'Falha GTFS', 'graph_transporte': None}

    n_origem = ox.distance.nearest_nodes(grafo_tp, X=coords_origem[1], Y=coords_origem[0]) 
    n_destino = ox.distance.nearest_nodes(grafo_tp, X=coords_destino[1], Y=coords_destino[0])
    mapa_linhas = carregar_dicionario_linhas()

    try:
        rota_tp = nx.shortest_path(grafo_tp, source=n_origem, target=n_destino, weight=peso_multiobjetivo)
        
        tempo_total = 0
        onibus_utilizados = 0
        
        for i in range(len(rota_tp) - 1):
            u, v = rota_tp[i], rota_tp[i+1]
            aresta = min(grafo_tp[u][v].values(), key=calcular_peso_aresta)
            
            modal = aresta.get('modal', 'calcada')
            tempo = aresta.get('tempo_dinamico')
            if tempo is None: tempo = aresta.get('length', 1) / VELOCIDADE_CAMINHADA_MS
            tempo_total += tempo
            
            if modal == 'embarque': onibus_utilizados += 1

        return {
            'rota_nós': rota_tp,
            'tempo_seg': tempo_total,
            'custo': TARIFA_ANEL_A if onibus_utilizados > 0 else 0.0,
            'onibus_utilizados': onibus_utilizados,
            'graph_transporte': grafo_tp # A MÁGICA: Agora retornamos o grafo junto!
        }
    except nx.NetworkXNoPath:
        return {'tempo_seg': 0, 'custo': 0, 'erro': 'Sem rota', 'graph_transporte': None}