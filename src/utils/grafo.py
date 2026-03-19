"""
Utilitários para download e configuração dos grafos da malha viária.

Centraliza a criação dos grafos do OSMnx e a injeção dos pesos
dinâmicos com base nos dados de velocidade da CTTU.
"""

import warnings
import osmnx as ox
import pandas as pd

# Suprime avisos desnecessários do pandas
warnings.filterwarnings('ignore')

# Coordenadas fixas do percurso estudado
COORDS_ORIGEM  = (-8.06374, -34.88269)  # Cine São Luiz (Centro)
COORDS_DESTINO = (-8.11782, -34.90017)  # Faculdade Nova Roma (Boa Viagem)

# Velocidades padrão por modal (km/h)
VELOCIDADE_PADRAO_CARRO_KMH     = 40
VELOCIDADE_PADRAO_MOTO_KMH      = 50
VELOCIDADE_PADRAO_BICICLETA_KMH = 20
VELOCIDADE_PADRAO_CAMINHADA_KMH = 5


def baixar_grafo_carro(coords_origem=COORDS_ORIGEM, dist=8000):
    """
    Baixa o grafo viário para carros a partir do OpenStreetMap.

    Parâmetros:
        coords_origem: tupla (lat, lon) do ponto central de busca
        dist: raio em metros ao redor da origem

    Retorna:
        Grafo MultiDiGraph do OSMnx com ruas para veículos
    """
    print("Baixando grafo viário (carros) do OpenStreetMap...")
    graph = ox.graph_from_point(coords_origem, dist=dist, network_type='drive')
    print("Grafo viário carregado com sucesso.\n")
    return graph


def baixar_grafo_pedestre(coords_origem=COORDS_ORIGEM, dist=8000):
    """
    Baixa o grafo de pedestres a partir do OpenStreetMap.
    Usado tanto para caminhada quanto para bicicleta.

    Parâmetros:
        coords_origem: tupla (lat, lon) do ponto central de busca
        dist: raio em metros ao redor da origem

    Retorna:
        Grafo MultiDiGraph do OSMnx com caminhos para pedestres
    """
    print("Baixando grafo de pedestres do OpenStreetMap...")
    graph = ox.graph_from_point(coords_origem, dist=dist, network_type='walk')
    print("Grafo de pedestres carregado com sucesso.\n")
    return graph


def classificar_congestionamento(velocidade_kmh):
    """
    Classifica o nível de congestionamento com base na velocidade medida.

    A função de custo é: tempo = distância / velocidade(congestionamento)
    Quanto menor a velocidade, maior o tempo de travessia da aresta.

    Categorias:
        leve:   velocidade >= 50 km/h  -> tráfego fluindo bem
        médio:  30 ≤ velocidade < 50   -> tráfego moderado
        pesado: velocidade < 30 km/h   -> tráfego intenso / congestionado

    Parâmetros:
        velocidade_kmh: velocidade média medida no trecho (km/h)

    Retorna:
        String: 'leve', 'medio' ou 'pesado'
    """
    if velocidade_kmh >= 50:
        return 'leve'
    elif velocidade_kmh >= 30:
        return 'medio'
    else:
        return 'pesado'


def processar_velocidades_cttu(arquivo_velocidade, arquivo_localizacao, hora=8):
    """
    Lê os arquivos CSV da CTTU e calcula a velocidade média estimada
    por equipamento em um horário específico.

    Parâmetros:
        arquivo_velocidade:  caminho do CSV com contagens por faixa de velocidade
        arquivo_localizacao: caminho do CSV com lat/lon dos equipamentos
        hora:                hora do dia a ser usada (0-23); padrão 8 (pico manhã)

    Retorna:
        DataFrame com colunas [equipamento, velocidade_media_estimada, latitude, longitude,
                                nivel_congestionamento]
    """
    # Pesos do ponto médio de cada faixa de velocidade
    pesos_velocidade = {
        'qtd_0a10km':      5.0,  'qtd_11a20km': 15.5, 'qtd_21a30km': 25.5,
        'qtd_31a40km':    35.5,  'qtd_41a50km': 45.5, 'qtd_51a60km': 55.5,
        'qtd_61a70km':    65.5,  'qtd_71a80km': 75.5, 'qtd_81a90km': 85.5,
        'qtd_91a100km':   95.5,  'qtd_acimade100km': 105.0
    }

    # Lê o arquivo de velocidades
    df_vel = pd.read_csv(arquivo_velocidade, sep=';')

    # Calcula a velocidade média ponderada por veículo
    colunas_qtd = list(pesos_velocidade.keys())
    df_vel['total_veiculos'] = df_vel[colunas_qtd].sum(axis=1)
    soma_velocidades = sum(df_vel[col] * peso for col, peso in pesos_velocidade.items())
    df_vel['velocidade_media_estimada'] = soma_velocidades / df_vel['total_veiculos'].replace(0, 1)

    # Filtra a hora escolhida e agrupa por equipamento
    df_hora = (
        df_vel[df_vel['hora'] == hora]
        .groupby('equipamento')['velocidade_media_estimada']
        .mean()
        .reset_index()
    )

    # Lê a localização geográfica dos equipamentos
    df_loc = pd.read_csv(arquivo_localizacao, sep=';', encoding='latin-1', on_bad_lines='skip')
    df_loc['identificacao_equipamento'] = df_loc['identificacao_equipamento'].astype(str).str.strip()

    # Filtra apenas equipamentos do tipo fotossensor (prefixo 'FC') e normaliza o ID
    df_loc_fc = df_loc[df_loc['identificacao_equipamento'].str.startswith('FC', na=False)].copy()
    df_loc_fc['equipamento'] = df_loc_fc['identificacao_equipamento'] + 'REC'

    # Junta velocidades com as coordenadas geográficas
    df_radares = pd.merge(
        df_hora,
        df_loc_fc[['equipamento', 'latitude', 'longitude']],
        on='equipamento',
        how='inner'
    )

    # Classifica o nível de congestionamento de cada radar
    df_radares['nivel_congestionamento'] = df_radares['velocidade_media_estimada'].apply(
        classificar_congestionamento
    )

    # Resumo dos níveis de congestionamento encontrados
    contagem = df_radares['nivel_congestionamento'].value_counts().to_dict()
    print(
        f"Velocidades CTTU (hora={hora}h) processadas. "
        f"{len(df_radares)} radares: "
        f"leve={contagem.get('leve', 0)}, "
        f"médio={contagem.get('medio', 0)}, "
        f"pesado={contagem.get('pesado', 0)}.\n"
    )
    return df_radares


