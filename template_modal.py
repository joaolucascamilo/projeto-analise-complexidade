# =============================================================================
# TEMPLATE_MODAL.PY — Modelo base para implementação de um novo modal
# =============================================================================
# INSTRUÇÕES PARA O MEMBRO DO GRUPO:
#
#   1. Copie este arquivo e renomeie para o seu modal:
#         modal_carro.py       ← carro (veículo particular)
#         modal_onibus.py      ← ônibus / transporte público
#         modal_bicicleta.py   ← bicicleta
#         modal_pedestre.py    ← caminhada / a pé
#         modal_brt.py         ← BRT / Metrô
#
#   2. Preencha as constantes da seção "PARÂMETROS DO MODAL"
#
#   3. Implemente a lógica de pesos na função _calcular_peso_aresta()
#
#   4. Execute hub_rotas_multimodal.py — seu modal aparece automaticamente
#      no painel do mapa sem precisar alterar mais nada.
#
# CONTRATO:
#   A única obrigação é que a função calcular() retorne um ModalResult.
#   Veja o dataclass ModalResult em hub_rotas_multimodal.py para os campos.
# =============================================================================

import networkx as nx
import osmnx as ox
import numpy as np
from hub_rotas_multimodal import ModalResult

# ==============================================================================
# PARÂMETROS DO MODAL  ← EDITE AQUI
# ==============================================================================

MODAL_ID    = 'car'          # id deve coincidir com MODAIS_REGISTRADOS no hub
MODAL_NOME  = 'Carro'

# Física / economia do modal
VELOCIDADE_BASE_KMH   = 45.0   # velocidade de cruzeiro urbano
CONSUMO_LITROS_100KM  = 10.5   # litros por 100 km (0 para bicicleta/pedestre)
PRECO_COMBUSTIVEL_BRL = 6.20   # R$/litro (gasolina)
MANUTENCAO_POR_KM     = 0.18   # R$/km (amortização, pneu, óleo)
EMISSAO_CO2_G_KM      = 120.0  # gCO₂/km (0 para bike/pedestre)
INDICE_RISCO          = 0.72   # 0 = sem risco, 1 = máximo risco

# Penalidades de tempo para fatores dinâmicos (frações aditivas)
PEN_CHUVA  = 0.20  # +20% no tempo em caso de chuva
PEN_PICO   = 0.35  # +35% no tempo em horário de pico
PEN_EVENTO = 0.50  # +50% no tempo em evento (jogo, carnaval, etc.)

# Horário de pico usado para filtrar dados CTTU (hora inteira)
HORA_PICO  = 8     # 8 = pico da manhã  |  17 = pico da tarde

# Peso Dijkstra principal para este modal
# Opções: 'tempo_dinamico' | 'length' | qualquer atributo custom que você criar
PESO_DIJKSTRA_PRINCIPAL = 'tempo_dinamico'


# ==============================================================================
# LÓGICA DE PESO — personalize para o seu modal
# ==============================================================================

def _preparar_grafo(graph, df_radares):
    """
    Adiciona ou recalcula atributos de aresta específicos para este modal.
    Chamada internamente por calcular().
    """
    vel_base_ms = VELOCIDADE_BASE_KMH / 3.6

    for u, v, key, data in graph.edges(keys=True, data=True):
        dist_m = data.get('length', 1.0)

        # ── velocidade base ──────────────────────────────────────────────────
        maxspeed = data.get('maxspeed', None)
        if isinstance(maxspeed, list):
            maxspeed = maxspeed[0]
        try:
            vel_via = float(str(maxspeed).split()[0]) if maxspeed else VELOCIDADE_BASE_KMH
        except (ValueError, AttributeError):
            vel_via = VELOCIDADE_BASE_KMH

        vel_ms = min(vel_via, VELOCIDADE_BASE_KMH) / 3.6  # não ultrapassa base
        data['tempo_modal'] = dist_m / vel_ms

    # Injeta velocidades reais CTTU nas arestas mais próximas dos sensores
    df = df_radares.copy()
    df['latitude']  = df['latitude'].astype(float)
    df['longitude'] = df['longitude'].astype(float)
    df = df.dropna(subset=['latitude', 'longitude'])

    arestas = ox.distance.nearest_edges(
        graph, X=df['longitude'].tolist(), Y=df['latitude'].tolist()
    )
    for idx, (u, v, key) in enumerate(arestas):
        vel_kmh  = max(df.iloc[idx]['velocidade_media'], 1.0)
        dist_m   = graph[u][v][key].get('length', 1.0)
        # -----------------------------------------------------------------
        # ▼ PERSONALIZE AQUI: como o seu modal reage ao trânsito medido?
        # -----------------------------------------------------------------
        # Exemplo carro: usa a velocidade real diretamente
        vel_efetiva = vel_kmh
        # Exemplo moto:  aplica bônus de filtragem
        #   vel_efetiva = max(vel_kmh / 0.85, 30.0) if vel_kmh < 30 else vel_kmh
        # Exemplo bus:   usa velocidade reduzida (paradas + semáforos)
        #   vel_efetiva = vel_kmh * 0.70
        # -----------------------------------------------------------------
        graph[u][v][key]['tempo_modal'] = dist_m / (vel_efetiva / 3.6)

    return graph


