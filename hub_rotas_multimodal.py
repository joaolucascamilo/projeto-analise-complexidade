# =============================================================================
# HUB_ROTAS_MULTIMODAL.PY
# Orquestrador multimodal — cada membro do grupo implementa seu próprio módulo
# de modal e o registra aqui. O hub calcula todas as rotas e gera o mapa com
# o painel interativo refletindo valores REAIS do Dijkstra por modal.
#
# COMO ADICIONAR UM NOVO MODAL:
#   1. Crie seu arquivo (ex: modal_bicicleta.py)
#   2. Implemente a função:
#          def calcular(graph, no_origem, no_destino, **kwargs) -> ModalResult
#   3. Registre em MODAIS_REGISTRADOS abaixo com um dict de configuração
#   4. Rode hub_rotas_multimodal.py — seu modal aparece automaticamente no mapa
#
# ARQUITETURA:
#   hub_rotas_multimodal.py   ← este arquivo (orquestrador)
#   modal_carro.py            ← impl. do membro responsável por carro
#   rota_moto_dijkstra.py     ← impl. já existente (moto)
#   modal_onibus.py           ← impl. do membro responsável por ônibus
#   modal_bicicleta.py        ← impl. do membro responsável por bicicleta
#   modal_brt.py              ← impl. do membro responsável por BRT/Metrô
#   modal_pedestre.py         ← impl. do membro responsável por pedestre
# =============================================================================

import osmnx as ox
import pandas as pd
import networkx as nx
import folium
import warnings
import webbrowser
import importlib
import traceback
from dataclasses import dataclass, field
from typing import Optional

warnings.filterwarnings('ignore')

# ==============================================================================
# 0. CONFIGURAÇÃO GLOBAL
# ==============================================================================

COORDS_ORIGEM  = (-8.06374,  -34.88269)   # Cine São Luiz — Centro
COORDS_DESTINO = (-8.11782,  -34.90017)   # Faculdade Nova Roma — Boa Viagem

FILE_VELOCIDADE = (
    'resources_c2d9c049-6511-4dc4-9691-b76a43e4f7e3'
    '_fotossensores-2025-dezembro-quantitativo-das-vias-por-velocidade-media.csv'
)
FILE_LOCALIZACAO = (
    'resources_36c2b47b-f439-4895-8b65-3f3dda36a4a7'
    '_lista-de-equipamentos-de-fiscalizacao-de-transito.csv'
)

# ==============================================================================
# 1. CONTRATO DE INTERFACE — ModalResult
#    Todo módulo de modal DEVE retornar um objeto com estes campos.
#    Campos opcionais podem ficar como None — o hub usa fallbacks.
# ==============================================================================

@dataclass
class ModalResult:
    """
    Resultado padronizado que cada módulo de modal deve retornar.
    O hub usa esses dados para preencher o painel e colorir as rotas no mapa.
    """
    # ── Obrigatórios ──────────────────────────────────────────────────────────
    modal_id    : str          # 'car' | 'moto' | 'bus' | 'walk' | 'bike' | 'brt'
    rota_nos    : list         # lista de node-ids do grafo (caminho Dijkstra)
    tempo_min   : float        # duração total em minutos
    distancia_km: float        # distância total em km

    # ── Métricas econômicas/ambientais ────────────────────────────────────────
    custo_brl   : float = 0.0  # custo estimado em R$
    emissao_co2_g: float = 0.0 # emissão em gramas de CO₂
    risco       : float = 0.5  # índice de risco [0–1]

    # ── Metadados da rota ─────────────────────────────────────────────────────
    nome_rota   : str  = ''    # ex: 'PE-009'
    descricao   : str  = ''    # ex: 'mais rápida (Dijkstra tempo)'
    vel_media_kmh: float = 0.0 # velocidade média efetiva
    congestionamento_pct: float = 0.0

    # ── Penalidades dinâmicas (aplicadas pelo hub) ────────────────────────────
    # Fator multiplicador de tempo por fator ativo (chuva / pico / evento)
    pen_chuva   : float = 0.15  # +15% padrão
    pen_pico    : float = 0.20  # +20% padrão
    pen_evento  : float = 0.25  # +25% padrão

    # ── Observação livre ──────────────────────────────────────────────────────
    observacao  : str  = ''

    # ── Rotas alternativas (prioridade diferente) ─────────────────────────────
    # Se o módulo calcular múltiplas rotas, preencha aqui.
    # Estrutura: {prioridade: ModalResult}
    alternativas: dict = field(default_factory=dict)


# ==============================================================================
# 2. REGISTRO DE MODAIS
#    Adicione seu modal aqui. Se o módulo não existir ainda, o hub usa
#    um fallback com valores estimados e avisa no terminal.
# ==============================================================================

