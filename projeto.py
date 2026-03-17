import osmnx as ox
import pandas as pd
import warnings
import networkx as nx
import folium  
import matplotlib.pyplot as plt
from osmnx.distance import great_circle

# suprime warnings do pandas
warnings.filterwarnings('ignore')

# ==========================================
# 1. EXTRAÇÃO DO GRAFO DA MALHA VIÁRIA (OSM)
# ==========================================
print("1. Baixando o grafo do Recife... (Isso pode levar alguns segundos)")
coords_origem = (-8.06374, -34.88269)  # Cine São Luiz (Centro)
coords_destino = (-8.11782, -34.90017) # Faculdade Nova Roma (Boa Viagem)
# network_type='drive' traz ruas para carros
graph = ox.graph_from_point(coords_origem, dist=8000, network_type='drive')
print("Grafo viário estruturado com sucesso!\n")

# ==========================================
# 2. PROCESSAMENTO DAS VELOCIDADES (CTTU)
# ==========================================
print("2. Processando dados de velocidade da CTTU...")
file_velocidade = 'resources_c2d9c049-6511-4dc4-9691-b76a43e4f7e3_fotossensores-2025-dezembro-quantitativo-das-vias-por-velocidade-media.csv'
df_vel = pd.read_csv(file_velocidade, sep=';')

# pesos usados na média de velocidade
pesos_velocidade = {
    'qtd_0a10km': 5.0, 'qtd_11a20km': 15.5, 'qtd_21a30km': 25.5,
    'qtd_31a40km': 35.5, 'qtd_41a50km': 45.5, 'qtd_51a60km': 55.5,
    'qtd_61a70km': 65.5, 'qtd_71a80km': 75.5, 'qtd_81a90km': 85.5,
    'qtd_91a100km': 95.5, 'qtd_acimade100km': 105.0
}

# Cálculos da velocidade
colunas_qtd = list(pesos_velocidade.keys())
df_vel['total_veiculos'] = df_vel[colunas_qtd].sum(axis=1)
soma_velocidades = sum(df_vel[col] * peso for col, peso in pesos_velocidade.items())
df_vel['velocidade_media_estimada'] = soma_velocidades / df_vel['total_veiculos'].replace(0, 1)

# escolhe hora 8 como exemplo e calcula média por equipamento
df_vel_pico_manha = df_vel[df_vel['hora'] == 8].groupby('equipamento')['velocidade_media_estimada'].mean().reset_index()
print("Velocidades processadas.\n")

# ==========================================
# 3. CRUZAMENTO COM A LOCALIZAÇÃO (LAT/LON)
# ==========================================
print("3. Cruzando dados com a localização dos equipamentos...")
file_localizacao = 'resources_36c2b47b-f439-4895-8b65-3f3dda36a4a7_lista-de-equipamentos-de-fiscalizacao-de-transito.csv'

# lê localização dos equipamentos (ignora linhas ruins)
df_loc = pd.read_csv(file_localizacao, sep=';', encoding='latin-1', on_bad_lines='skip')

# normaliza identificadores e adiciona 'REC'
df_loc['identificacao_equipamento'] = df_loc['identificacao_equipamento'].astype(str).str.strip()
df_loc_fc = df_loc[df_loc['identificacao_equipamento'].str.startswith('FC', na=False)].copy()
df_loc_fc['equipamento'] = df_loc_fc['identificacao_equipamento'] + 'REC'

# junta velocidades com lat/lon
df_radares_no_mapa = pd.merge(df_vel_pico_manha, df_loc_fc[['equipamento', 'latitude', 'longitude']], on='equipamento', how='inner')

print("Radares mapeados com sucesso! Exemplo:")
print(df_radares_no_mapa.head())

# ==========================================
# 4. INJETANDO PESOS DINÂMICOS NO GRAFO
# ==========================================
print("4. Mapeando radares para as ruas (arestas) do grafo...")

# 4.1 definir tempo base (40 km/h em m/s)
velocidade_padrao_ms = 40 / 3.6 

