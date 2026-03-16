import osmnx as ox
import pandas as pd
import warnings
import networkx as nx
import folium  

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