MODAIS_REGISTRADOS = {
    # ── id ──── módulo Python ────────── cor hex ── ícone SVG ──────────────────
    'car': {
        'modulo'   : 'modal_carro',          # arquivo modal_carro.py
        'label'    : 'Carro',
        'cor'      : '#378ADD',
        'peso_dash': None,                   # linha sólida
        'icon_svg' : (
            '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor"'
            ' stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M3.5 12h13M3 9l2-4h10l2 4v3H3V9z"/>'
            '<circle cx="6.5" cy="14" r="1.5" fill="currentColor" stroke="none"/>'
            '<circle cx="13.5" cy="14" r="1.5" fill="currentColor" stroke="none"/>'
            '</svg>'
        ),
        # Fallback enquanto modal_carro.py não existir
        'fallback' : dict(tempo_min=18, distancia_km=8.5, custo_brl=6.12,
                          emissao_co2_g=1020, risco=0.72, vel_media_kmh=45,
                          congestionamento_pct=65, pen_chuva=.20, pen_pico=.35,
                          pen_evento=.50, nome_rota='PE-009',
                          descricao='mais rápida (fallback)',
                          observacao='Vel. média 32 km/h no pico · CTTU dez/2025'),
    },
    'moto': {
        'modulo'   : 'rota_moto_dijkstra',   # arquivo já existente!
        'label'    : 'Moto',
        'cor'      : '#D85A30',
        'peso_dash': '8,5',
        'icon_svg' : (
            '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor"'
            ' stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="5" cy="13" r="2.5"/><circle cx="15" cy="13" r="2.5"/>'
            '<path d="M5 13l4-5 2.5 0L15 13M10 8l2-3"/>'
            '</svg>'
        ),
        'fallback' : dict(tempo_min=15, distancia_km=8.5, custo_brl=2.73,
                          emissao_co2_g=468, risco=0.85, vel_media_kmh=58,
                          congestionamento_pct=20, pen_chuva=.25, pen_pico=.10,
                          pen_evento=.15, nome_rota='PE-009 (moto)',
                          descricao='mais rápida (Dijkstra MDS)',
                          observacao='Filtragem entre faixas · ~33% mais rápido que carro'),
    },
    'bus': {
        'modulo'   : 'modal_onibus',
        'label'    : 'Ônibus',
        'cor'      : '#1D9E75',
        'peso_dash': '4,4',
        'icon_svg' : (
            '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor"'
            ' stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="3" y="4" width="14" height="9" rx="1.5"/>'
            '<path d="M3 8h14M7 4V3M13 4V3M6 13v1.5M14 13v1.5"/>'
            '<circle cx="6.5" cy="16" r="1" fill="currentColor" stroke="none"/>'
            '<circle cx="13.5" cy="16" r="1" fill="currentColor" stroke="none"/>'
            '</svg>'
        ),
        'fallback' : dict(tempo_min=34, distancia_km=10.2, custo_brl=4.80,
                          emissao_co2_g=275, risco=0.28, vel_media_kmh=30,
                          congestionamento_pct=40, pen_chuva=.15, pen_pico=.25,
                          pen_evento=.30, nome_rota='Linha Setúbal (Príncipe)',
                          descricao='mais rápida (fallback)',
                          observacao='Tarifa R$ 4,80 · integração BRT e metrô'),
    },
    'walk': {
        'modulo'   : 'modal_pedestre',
        'label'    : 'A pé',
        'cor'      : '#639922',
        'peso_dash': '3,3',
        'icon_svg' : (
            '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor"'
            ' stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="10" cy="3.5" r="1.5" fill="currentColor" stroke="none"/>'
            '<path d="M9 6l-2 5 2.5 1M11 6l2 3.5-2 2.5M7.5 17l1.5-5M12.5 17l-1.5-4.5"/>'
            '</svg>'
        ),
        'fallback' : dict(tempo_min=118, distancia_km=9.0, custo_brl=0,
                          emissao_co2_g=0, risco=0.10, vel_media_kmh=5,
                          congestionamento_pct=0, pen_chuva=.30, pen_pico=.00,
                          pen_evento=.00, nome_rota='Av. Domingos Ferreira',
                          descricao='sem custo (fallback)',
                          observacao='~120 min · calçadas e faixas de pedestres'),
    },
    'bike': {
        'modulo'   : 'modal_bicicleta',
        'label'    : 'Bicicleta',
        'cor'      : '#BA7517',
        'peso_dash': '6,3',
        'icon_svg' : (
            '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor"'
            ' stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="5" cy="13" r="3"/><circle cx="15" cy="13" r="3"/>'
            '<path d="M5 13l5.5-7 4.5 7M10.5 6h3.5"/>'
            '<circle cx="14" cy="6" r="1" fill="currentColor" stroke="none"/>'
            '</svg>'
        ),
        'fallback' : dict(tempo_min=33, distancia_km=8.0, custo_brl=0,
                          emissao_co2_g=0, risco=0.45, vel_media_kmh=18,
                          congestionamento_pct=5, pen_chuva=.40, pen_pico=.05,
                          pen_evento=.05, nome_rota='Via Mangue',
                          descricao='mais rápida (fallback)',
                          observacao='~18 km/h · ciclovia disponível na Via Mangue'),
    },
    'brt': {
        'modulo'   : 'modal_brt',
        'label'    : 'BRT/Metrô',
        'cor'      : '#7F77DD',
        'peso_dash': '12,4',
        'icon_svg' : (
            '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor"'
            ' stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="4" y="3" width="12" height="10" rx="1.5"/>'
            '<path d="M4 8h12M7 13v2.5M13 13v2.5M7 15.5h6"/>'
            '<circle cx="7.5" cy="11" r="1" fill="currentColor" stroke="none"/>'
            '<circle cx="12.5" cy="11" r="1" fill="currentColor" stroke="none"/>'
            '</svg>'
        ),
        'fallback' : dict(tempo_min=38, distancia_km=11.0, custo_brl=4.80,
                          emissao_co2_g=209, risco=0.18, vel_media_kmh=38,
                          congestionamento_pct=15, pen_chuva=.05, pen_pico=.15,
                          pen_evento=.20, nome_rota='TI Recife → Joana Bezerra',
                          descricao='corredor exclusivo (fallback)',
                          observacao='Corredor dedicado · menor impacto de congestionamento'),
    },
}