for u, v, key, data in graph.edges(keys=True, data=True):
    # O OSMnx já traz o tamanho da rua em metros no atributo 'length'
    distancia_metros = data.get('length', 1) 
    
    # Adicionamos o atributo 'tempo_dinamico' na aresta (em segundos)
    data['tempo_dinamico'] = distancia_metros / velocidade_padrao_ms

# 4.2 extrai lon/lat para o formato OSMnx (X=lon, Y=lat)
lons = df_radares_no_mapa['longitude'].tolist()
lats = df_radares_no_mapa['latitude'].tolist()

# 4.3 acha a aresta mais próxima de cada radar
arestas_proximas = ox.distance.nearest_edges(graph, X=lons, Y=lats)

# 4.4. Atualizar o 'tempo_dinamico' dessas arestas com a velocidade real da CTTU
for idx, (u, v, key) in enumerate(arestas_proximas):
    velocidade_kmh = df_radares_no_mapa.iloc[idx]['velocidade_media_estimada']
    
    # Trava de segurança para evitar divisão por zero se a via estiver totalmente parada
    if velocidade_kmh < 1:
        velocidade_kmh = 1.0 
        
    velocidade_ms = velocidade_kmh / 3.6
    distancia_metros = graph[u][v][key].get('length', 1)
    
    # Recalcula o tempo com o trânsito real
    novo_tempo = distancia_metros / velocidade_ms
    
    # Sobrescreve o tempo base com o tempo congestionado/real
    graph[u][v][key]['tempo_dinamico'] = novo_tempo

print("Pesos reais da CTTU injetados nas arestas com sucesso!")

import networkx as nx

# ==========================================
# 5. EXECUÇÃO DO ALGORITMO DE DIJKSTRA
# ==========================================
print("\n5. Calculando as rotas otimizadas...")

# 5.1 localiza nós mais próximos da origem/destino
no_origem = ox.distance.nearest_nodes(graph, X=-34.88269, Y=-8.06374) 
no_destino = ox.distance.nearest_nodes(graph, X=-34.90017, Y=-8.11782)

# 5.2 rota mais curta usando peso 'length'
rota_distancia = nx.shortest_path(graph, source=no_origem, target=no_destino, weight='length')

# 5.3 rota mais rápida para carro (uso do tráfego real)
rota_tempo_carro = nx.shortest_path(graph, source=no_origem, target=no_destino, weight='tempo_dinamico')

# 5.4 custos do carro
tempo_carro = nx.shortest_path_length(graph, source=no_origem, target=no_destino, weight='tempo_dinamico')
distancia_total_metros = nx.shortest_path_length(graph, source=no_origem, target=no_destino, weight='length')

# 5.5 estimativa para moto: mesma rota do carro, velocidade constante média
velocidade_moto_ms = 50 / 3.6  # 50 km/h em m/s
tempo_moto = 0.0
for u, v in zip(rota_tempo_carro[:-1], rota_tempo_carro[1:]):
    edge_data = graph.get_edge_data(u, v)
    if edge_data:
        length = list(edge_data.values())[0].get('length', 0)
        tempo_moto += length / velocidade_moto_ms

print(f"-> Rota carro: {tempo_carro / 60:.2f} min.")
print(f"-> Rota moto (mesma via): {tempo_moto / 60:.2f} min.")
print(f"-> Rota mais curta: {distancia_total_metros / 1000:.2f} km.")
if tempo_moto < tempo_carro:
    diff = (tempo_carro - tempo_moto) / 60
    print(f"   moto é ~{diff:.1f} min mais rápida")
else:
    diff = (tempo_moto - tempo_carro) / 60
    print(f"   carro é ~{diff:.1f} min mais rápido")

# ==========================================
# 6. VISUALIZAÇÃO CARTOGRÁFICA INTERATIVA
# ==========================================
# utilizamos apenas o folium; o grafo estático foi removido
print("\n6. Gerando mapa interativo (HTML)...")

# função auxiliar: converte rota de nós em lista de (lat, lon)
# percorre cada par de nós consecutivos e extrai a geometria real da aresta
# quando disponível, garantindo que a linha siga o traçado da rua.
import shapely.geometry as geom

