import osmnx as ox
import pandas as pd
import warnings
import networkx as nx

# Ignora warnings de depreciação do Pandas
warnings.filterwarnings('ignore')

# ==========================================
# 1. EXTRAÇÃO DO GRAFO DA MALHA VIÁRIA (OSM)
# ==========================================
print("1. Baixando o grafo do Recife... (Isso pode levar alguns segundos)")
coords_origem = (-8.06374, -34.88269)  # Cine São Luiz (Centro)
coords_destino = (-8.11782, -34.90017) # Faculdade Nova Roma (Boa Viagem)
# O modo 'drive' baixa a malha viária para veículos
graph = ox.graph_from_point(coords_origem, dist=8000, network_type='drive')
print("Grafo viário estruturado com sucesso!\n")

# ==========================================
# 2. PROCESSAMENTO DAS VELOCIDADES (CTTU)
# ==========================================
print("2. Processando dados de velocidade da CTTU...")
file_velocidade = 'resources_c2d9c049-6511-4dc4-9691-b76a43e4f7e3_fotossensores-2025-dezembro-quantitativo-das-vias-por-velocidade-media.csv'
df_vel = pd.read_csv(file_velocidade, sep=';')

# Dicionário de pesos para calcular a velocidade média
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

# Filtramos apenas os radares e as médias (Vamos pegar apenas a hora = 8 como exemplo de pico da manhã)
df_vel_pico_manha = df_vel[df_vel['hora'] == 8].groupby('equipamento')['velocidade_media_estimada'].mean().reset_index()
print("Velocidades processadas.\n")

# ==========================================
# 3. CRUZAMENTO COM A LOCALIZAÇÃO (LAT/LON)
# ==========================================
print("3. Cruzando dados com a localização dos equipamentos...")
file_localizacao = 'resources_36c2b47b-f439-4895-8b65-3f3dda36a4a7_lista-de-equipamentos-de-fiscalizacao-de-transito.csv'

# Lê o arquivo que você encontrou (pulando linhas corrompidas, se houver)
df_loc = pd.read_csv(file_localizacao, sep=';', encoding='latin-1', on_bad_lines='skip')

# Limpa e padroniza a coluna para que FC004 vire FC004REC
df_loc['identificacao_equipamento'] = df_loc['identificacao_equipamento'].astype(str).str.strip()
df_loc_fc = df_loc[df_loc['identificacao_equipamento'].str.startswith('FC', na=False)].copy()
df_loc_fc['equipamento'] = df_loc_fc['identificacao_equipamento'] + 'REC'

# Faz o MERGE (Junta a velocidade com a Latitude e Longitude)
df_radares_no_mapa = pd.merge(df_vel_pico_manha, df_loc_fc[['equipamento', 'latitude', 'longitude']], on='equipamento', how='inner')

print("Radares mapeados com sucesso! Exemplo:")
print(df_radares_no_mapa.head())

# ==========================================
# 4. INJETANDO PESOS DINÂMICOS NO GRAFO
# ==========================================
print("4. Mapeando radares para as ruas (arestas) do grafo...")

# 4.1. Definir um "tempo base" para todas as ruas que NÃO têm radar
# Vamos assumir uma velocidade padrão de 40 km/h (convertida para metros/segundo)
velocidade_padrao_ms = 40 / 3.6 

for u, v, key, data in graph.edges(keys=True, data=True):
    # O OSMnx já traz o tamanho da rua em metros no atributo 'length'
    distancia_metros = data.get('length', 1) 
    
    # Adicionamos o atributo 'tempo_dinamico' na aresta (em segundos)
    data['tempo_dinamico'] = distancia_metros / velocidade_padrao_ms

# 4.2. Extrair as coordenadas dos radares para o formato que o OSMnx entende (X, Y)
# Atenção: O OSMnx pede primeiro a Longitude (X), depois a Latitude (Y)
lons = df_radares_no_mapa['longitude'].tolist()
lats = df_radares_no_mapa['latitude'].tolist()

# 4.3. Encontrar a aresta mais próxima de cada radar
# Isso retorna uma lista de identificadores das ruas (nó origem, nó destino, chave)
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

# 5.1. Encontrar os nós (cruzamentos) mais próximos da nossa origem e destino
# Atenção: O OSMnx pede X (Longitude) e Y (Latitude)
# Cine São Luiz (s) e Faculdade Nova Roma (t)
no_origem = ox.distance.nearest_nodes(graph, X=-34.88269, Y=-8.06374) 
no_destino = ox.distance.nearest_nodes(graph, X=-34.90017, Y=-8.11782)

# 5.2. Rota 1: Menor Distância Física (Eficiência Espacial)
# Usa o atributo 'length' (tamanho da rua em metros) nativo do OSMnx
rota_distancia = nx.shortest_path(graph, source=no_origem, target=no_destino, weight='length')

# 5.3. Rota 2: Menor Tempo (Eficiência Temporal com pesos dinâmicos da CTTU)
# Usa o atributo 'tempo_dinamico' que criamos no passo 4
rota_tempo = nx.shortest_path(graph, source=no_origem, target=no_destino, weight='tempo_dinamico')

# 5.4. Calcular os custos finais para comparar
tempo_total_segundos = nx.shortest_path_length(graph, source=no_origem, target=no_destino, weight='tempo_dinamico')
distancia_total_metros = nx.shortest_path_length(graph, source=no_origem, target=no_destino, weight='length')

print(f"-> Rota mais rápida calculada! Tempo estimado: {tempo_total_segundos / 60:.2f} minutos.")
print(f"-> Rota mais curta calculada! Distância total: {distancia_total_metros / 1000:.2f} km.")

# ==========================================
# 6. VISUALIZAÇÃO CARTOGRÁFICA
# ==========================================
print("\n6. Gerando a visualização no mapa...")

# Se as rotas forem diferentes, o algoritmo provou seu valor desviando do trânsito!
if rota_distancia != rota_tempo:
    print("O trânsito alterou a rota ideal! Desenhando ambas no mapa...")
    # Plota as duas rotas: Vermelha (Tempo/Dinâmica) e Azul (Distância/Estática)
    fig, ax = ox.plot_graph_routes(
        graph, 
        routes=[rota_tempo, rota_distancia], 
        route_colors=['r', 'b'], 
        route_linewidths=[4, 2], 
        node_size=0
    )
else:
    print("A rota mais curta também é a mais rápida neste horário.")
    fig, ax = ox.plot_graph_route(graph, rota_tempo, route_color='r', route_linewidth=4, node_size=0)
    
# O comando de plotagem acima já executa o plt.show() internamente.