# Prioridades de rota (mapeadas nos botões do painel)
PRIORIDADES = [
    {'id': 'tempo',    'label': 'Tempo'},
    {'id': 'distancia','label': 'Distância'},
    {'id': 'economia', 'label': 'Economia'},
    {'id': 'seguranca','label': 'Segurança'},
]

# ==============================================================================
# 3. CARREGAMENTO DO GRAFO E DADOS CTTU (compartilhado por todos os modais)
# ==============================================================================

def carregar_grafo():
    print("► Baixando grafo OSM do Recife...")
    G = ox.graph_from_point(COORDS_ORIGEM, dist=8000, network_type='drive')
    print(f"  {G.number_of_nodes()} nós | {G.number_of_edges()} arestas\n")
    return G


def carregar_cttu():
    print("► Processando dados CTTU...")
    pesos = {
        'qtd_0a10km': 5.0,    'qtd_11a20km': 15.5,  'qtd_21a30km': 25.5,
        'qtd_31a40km': 35.5,  'qtd_41a50km': 45.5,  'qtd_51a60km': 55.5,
        'qtd_61a70km': 65.5,  'qtd_71a80km': 75.5,  'qtd_81a90km': 85.5,
        'qtd_91a100km': 95.5, 'qtd_acimade100km': 105.0,
    }
    df_vel = pd.read_csv(FILE_VELOCIDADE, sep=';')
    cols   = list(pesos.keys())
    df_vel['total'] = df_vel[cols].sum(axis=1)
    df_vel['vel']   = (
        sum(df_vel[c] * p for c, p in pesos.items())
        / df_vel['total'].replace(0, 1)
    )
    df_pico = (
        df_vel[df_vel['hora'] == 8]
        .groupby('equipamento')['vel'].mean()
        .reset_index()
        .rename(columns={'vel': 'velocidade_media'})
    )

    df_loc = pd.read_csv(FILE_LOCALIZACAO, sep=';', encoding='latin-1',
                         on_bad_lines='skip')
    df_loc['identificacao_equipamento'] = (
        df_loc['identificacao_equipamento'].astype(str).str.strip()
    )
    df_fc = df_loc[df_loc['identificacao_equipamento']
                   .str.startswith('FC', na=False)].copy()
    df_fc['equipamento'] = df_fc['identificacao_equipamento'] + 'REC'

    df = pd.merge(df_pico,
                  df_fc[['equipamento', 'latitude', 'longitude']],
                  on='equipamento', how='inner')
    print(f"  {df['equipamento'].nunique()} sensores carregados\n")
    return df


def injetar_pesos_base(G, df_radares):
    """
    Injeta peso 'tempo_dinamico' nas arestas usando dados reais CTTU.
    Serve como ponto de partida para qualquer módulo de modal.
    """
    vel_padrao = 40 / 3.6
    for u, v, key, data in G.edges(keys=True, data=True):
        data['tempo_dinamico'] = data.get('length', 1) / vel_padrao

    lons = df_radares['longitude'].tolist()
    lats = df_radares['latitude'].tolist()
    arestas = ox.distance.nearest_edges(G, X=lons, Y=lats)

    for idx, (u, v, key) in enumerate(arestas):
        v_kmh = max(df_radares.iloc[idx]['velocidade_media'], 1.0)
        dist  = G[u][v][key].get('length', 1)
        G[u][v][key]['tempo_dinamico'] = dist / (v_kmh / 3.6)

    return G