def rota_para_latlng(g, rota):
    coords = []
    for u, v in zip(rota[:-1], rota[1:]):
        # Seleciona a primeira aresta (ou a menor, se houver paralelas)
        data = min(g.get_edge_data(u, v).values(), key=lambda d: d.get('length', 0))
        if 'geometry' in data:
            # geometry é LineString; extrai coordenadas ordenadas (lon,lat)
            coords.extend([(y, x) for x, y in data['geometry'].coords])
        else:
            # fallback para os pontos dos nós
            coords.append((g.nodes[u]['y'], g.nodes[u]['x']))
            coords.append((g.nodes[v]['y'], g.nodes[v]['x']))
    return coords

# cria mapa centrado na origem
centro = (coords_origem[0], coords_origem[1])
m = folium.Map(location=centro, zoom_start=13, tiles='CartoDB positron')

# adiciona camadas das rotas
folium.PolyLine(
    rota_para_latlng(graph, rota_tempo_carro),
    color='red', weight=5, opacity=0.8,
    tooltip='carro (tempo)'
).add_to(m)
# moto segue a mesma rota, desenho tracejado
folium.PolyLine(
    rota_para_latlng(graph, rota_tempo_carro),
    color='green', weight=3, opacity=0.8,
    tooltip='moto (mesma via)',
    dash_array='5,5'
).add_to(m)
folium.PolyLine(
    rota_para_latlng(graph, rota_distancia),
    color='blue', weight=3, opacity=0.6,
    tooltip='distância'
).add_to(m)

# marcadores opcionais de origem/destino
folium.Marker(centro, tooltip='origem').add_to(m)
folium.Marker((coords_destino[0], coords_destino[1]), tooltip='destino').add_to(m)

# salva e abre automaticamente
m.save('mapa_rotas.html')
import webbrowser
webbrowser.open('mapa_rotas.html')

# ==========================================
# 7. IMPORTAÇÃO DO GTFS E FILTRO DINÂMICO
# ==========================================
print("\n7. Carregando dados do transporte público (GTFS)...")
file_stops = 'stops.txt' 

try:
    df_stops = pd.read_csv(file_stops)
    
    # O SEGREDO 1: Pegar os limites exatos do mapa de ruas (Grafo OSMnx)
    # Isso evita cortar uma linha de ônibus na metade!
    gdf_nodes = ox.graph_to_gdfs(graph, edges=False)
    lon_min, lon_max = gdf_nodes['x'].min(), gdf_nodes['x'].max()
    lat_min, lat_max = gdf_nodes['y'].min(), gdf_nodes['y'].max()
    
    df_stops_filtrado = df_stops[
        (df_stops['stop_lat'] >= lat_min) & (df_stops['stop_lat'] <= lat_max) &
        (df_stops['stop_lon'] >= lon_min) & (df_stops['stop_lon'] <= lon_max)
    ]
    
    # Atualiza a lista de IDs válidos
    stop_ids = df_stops_filtrado['stop_id'].tolist()
    
    print(f"Paradas perfeitamente alinhadas ao mapa: {len(df_stops_filtrado)}")

except FileNotFoundError:
    print(f"ERRO: Arquivo {file_stops} não encontrado.")

# ==========================================
# 8. CONECTANDO AS PARADAS À RUA (CAMINHADA)
# ==========================================
print("\n8. Criando arestas de caminhada entre calçadas e paradas de ônibus...")

# Velocidade média de caminhada (ex: 1.2 metros/segundo, que dá uns ~4.3 km/h)
velocidade_caminhada_ms = 1.2

# Extrair listas de coordenadas e IDs das paradas
lons_paradas = df_stops_filtrado['stop_lon'].tolist()
lats_paradas = df_stops_filtrado['stop_lat'].tolist()
stop_ids = df_stops_filtrado['stop_id'].tolist()

# Encontrar o nó de rua (cruzamento) mais próximo para cada parada de uma vez só
nos_rua_proximos = ox.distance.nearest_nodes(graph, X=lons_paradas, Y=lats_paradas)