def injetar_pesos_carro(graph, df_radares):
    """
    Adiciona o atributo 'tempo_dinamico' em cada aresta do grafo de carros.

    Primeiro define um tempo base com velocidade padrão, depois sobrescreve
    as arestas próximas aos radares com a velocidade real da CTTU.

    Parâmetros:
        graph:      grafo MultiDiGraph de carros
        df_radares: DataFrame com velocidades e coordenadas dos radares

    Retorna:
        graph com atributo 'tempo_dinamico' em todas as arestas (segundos)
    """
    velocidade_padrao_ms = VELOCIDADE_PADRAO_CARRO_KMH / 3.6

    # Define tempo base em todas as arestas
    for u, v, key, data in graph.edges(keys=True, data=True):
        distancia = data.get('length', 1)
        data['tempo_dinamico'] = distancia / velocidade_padrao_ms

    # Localiza a aresta mais próxima de cada radar
    lons = df_radares['longitude'].tolist()
    lats = df_radares['latitude'].tolist()
    arestas_proximas = ox.distance.nearest_edges(graph, X=lons, Y=lats)

    # Sobrescreve o tempo das arestas com o dado real da CTTU
    for idx, (u, v, key) in enumerate(arestas_proximas):
        velocidade_kmh = df_radares.iloc[idx]['velocidade_media_estimada']

        # Evita divisão por zero em vias completamente paradas
        if velocidade_kmh < 1:
            velocidade_kmh = 1.0

        velocidade_ms = velocidade_kmh / 3.6
        distancia = graph[u][v][key].get('length', 1)
        graph[u][v][key]['tempo_dinamico']         = distancia / velocidade_ms
        graph[u][v][key]['nivel_congestionamento'] = classificar_congestionamento(velocidade_kmh)

    print("Pesos dinâmicos da CTTU injetados no grafo de carros.\n")
    return graph


def injetar_tempo_caminhada(graph_walk):
    """
    Adiciona o atributo 'tempo_caminhada' em cada aresta do grafo de pedestres.

    Parâmetros:
        graph_walk: grafo MultiDiGraph de pedestres

    Retorna:
        graph_walk com atributo 'tempo_caminhada' em todas as arestas (segundos)
    """
    velocidade_ms = VELOCIDADE_PADRAO_CAMINHADA_KMH / 3.6
    for u, v, key, data in graph_walk.edges(keys=True, data=True):
        distancia = data.get('length', 1)
        data['tempo_caminhada'] = distancia / velocidade_ms
    return graph_walk


def injetar_tempo_bicicleta(graph_bike):
    """
    Adiciona o atributo 'tempo_bicicleta' em cada aresta do grafo de bicicleta.

    Parâmetros:
        graph_bike: grafo MultiDiGraph (cópia do grafo de pedestres)

    Retorna:
        graph_bike com atributo 'tempo_bicicleta' em todas as arestas (segundos)
    """
    velocidade_ms = VELOCIDADE_PADRAO_BICICLETA_KMH / 3.6
    for u, v, key, data in graph_bike.edges(keys=True, data=True):
        distancia = data.get('length', 1)
        data['tempo_bicicleta'] = distancia / velocidade_ms
    return graph_bike