# ==============================================================================
# 4. EXECUTOR DE MODAIS
#    Tenta carregar o módulo do membro; usa fallback se não existir.
# ==============================================================================

def executar_modal(mid: str, cfg: dict, G, no_orig: int,
                   no_dest: int, df_radares) -> ModalResult:
    """
    Tenta importar o módulo registrado e chamar modal.calcular().
    Se o arquivo não existir, usa fallback.
    """
    modulo_nome = cfg['modulo']
    try:
        mod = importlib.import_module(modulo_nome)
        resultado = mod.calcular(
            graph=G,
            no_origem=no_orig,
            no_destino=no_dest,
            df_radares=df_radares,
            coords_origem=COORDS_ORIGEM,
            coords_destino=COORDS_DESTINO,
        )
        if not isinstance(resultado, ModalResult):
            raise TypeError(f"{modulo_nome}.calcular() deve retornar ModalResult")
        resultado.modal_id = mid
        print(f"  [{mid:8s}] ✓ {modulo_nome}.py — {resultado.tempo_min:.1f} min | "
              f"{resultado.distancia_km:.2f} km")
        return resultado

    except ModuleNotFoundError:
        print(f"  [{mid:8s}] ⚠  {modulo_nome}.py não encontrado — usando fallback")

    except Exception as e:
        print(f"  [{mid:8s}] ✗  Erro em {modulo_nome}.py:\n"
              f"              {traceback.format_exc(limit=2)}")
        print(f"              → usando fallback")

    # ── Fallback ──────────────────────────────────────────────────────────────
    fb = cfg['fallback']
    # rota_nos = rota padrão pelo grafo (Dijkstra distância simples)
    try:
        rota_fb = nx.shortest_path(G, no_orig, no_dest, weight='length')
    except Exception:
        rota_fb = [no_orig, no_dest]

    return ModalResult(modal_id=mid, rota_nos=rota_fb, **fb)


# ==============================================================================
# 5. EXTRAÇÃO DE COORDENADAS DE ROTA
# ==============================================================================

def rota_para_latlng(G, rota: list) -> list:
    coords = []
    for u, v in zip(rota[:-1], rota[1:]):
        edata = G.get_edge_data(u, v)
        if not edata:
            continue
        data = min(edata.values(), key=lambda d: d.get('length', 0))
        if 'geometry' in data:
            coords.extend([(y, x) for x, y in data['geometry'].coords])
        else:
            coords.append((G.nodes[u]['y'], G.nodes[u]['x']))
            coords.append((G.nodes[v]['y'], G.nodes[v]['x']))
    return coords


# ==============================================================================
# 6. GERAÇÃO DO PAINEL HTML (dados reais injetados via Python → JS)
# ==============================================================================