# Adicionar as paradas ao grafo e conectá-las
for i in range(len(stop_ids)):
    # Criamos um ID com prefixo para não misturar com os IDs numéricos do OpenStreetMap
    stop_id_grafo = f"stop_{stop_ids[i]}" 
    lon = lons_paradas[i]
    lat = lats_paradas[i]
    no_rua = nos_rua_proximos[i]

    # 1. Adiciona a parada como um novo Nó (Vértice) no grafo
    graph.add_node(stop_id_grafo, x=lon, y=lat, tipo='parada_onibus')

    # 2. Calcula a distância física (em metros) entre o nó da rua e o nó da parada
    rua_lon = graph.nodes[no_rua]['x']
    rua_lat = graph.nodes[no_rua]['y']
    distancia_metros = great_circle(lat, lon, rua_lat, rua_lon)
    
    # 3. Calcula o peso da caminhada (tempo = distância / velocidade)
    tempo_caminhada = distancia_metros / velocidade_caminhada_ms

    # 4. Cria arestas bidirecionais (Rua -> Parada e Parada -> Rua)
    # Usamos a chave 'tempo_dinamico' para que o algoritmo Dijkstra consiga somar isso 
    # com o tempo de trânsito dos carros perfeitamente!
    graph.add_edge(no_rua, stop_id_grafo, length=distancia_metros, tempo_dinamico=tempo_caminhada, modal='caminhada')
    graph.add_edge(stop_id_grafo, no_rua, length=distancia_metros, tempo_dinamico=tempo_caminhada, modal='caminhada')

print(f"{len(stop_ids)} paradas integradas! As arestas de caminhada foram criadas com sucesso.")    

# ==========================================
# 8.5. CAMADA DE PEDESTRES (BIDIRECIONAL)
# ==========================================
print("\n8.5. Duplicando malha viária para pedestres (ignorando contramão)...")

velocidade_caminhada_ms = 1.2 # ~4.3 km/h
arestas_rua = list(graph.edges(keys=True, data=True))

for u, v, key, data in arestas_rua:
    if data.get('modal') not in ['onibus', 'caminhada', 'embarque', 'desembarque']:
        # Marca a original como carro
        data['modal'] = 'carro/rua' 
        
        distancia = data.get('length', 1)
        tempo_pedestre = distancia / velocidade_caminhada_ms
        
        # O SEGREDO 2: Pedestres andam nos dois sentidos da calçada!
        # Sem isso, vias de mão única travam o usuário.
        graph.add_edge(u, v, length=distancia, tempo_dinamico=tempo_pedestre, modal='pedestre/calcada')
        graph.add_edge(v, u, length=distancia, tempo_dinamico=tempo_pedestre, modal='pedestre/calcada')

print("Camada de pedestres bidirecional criada!")

# ==========================================
# 9. ADICIONANDO ROTAS COM EMBARQUE E TARIFA
# ==========================================
print("\n9. Lendo itinerários e modelando transbordos e tarifas (Grafo Expandido)...")
file_stop_times = 'stop_times.txt'