def _calcular_custo_aresta(dist_m: float) -> float:
    """Custo financeiro em R$ para percorrer dist_m metros com este modal."""
    km = dist_m / 1000
    return km * ((CONSUMO_LITROS_100KM / 100) * PRECO_COMBUSTIVEL_BRL
                 + MANUTENCAO_POR_KM)


# ==============================================================================
# FUNÇÃO PRINCIPAL — NÃO RENOMEIE (o hub chama exatamente "calcular")
# ==============================================================================

def calcular(graph, no_origem: int, no_destino: int,
             df_radares, coords_origem, coords_destino, **kwargs) -> ModalResult:
    """
    Calcula a melhor rota para este modal e retorna um ModalResult.

    Parâmetros
    ----------
    graph         : grafo OSMnx já baixado e com pesos base injetados
    no_origem     : node id do nó de origem no grafo
    no_destino    : node id do nó de destino no grafo
    df_radares    : DataFrame CTTU com colunas [equipamento, velocidade_media,
                    latitude, longitude]
    coords_origem : tuple (lat, lon) — ponto de origem original
    coords_destino: tuple (lat, lon) — ponto de destino original
    """

    # ── 1. Prepara pesos específicos do modal ─────────────────────────────────
    graph = _preparar_grafo(graph, df_radares)

    # ── 2. Rota principal (menor tempo com dados reais CTTU) ──────────────────
    rota_principal = nx.shortest_path(
        graph, source=no_origem, target=no_destino,
        weight='tempo_modal'
    )

    # ── 3. Rotas alternativas por prioridade ──────────────────────────────────
    rota_distancia = nx.shortest_path(
        graph, source=no_origem, target=no_destino,
        weight='length'
    )
    # Para "economia": menor custo financeiro por aresta
    # Para "segurança": pode usar índice de risco calculado via CTTU
    # Se não tiver implementado, use a rota principal como fallback
    rota_economia  = rota_principal   # ← substitua pelo seu cálculo
    rota_seguranca = rota_distancia   # ← substitua pelo seu cálculo

    # ── 4. Acumula métricas ───────────────────────────────────────────────────
    def acumular(rota):
        t_seg, dist_m, custo = 0.0, 0.0, 0.0
        for u, v in zip(rota[:-1], rota[1:]):
            edata = graph.get_edge_data(u, v)
            if not edata:
                continue
            data  = min(edata.values(), key=lambda d: d.get('tempo_modal', 1e9))
            dm    = data.get('length', 0)
            t_seg += data.get('tempo_modal', 0)
            dist_m += dm
            custo  += _calcular_custo_aresta(dm)
        return t_seg, dist_m, custo

    t_p, dist_p, custo_p = acumular(rota_principal)
    _, dist_d, custo_d   = acumular(rota_distancia)
    _, dist_e, custo_e   = acumular(rota_economia)
    _, dist_s, custo_s   = acumular(rota_seguranca)

    vel_media = (dist_p / 1000) / max(t_p / 3600, 0.001)

    # ── 5. Monta alternativas por prioridade ──────────────────────────────────
    def _alt(rota, dist_m, custo_brl, nome, desc):
        return ModalResult(
            modal_id=MODAL_ID, rota_nos=rota,
            tempo_min=round(nx.shortest_path_length(
                graph, source=no_origem, target=no_destino,
                weight='tempo_modal') / 60, 1),
            distancia_km=round(dist_m / 1000, 2),
            custo_brl=round(custo_brl, 2),
            emissao_co2_g=round((dist_m / 1000) * EMISSAO_CO2_G_KM, 1),
            risco=INDICE_RISCO,
            nome_rota=nome, descricao=desc,
        )

    alternativas = {
        'distancia': _alt(rota_distancia, dist_d, custo_d,
                          'Rota mais curta', 'menor distância'),
        'economia' : _alt(rota_economia,  dist_e, custo_e,
                          'Rota econômica', 'menor consumo'),
        'seguranca': _alt(rota_seguranca, dist_s, custo_s,
                          'Rota segura', 'menor índice de risco'),
    }

    # ── 6. Retorna ModalResult ────────────────────────────────────────────────
    return ModalResult(
        modal_id     = MODAL_ID,
        rota_nos     = rota_principal,
        tempo_min    = round(t_p / 60, 1),
        distancia_km = round(dist_p / 1000, 2),
        custo_brl    = round(custo_p, 2),
        emissao_co2_g= round((dist_p / 1000) * EMISSAO_CO2_G_KM, 1),
        risco        = INDICE_RISCO,
        vel_media_kmh= round(vel_media, 1),
        congestionamento_pct = 65,   # ← implemente com dados CTTU se desejar
        pen_chuva    = PEN_CHUVA,
        pen_pico     = PEN_PICO,
        pen_evento   = PEN_EVENTO,
        nome_rota    = 'PE-009',     # ← substitua pelo nome real da rota
        descricao    = 'mais rápida (Dijkstra tempo)',
        observacao   = f'Vel. média {vel_media:.0f} km/h · CTTU dez/2025',
        alternativas = alternativas,
    )