def gerar_painel_html(resultados: dict[str, ModalResult]) -> str:
    """
    Serializa os ModalResults para um objeto JS e retorna o HTML do painel.
    O painel é 100% reativo: ao trocar modal/prioridade, relê os dados reais.
    """

    # ── Serializa dados reais + alternativas para JS ──────────────────────────
    def _res_js(r: ModalResult, prio: str) -> str:
        alt = r.alternativas.get(prio)
        if alt:
            t  = alt.tempo_min
            km = alt.distancia_km
            lb = alt.nome_rota
            ds = alt.descricao
        else:
            t  = r.tempo_min
            km = r.distancia_km
            lb = r.nome_rota
            ds = r.descricao
        return (f"{{d:{t:.1f},km:{km:.2f},"
                f"lb:{_js_str(lb)},ds:{_js_str(ds)}}}")

    def _js_str(s: str) -> str:
        return "'" + s.replace("'", "\\'") + "'"

    modal_js_parts = []
    for mid, cfg in MODAIS_REGISTRADOS.items():
        r = resultados.get(mid)
        if r is None:
            continue
        rt_parts = ",".join(
            f"{p['id']}:{_res_js(r, p['id'])}"
            for p in PRIORIDADES
        )
        modal_js_parts.append(
            f"{{id:{_js_str(mid)},"
            f"label:{_js_str(cfg['label'])},"
            f"color:{_js_str(cfg['cor'])},"
            f"co2k:{r.emissao_co2_g / max(r.distancia_km, 0.01):.1f},"
            f"cstK:{r.custo_brl / max(r.distancia_km, 0.01):.4f},"
            f"risk:{r.risco:.3f},"
            f"sp:{r.vel_media_kmh:.1f},"
            f"cong:{r.congestionamento_pct:.0f},"
            f"penR:{r.pen_chuva:.2f},"
            f"penP:{r.pen_pico:.2f},"
            f"penE:{r.pen_evento:.2f},"
            f"tip:{_js_str(r.observacao)},"
            f"rt:{{{rt_parts}}}}}"
        )
    modal_js_array = "[" + ",\n".join(modal_js_parts) + "]"

    icons_js_parts = []
    for mid, cfg in MODAIS_REGISTRADOS.items():
        safe_svg = cfg['icon_svg'].replace('`', "'")
        icons_js_parts.append(f"{mid}:`{safe_svg}`")
    icons_js = "{" + ",".join(icons_js_parts) + "}"

    prio_js = "[" + ",".join(
        f"{{id:'{p['id']}',lb:'{p['label']}'}}" for p in PRIORIDADES
    ) + "]"

    return f"""
<!-- ===== PAINEL MULTIMODAL — HUB DE ROTAS ===== -->
<style>
/* ── Variáveis de cor — modo claro (padrão) ── */
#rmPanel{{
  --c-bg      : #ffffff;
  --c-bg2     : #f4f6fb;
  --c-bg3     : #edf1f9;
  --c-bg4     : #eff1f6;
  --c-txt     : #0f1117;
  --c-txt2    : #4a4f5e;
  --c-txt3    : #7a8090;
  --c-txt4    : #a8adb8;
  --c-bdr     : rgba(0,0,0,0.09);
  --c-bdr2    : rgba(0,0,0,0.06);
  --c-chip    : #dde0e8;
  --c-tgl-bg  : #f4f6fb;
  --c-tgl-bdr : #d8dce6;
  --c-bar-bg  : #dde0e8;
  position:fixed;top:16px;right:16px;z-index:9999;width:352px;
  background:var(--c-bg);
  border-radius:16px;
  box-shadow:0 8px 40px rgba(0,0,0,.14),0 2px 8px rgba(0,0,0,.09);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  overflow:hidden;
}}
/* ── Variáveis de cor — modo escuro ── */
@media (prefers-color-scheme:dark){{
  #rmPanel{{
    --c-bg      : #1a1d25;
    --c-bg2     : #22252f;
    --c-bg3     : #1a2840;
    --c-bg4     : #272a34;
    --c-txt     : #eceef4;
    --c-txt2    : #adb2c0;
    --c-txt3    : #757b8a;
    --c-txt4    : #505563;
    --c-bdr     : rgba(255,255,255,0.09);
    --c-bdr2    : rgba(255,255,255,0.06);
    --c-chip    : rgba(255,255,255,0.14);
    --c-tgl-bg  : #22252f;
    --c-tgl-bdr : rgba(255,255,255,0.14);
    --c-bar-bg  : rgba(255,255,255,0.12);
    box-shadow:0 8px 40px rgba(0,0,0,.55),0 2px 8px rgba(0,0,0,.35);
  }}
}}
#rmPanel *{{box-sizing:border-box;margin:0}}
#rmHead{{padding:12px 14px 9px;border-bottom:1px solid var(--c-bdr)}}
.rm-live{{float:right;margin-top:2px;display:inline-block;padding:2px 9px;
  border-radius:8px;background:#e8f9f0;color:#1a7a4a;font-size:10px;font-weight:700;
  letter-spacing:.05em}}
.rm-trip{{font-size:13px;font-weight:700;color:var(--c-txt);line-height:1.35;clear:both}}
.rm-sub{{font-size:10.5px;color:var(--c-txt3);margin-top:2px}}
#rmMbar{{display:flex;padding:8px 10px 0;border-bottom:1px solid var(--c-bdr2);
  gap:0;overflow-x:auto}}
.rm-mbtn{{flex:1;min-width:44px;display:flex;flex-direction:column;align-items:center;
  gap:2px;padding:5px 3px 7px;border:none;background:transparent;cursor:pointer;
  font-size:9.5px;font-weight:700;color:var(--c-txt4);
  border-bottom:2.5px solid transparent;transition:all .15s;white-space:nowrap;
  letter-spacing:.01em}}
.rm-mbtn.active{{color:var(--c-txt)}}
.rm-mbtn svg{{width:18px;height:18px;stroke:currentColor}}
#rmPtabs{{display:flex;gap:5px;padding:8px 12px 7px;flex-wrap:wrap}}
.rm-ptab{{padding:3px 12px;font-size:11px;font-weight:700;
  border:1px solid var(--c-chip);border-radius:20px;background:transparent;
  cursor:pointer;color:var(--c-txt3);transition:all .14s;letter-spacing:.01em}}
.rm-ptab.active{{background:var(--c-txt);color:var(--c-bg);border-color:var(--c-txt)}}
#rmHero{{padding:4px 14px 8px}}
.rm-dur{{font-size:40px;font-weight:800;color:var(--c-txt);line-height:1;letter-spacing:-1px}}
.rm-dur span{{font-size:15px;font-weight:400;color:var(--c-txt3);margin-left:3px}}
.rm-rname{{font-size:11px;color:var(--c-txt3);margin-top:3px;line-height:1.4}}
.rm-grid{{display:grid;grid-template-columns:1fr 1fr;gap:5px;padding:0 10px 8px}}
.rm-card{{background:var(--c-bg2);border-radius:9px;padding:8px 10px}}
.rm-clbl{{font-size:9.5px;color:var(--c-txt4);text-transform:uppercase;
  letter-spacing:.05em;margin-bottom:3px}}
.rm-cval{{font-size:17px;font-weight:800;color:var(--c-txt)}}
.rm-cunit{{font-size:10px;color:var(--c-txt3);font-weight:400}}
.rm-badge{{display:inline-block;padding:2px 10px;border-radius:8px;
  font-size:11px;font-weight:700;margin-top:2px}}
.rm-sprow{{display:flex;gap:5px;padding:0 10px 8px}}
.rm-spcard{{flex:1;background:var(--c-bg2);border-radius:9px;padding:7px 10px}}
.rm-factors{{padding:4px 10px 9px}}
.rm-flbl{{font-size:9.5px;color:var(--c-txt4);text-transform:uppercase;
  letter-spacing:.05em;margin-bottom:5px}}
.rm-chips{{display:flex;gap:5px;flex-wrap:wrap}}
.rm-chip{{display:inline-flex;align-items:center;gap:4px;padding:3px 11px;
  border:1px solid var(--c-chip);border-radius:12px;font-size:11px;font-weight:700;
  cursor:pointer;color:var(--c-txt3);background:transparent;transition:all .13s}}
.rm-chip.on{{background:#fff8e1;border-color:#e0a800;color:#a07200}}
.rm-dot{{width:5px;height:5px;border-radius:50%;background:currentColor;
  opacity:.35;transition:opacity .13s;flex-shrink:0}}
.rm-chip.on .rm-dot{{opacity:1}}
.rm-comp{{padding:0 10px 11px}}
.rm-complbl{{font-size:9.5px;color:var(--c-txt4);text-transform:uppercase;
  letter-spacing:.05em;margin-bottom:5px}}
.rm-crow{{display:flex;align-items:center;gap:7px;padding:4px 5px;
  border-radius:7px;cursor:pointer;transition:background .1s}}
.rm-crow:hover{{background:var(--c-bg4)}}
.rm-crow.rm-active{{background:var(--c-bg3)}}
.rm-cname{{width:62px;font-size:12px;color:var(--c-txt3)}}
.rm-cname.rm-active{{font-weight:800;color:var(--c-txt)}}
.rm-cbarw{{flex:1;background:var(--c-bar-bg);border-radius:3px;height:3px;overflow:hidden}}
.rm-cbar{{height:3px;border-radius:3px;transition:width .35s cubic-bezier(.4,0,.2,1)}}
.rm-cdur{{width:48px;text-align:right;font-size:12px;color:var(--c-txt3)}}
.rm-cdur.rm-active{{font-weight:800;color:var(--c-txt)}}
#rmToggle{{position:absolute;top:11px;right:11px;width:23px;height:23px;
  border-radius:50%;border:1px solid var(--c-tgl-bdr);background:var(--c-tgl-bg);
  cursor:pointer;display:flex;align-items:center;justify-content:center;
  font-size:11px;color:var(--c-txt3);z-index:2}}
#rmBody{{transition:max-height .3s ease;overflow:hidden;max-height:900px}}
.rm-tip-txt{{font-size:10.5px;color:var(--c-txt2);line-height:1.45;margin-top:2px}}
.rm-src-badge{{margin:4px 10px 0;padding:3px 10px;border-radius:6px;
  background:#f0f4ff;border:1px solid #d0dbff;
  font-size:10px;color:#4060cc;font-weight:600;}}
</style>

<div id="rmPanel">
  <button id="rmToggle" onclick="rmToggle()" title="minimizar">▲</button>
  <div id="rmHead">
    <span class="rm-live">● ao vivo</span>
    <div class="rm-trip">Cine São Luiz &rarr; Fac. Nova Roma</div>
    <div class="rm-sub">Recife · CTTU dez/2025 · OSM + Dijkstra multimodal</div>
  </div>
  <div id="rmBody">
    <div id="rmMbar"></div>
    <div id="rmPtabs"></div>
    <div id="rmHero">
      <div class="rm-dur" id="rmDur">-- <span>min</span></div>
      <div class="rm-rname" id="rmRname">—</div>
    </div>
    <div id="rmSrcBadge" class="rm-src-badge" style="display:none"></div>
    <div class="rm-grid">
      <div class="rm-card">
        <div class="rm-clbl">distância</div>
        <div><span class="rm-cval" id="rmDist">--</span><span class="rm-cunit"> km</span></div>
      </div>
      <div class="rm-card">
        <div class="rm-clbl">custo estimado</div>
        <div><span class="rm-cunit">R$&#8202;</span><span class="rm-cval" id="rmCost">--</span></div>
      </div>
      <div class="rm-card">
        <div class="rm-clbl">emissão CO₂</div>
        <div><span class="rm-cval" id="rmCo2">--</span><span class="rm-cunit"> g</span></div>
      </div>
      <div class="rm-card">
        <div class="rm-clbl">risco viário</div>
        <span class="rm-badge" id="rmRisk">--</span>
      </div>
    </div>
    <div class="rm-sprow">
      <div class="rm-spcard">
        <div class="rm-clbl">vel. média</div>
        <div><span class="rm-cval" style="font-size:16px" id="rmSp">--</span>
             <span class="rm-cunit"> km/h</span></div>
      </div>
      <div class="rm-spcard">
        <div class="rm-clbl">congestionamento</div>
        <div><span class="rm-cval" style="font-size:16px" id="rmCong">--</span>
             <span class="rm-cunit">%</span></div>
      </div>
      <div class="rm-spcard" style="flex:1.7">
        <div class="rm-clbl">observação</div>
        <div class="rm-tip-txt" id="rmTip">—</div>
      </div>
    </div>
    <div class="rm-factors">
      <div class="rm-flbl">fatores dinâmicos</div>
      <div class="rm-chips">
        <button class="rm-chip" id="fc-rain"  onclick="rmFac('rain')">
          <span class="rm-dot"></span>chuva</button>
        <button class="rm-chip" id="fc-peak"  onclick="rmFac('peak')">
          <span class="rm-dot"></span>pico</button>
        <button class="rm-chip" id="fc-event" onclick="rmFac('event')">
          <span class="rm-dot"></span>evento</button>
      </div>
    </div>
    <div class="rm-comp">
      <div class="rm-complbl">comparativo multimodal</div>
      <div id="rmComp"></div>
    </div>
  </div>
</div>

<script>
(function(){{
  var MD = {modal_js_array};
  var PR = {prio_js};
  var IC = {icons_js};

  var aM = MD[0].id, aP = 'tempo';
  var fac = {{rain:false, peak:false, event:false}};
  var collapsed = false;

  function gd(mo, p){{
    var b = mo.rt[p].d;
    var mul = 1;
    if(fac.rain)  mul += mo.penR;
    if(fac.peak)  mul += mo.penP;
    if(fac.event) mul += mo.penE;
    return +(b * mul).toFixed(1);
  }}

  function rl(r){{
    if(r < 0.3) return {{t:'baixo', bg:'#e8f9f0', tc:'#1a7a4a'}};
    if(r < 0.6) return {{t:'médio', bg:'#fff8e1', tc:'#b07800'}};
    return {{t:'alto',  bg:'#fdecea', tc:'#c0392b'}};
  }}

  function render(){{
    var mo = MD.find(function(x){{ return x.id === aM; }});
    var r  = mo.rt[aP];
    var dur = gd(mo, aP);

    document.getElementById('rmDur').innerHTML = dur + ' <span>min</span>';
    document.getElementById('rmRname').textContent = r.lb + ' · ' + r.ds;
    document.getElementById('rmDist').textContent  = r.km.toFixed(2);

    var cost = (r.km * mo.cstK);
    document.getElementById('rmCost').textContent  = cost.toFixed(2);
    document.getElementById('rmCo2').textContent   = Math.round(r.km * mo.co2k);

    var ri = rl(mo.risk), rb = document.getElementById('rmRisk');
    rb.textContent = ri.t; rb.style.background = ri.bg; rb.style.color = ri.tc;

    var sp = fac.peak ? Math.round(mo.sp * 0.7) : mo.sp;
    document.getElementById('rmSp').textContent   = sp;
    var congAdj = fac.peak ? Math.min(mo.cong + 15, 99) : mo.cong;
    document.getElementById('rmCong').textContent = congAdj;
    document.getElementById('rmTip').textContent  = mo.tip;

    document.querySelectorAll('.rm-mbtn').forEach(function(b){{
      var id  = b.dataset.id;
      var m2  = MD.find(function(x){{ return x.id === id; }});
      var isA = id === aM;
      b.classList.toggle('active', isA);
      b.style.borderBottomColor = isA ? m2.color : 'transparent';
      b.style.color = '';
    }});
    document.querySelectorAll('.rm-ptab').forEach(function(t){{
      t.classList.toggle('active', t.dataset.id === aP);
    }});

    var mx = Math.max.apply(null, MD.map(function(x){{ return gd(x, aP); }}));
    document.getElementById('rmComp').innerHTML = MD.map(function(x){{
      var d  = gd(x, aP);
      var w  = Math.max(5, Math.round(d / mx * 100));
      var isA = x.id === aM;
      return '<div class="rm-crow' + (isA ? ' rm-active' : '')
        + '" onclick="window._rmSm(\\'' + x.id + '\\')">'
        + '<div class="rm-cname' + (isA ? ' rm-active' : '') + '">' + x.label + '</div>'
        + '<div class="rm-cbarw"><div class="rm-cbar" style="width:' + w + '%;background:'
        + x.color + (isA ? '' : 'bb') + '"></div></div>'
        + '<div class="rm-cdur' + (isA ? ' rm-active' : '') + '">' + d + ' min</div>'
        + '</div>';
    }}).join('');
  }}

  window._rmSm = function(id){{ aM = id; render(); }};
  window.rmFac = function(f){{
    fac[f] = !fac[f];
    document.getElementById('fc-' + f).classList.toggle('on', fac[f]);
    render();
  }};
  window.rmToggle = function(){{
    collapsed = !collapsed;
    var body = document.getElementById('rmBody');
    var btn  = document.getElementById('rmToggle');
    body.style.maxHeight = collapsed ? '0' : '900px';
    btn.textContent = collapsed ? '▼' : '▲';
  }};

  /* modal bar */
  var mb = document.getElementById('rmMbar');
  MD.forEach(function(mo){{
    var b = document.createElement('button');
    b.className = 'rm-mbtn' + (mo.id === aM ? ' active' : '');
    b.dataset.id = mo.id;
    b.innerHTML  = IC[mo.id] + '<span>' + mo.label + '</span>';
    b.onclick = function(){{ window._rmSm(mo.id); }};
    mb.appendChild(b);
  }});

  /* priority tabs */
  var pt = document.getElementById('rmPtabs');
  PR.forEach(function(p){{
    var b = document.createElement('button');
    b.className = 'rm-ptab' + (p.id === aP ? ' active' : '');
    b.dataset.id = p.id;
    b.textContent = p.lb;
    b.onclick = function(){{ aP = p.id; render(); }};
    pt.appendChild(b);
  }});

  render();
}})();
</script>
<!-- ===== FIM DO PAINEL ===== -->
"""