try:
    df_st = pd.read_csv(file_stop_times)
    
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
    
    # Conjuntos para garantir que só cobramos o embarque/desembarque uma vez por parada/viagem
    set_embarques = set()
    set_desembarques = set()
    conexoes_adicionadas = 0
    
    tarifa_onibus = 4.10 # Valor do Anel A
    tempo_espera_padrao = 300 # 5 minutos (300 segundos) de penalidade aguardando na parada
    
    for row in df_edges_filtrado.itertuples():
        stop_fisico_origem = f"stop_{int(row.stop_id)}"
        stop_fisico_destino = f"stop_{int(row.next_stop_id)}"
        
        # Nós "virtuais" exclusivos para a pessoa dentro deste ônibus específico
        no_viagem_origem = f"{stop_fisico_origem}_{row.trip_id}"
        no_viagem_destino = f"{stop_fisico_destino}_{row.trip_id}"
        
        tempo_viagem_segundos = row.next_arrival_sec - row.arrival_sec
        if tempo_viagem_segundos <= 0: tempo_viagem_segundos = 60
        
        # ========================================================
        # A CORREÇÃO: Pegar as coordenadas X e Y da parada física
        # ========================================================
        lon_origem = graph.nodes[stop_fisico_origem]['x']
        lat_origem = graph.nodes[stop_fisico_origem]['y']
        
        lon_destino = graph.nodes[stop_fisico_destino]['x']
        lat_destino = graph.nodes[stop_fisico_destino]['y']
            
        # 1. ARESTA DE EMBARQUE (Paga a tarifa e espera)
        if no_viagem_origem not in set_embarques:
            # Cria o nó virtual com as coordenadas ANTES de criar a aresta
            graph.add_node(no_viagem_origem, x=lon_origem, y=lat_origem, tipo='virtual_embarque')
            
            graph.add_edge(stop_fisico_origem, no_viagem_origem, 
                           tempo_dinamico=tempo_espera_padrao, custo_financeiro=tarifa_onibus, 
                           modal='embarque', trip_id=row.trip_id)
            set_embarques.add(no_viagem_origem)
            
        # 2. ARESTA DE DESEMBARQUE (Desce de graça e instantaneamente)
        if no_viagem_destino not in set_desembarques:
            # Cria o nó virtual com as coordenadas
            graph.add_node(no_viagem_destino, x=lon_destino, y=lat_destino, tipo='virtual_desembarque')
            
            graph.add_edge(no_viagem_destino, stop_fisico_destino, 
                           tempo_dinamico=0, custo_financeiro=0.0, 
                           modal='desembarque', trip_id=row.trip_id)
            set_desembarques.add(no_viagem_destino)

        # 3. ARESTA DE VIAGEM (O ônibus andando, já pago)
        graph.add_edge(no_viagem_origem, no_viagem_destino, 
                       tempo_dinamico=tempo_viagem_segundos, custo_financeiro=0.0, 
                       modal='onibus', trip_id=row.trip_id)
        conexoes_adicionadas += 1

    print(f"Sucesso! {conexoes_adicionadas} arestas de ônibus foram injetadas no grafo.")
except Exception as e:
    print(f"Erro: {e}")

# ==========================================
# 9.5. MAPEAMENTO DE NOMES DAS LINHAS DE ÔNIBUS (GTFS)
# ==========================================
print("\n9.5. Carregando os nomes reais das linhas (trips.txt e routes.txt)...")

mapa_linhas = {} # Dicionário de tradução rápida: {trip_id: "Nome da Linha"}

try:
    # Lemos apenas as colunas necessárias para poupar memória RAM
    df_trips = pd.read_csv('trips.txt', usecols=['trip_id', 'route_id'])
    df_routes = pd.read_csv('routes.txt', usecols=['route_id', 'route_short_name', 'route_long_name'])
    
    # Fazemos um "JOIN" (Merge) dos dois DataFrames usando o route_id como chave
    df_linhas_nomes = pd.merge(df_trips, df_routes, on='route_id')
    
    # Preenchemos o dicionário iterando rapidamente
    for row in df_linhas_nomes.itertuples():
        # Exemplo de formatação: "195 - RECIFE / PORTO DE GALINHAS"
        # Tratamos o preenchimento caso o nome curto ou longo venha vazio (NaN)
        curto = str(row.route_short_name) if pd.notna(row.route_short_name) else ""
        longo = str(row.route_long_name) if pd.notna(row.route_long_name) else ""
        
        mapa_linhas[row.trip_id] = f"{curto} - {longo}".strip(" -")
        
    print(f"Sucesso! Dicionário de rotas criado com {len(df_routes)} linhas de autocarro identificadas.")

except FileNotFoundError as e:
    print(f"Aviso: Ficheiro não encontrado ({e.filename}). O itinerário exibirá os IDs originais.")

# ==========================================
# 10. OTIMIZAÇÃO: CORREÇÃO DO MULTIDIGRAPH
# ==========================================
print("\n10. Calculando a melhor rota (Equilíbrio entre Tempo e Tarifa)...")