# ==============================================================================
# 7. INJEÇÃO DO PAINEL NO HTML FOLIUM
# ==============================================================================

def inject_panel(html_path: str, panel_html: str):
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('</body>', panel_html + '\n</body>')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  Painel injetado em {html_path}")


# ==============================================================================
# 8. PIPELINE PRINCIPAL
# ==============================================================================

def main():
    print("\n" + "="*62)
    print("  HUB DE ROTAS MULTIMODAL — Recife (CTTU dez/2025)")
    print("="*62 + "\n")

    # ── Infra compartilhada ───────────────────────────────────────────────────
    G          = carregar_grafo()
    df_radares = carregar_cttu()
    G          = injetar_pesos_base(G, df_radares)

    no_orig  = ox.distance.nearest_nodes(G, X=COORDS_ORIGEM[1],  Y=COORDS_ORIGEM[0])
    no_dest  = ox.distance.nearest_nodes(G, X=COORDS_DESTINO[1], Y=COORDS_DESTINO[0])

    # ── Executa cada modal registrado ─────────────────────────────────────────
    print("► Calculando rotas por modal...\n")
    resultados: dict[str, ModalResult] = {}
    for mid, cfg in MODAIS_REGISTRADOS.items():
        resultados[mid] = executar_modal(mid, cfg, G, no_orig, no_dest, df_radares)

    # ── Mapa Folium ───────────────────────────────────────────────────────────
    print("\n► Gerando mapa interativo...")
    m = folium.Map(location=COORDS_ORIGEM, zoom_start=13,
                   tiles='CartoDB positron')

    for mid, res in resultados.items():
        cfg = MODAIS_REGISTRADOS[mid]
        if not res.rota_nos or len(res.rota_nos) < 2:
            continue
        coords = rota_para_latlng(G, res.rota_nos)
        if not coords:
            continue
        kw = dict(
            color   = cfg['cor'],
            weight  = 6 if mid == 'car' else 4,
            opacity = 0.9 if mid == 'car' else 0.75,
            tooltip = f"{cfg['label']} — {res.tempo_min:.0f} min · {res.distancia_km:.1f} km",
        )
        if cfg['peso_dash']:
            kw['dash_array'] = cfg['peso_dash']
        folium.PolyLine(coords, **kw).add_to(m)

    folium.Marker(
        COORDS_ORIGEM,
        tooltip='🟢 Origem — Cine São Luiz',
        icon=folium.Icon(color='green', icon='play', prefix='fa'),
    ).add_to(m)
    folium.Marker(
        COORDS_DESTINO,
        tooltip='🔴 Destino — Faculdade Nova Roma',
        icon=folium.Icon(color='red', icon='flag', prefix='fa'),
    ).add_to(m)

    html_path = 'mapa_rotas.html'
    m.save(html_path)
    inject_panel(html_path, gerar_painel_html(resultados))

    print(f"\n✅ {html_path} gerado com sucesso.")
    print("   Abrindo no navegador...\n")
    webbrowser.open(html_path)


if __name__ == '__main__':
    main()