no_origem = ox.distance.nearest_nodes(graph, X=-34.88269, Y=-8.06374) 
no_destino = ox.distance.nearest_nodes(graph, X=-34.90017, Y=-8.11782)

arestas_tp = [(u, v, k) for u, v, k, d in graph.edges(keys=True, data=True) if d.get('modal') != 'carro/rua']
grafo_transporte = graph.edge_subgraph(arestas_tp)

# 1. Função auxiliar que calcula a Fadiga e o Custo de uma ÚNICA aresta
def calcular_peso_aresta(atributos):
    tempo = atributos.get('tempo_dinamico', 0)
    modal = atributos.get('modal', '')
    
    peso = tempo
    # Penalidade por cansaço físico
    if modal in ['pedestre/calcada', 'caminhada']:
        peso = tempo * 3.5 
    # Penalidade por quebra de conforto (troca de ônibus)
    elif modal == 'embarque':
        peso += 720 
        
    return peso

# 2. A Correção do MultiDiGraph: O Dijkstra chama esta função
def peso_multiobjetivo(u, v, d):
    # 'd' é um dicionário com várias arestas paralelas. 
    # Avaliamos todas e retornamos a que tiver o menor peso (menor dor).
    return min(calcular_peso_aresta(attr) for attr in d.values())

try:
    # Roda o Dijkstra com a nova lógica
    rota_tp = nx.shortest_path(grafo_transporte, source=no_origem, target=no_destino, weight=peso_multiobjetivo)

    print(f"\n=> ROTA MULTIMODAL REALISTA ENCONTRADA!")
    print("-" * 60)
    print("DETALHAMENTO DO ITINERÁRIO:")

    modal_atual = None
    tempo_etapa = 0
    tempo_total_real_segundos = 0
    onibus_utilizados = 0
    
    for i in range(len(rota_tp) - 1):
        u = rota_tp[i]
        v = rota_tp[i+1]
        
        arestas = grafo_transporte[u][v]
        # Pega exatamente a aresta que o Dijkstra escolheu usar
        aresta_escolhida = min(arestas.values(), key=calcular_peso_aresta)
        
        modal_aresta = aresta_escolhida.get('modal', 'desconhecido')
        tempo_aresta = aresta_escolhida.get('tempo_dinamico', 0)
        
        tempo_total_real_segundos += tempo_aresta
        
        if modal_aresta == 'embarque':
            id_viagem = aresta_escolhida.get('trip_id')
            # Busca no nosso dicionário O(1). Se não existir, mostra o ID original por segurança
            nome_linha_real = mapa_linhas.get(id_viagem, id_viagem)
            
            nome_modal = f"EMBARQUE (Linha: {nome_linha_real})"
            onibus_utilizados += 1
        elif modal_aresta == 'onibus':
            nome_modal = f"ÔNIBUS (Em trânsito)"
        elif modal_aresta == 'desembarque':
            continue 
        elif modal_aresta == 'caminhada':
            nome_modal = "PEDESTRE (Indo/Voltando da parada)"
        elif modal_aresta == 'pedestre/calcada':
            nome_modal = "PEDESTRE (Andando na calçada)"
            
        if nome_modal == modal_atual:
            tempo_etapa += tempo_aresta
        else:
            if modal_atual is not None:
                print(f" -> {modal_atual}: {tempo_etapa / 60:.1f} minutos")
            modal_atual = nome_modal
            tempo_etapa = tempo_aresta

    if modal_atual is not None:
        print(f" -> {modal_atual}: {tempo_etapa / 60:.1f} minutos")
        
    custo_final = 4.10 if onibus_utilizados > 0 else 0.0

    print("-" * 60)
    print(f"TEMPO TOTAL DA VIAGEM: {tempo_total_real_segundos / 60:.1f} minutos")
    print(f"CUSTO FINANCEIRO: R$ {custo_final:.2f} (Considerando Integração VEM)")
    print("-" * 60)

except nx.NetworkXNoPath:
    print("Não foi possível encontrar uma rota válida.")