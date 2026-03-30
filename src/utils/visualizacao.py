"""
Geração do mapa interativo com painel estilo Google Maps.

O painel lateral permite selecionar o modal de transporte e o cenário
(pico 8h / fora de pico 14h). As rotas no mapa são exibidas/ocultadas
de acordo com a seleção do usuário.
"""

import json
import webbrowser

import folium

from src.utils.helpers import rota_para_latlng
from src.utils.comparacao import (
    calcular_custo_variavel,
    CUSTO_KM_CARRO,
    CUSTO_KM_MOTO,
    CUSTO_FIXO_ONIBUS,
)


# ---------------------------------------------------------------------------
# Funções internas: adicionam polylines a um FeatureGroup
# ---------------------------------------------------------------------------

def _linhas_carro(group, graph, rota_tempo, rota_distancia, tempo_min):
    """Adiciona as linhas de carro (rota mais rápida e mais curta) ao grupo."""
    folium.PolyLine(
        rota_para_latlng(graph, rota_tempo),
        color='#e53935', weight=6, opacity=0.9,
        tooltip=f'Carro – mais rápido (~{tempo_min:.0f} min)',
    ).add_to(group)
    folium.PolyLine(
        rota_para_latlng(graph, rota_distancia),
        color='#b71c1c', weight=4, opacity=0.5,
        dash_array='6,4',
        tooltip='Carro – mais curto (em distância)',
    ).add_to(group)


def _linhas_moto(group, graph, rota, tempo_min):
    """Adiciona a linha de moto ao grupo."""
    folium.PolyLine(
        rota_para_latlng(graph, rota),
        color='#43a047', weight=5, opacity=0.9,
        dash_array='5,5',
        tooltip=f'Moto – ~{tempo_min:.0f} min',
    ).add_to(group)


def _linhas_bike(group, graph, rotas):
    """Adiciona as linhas de bicicleta ao grupo (até 3 rotas)."""
    cores = ['#00acc1', '#006064', '#80deea']
    for i, item in enumerate(rotas):
        folium.PolyLine(
            rota_para_latlng(graph, item['rota']),
            color=cores[i % len(cores)], weight=5, opacity=0.9,
            tooltip=f"Bicicleta – {item['nome']} (~{item['tempo_min']:.0f} min)",
        ).add_to(group)


def _linhas_caminhada(group, graph, rotas):
    """Adiciona as linhas de caminhada ao grupo."""
    cores = ['#fb8c00', '#e65100']
    for i, item in enumerate(rotas):
        folium.PolyLine(
            rota_para_latlng(graph, item['rota']),
            color=cores[i % len(cores)], weight=4, opacity=0.9,
            dash_array='8,4',
            tooltip=f"Caminhada – {item['nome']} (~{item['tempo_min']:.0f} min)",
        ).add_to(group)


# ---------------------------------------------------------------------------
# Monta os dados do painel para cada cenário
# ---------------------------------------------------------------------------

def _dados_painel(cenarios_resultados):
    """
    Extrai tempo, distância e custo de cada modal por cenário.

    Retorna um dict {pico: {...}, fora: {...}} pronto para serializar em JSON.
    """
    dados = {}
    for cr in cenarios_resultados:
        chave = 'pico' if cr['hora'] == 8 else 'fora'
        dist_m  = cr['carro']['distancia_metros']
        dist_km = dist_m / 1000

        dados[chave] = {
            'carro': {
                'tempo_min':    round(cr['carro']['tempo_seg'] / 60, 1),
                'distancia_km': round(dist_km, 2),
                'custo':        round(calcular_custo_variavel(dist_m, CUSTO_KM_CARRO), 2),
            },
            'moto': {
                'tempo_min':    round(cr['moto']['tempo_seg'] / 60, 1),
                'distancia_km': round(dist_km, 2),
                'custo':        round(calcular_custo_variavel(dist_m, CUSTO_KM_MOTO), 2),
            },
            'bicicleta': [
                {'nome': r['nome'], 'tempo_min': round(r['tempo_min'], 1)}
                for r in cr['bicicleta']
            ],
            'caminhada': [
                {'nome': r['nome'], 'tempo_min': round(r['tempo_min'], 1)}
                for r in cr['caminhada']
            ],
            'onibus': {
                'tempo_min':    34.0,
                'distancia_km': None,
                'custo':        CUSTO_FIXO_ONIBUS,
            },
        }
    return dados


# ---------------------------------------------------------------------------
# HTML / CSS / JS do painel lateral
# ---------------------------------------------------------------------------

def _html_painel(map_name, layers_js, dados_painel):
    """
    Gera o bloco HTML com o painel estilo Google Maps e o JS de controle.

    Parâmetros:
        map_name:     nome da variável JS do mapa Folium (ex: 'map_abc123')
        layers_js:    dict {chave_modal: nome_variavel_js_do_featuregroup}
        dados_painel: dict com dados de tempo/custo por modal e cenário
    """
    layers_json = json.dumps(layers_js, ensure_ascii=False)
    dados_json  = json.dumps(dados_painel, ensure_ascii=False)

    return f"""
<style>
  #painel-rotas {{
    position: fixed;
    top: 10px;
    left: 10px;
    width: 310px;
    max-height: calc(100vh - 20px);
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 3px 16px rgba(0,0,0,.28);
    z-index: 1000;
    display: flex;
    flex-direction: column;
    font-family: Roboto, Arial, sans-serif;
    overflow: hidden;
  }}
  #painel-header {{
    background: #1a73e8;
    color: #fff;
    padding: 14px 16px 10px;
    flex-shrink: 0;
  }}
  #painel-header .titulo   {{ font-size: 13px; font-weight: 600; margin-bottom: 3px; }}
  #painel-header .subtitulo {{ font-size: 11px; opacity: .85; }}
  .cenario-tabs {{
    display: flex;
    border-bottom: 1px solid #e0e0e0;
    flex-shrink: 0;
  }}
  .tab-btn {{
    flex: 1;
    padding: 9px 4px;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 11px;
    color: #5f6368;
    border-bottom: 2px solid transparent;
    transition: all .2s;
  }}
  .tab-btn.ativo {{ color: #1a73e8; border-bottom-color: #1a73e8; font-weight: 600; }}
  #modais-lista {{ flex: 1; overflow-y: auto; padding: 6px 8px; }}
  .modal-card {{
    display: flex;
    align-items: flex-start;
    padding: 10px 8px;
    border-radius: 8px;
    cursor: pointer;
    margin-bottom: 2px;
    border: 2px solid transparent;
    transition: background .15s, border-color .15s;
    gap: 10px;
  }}
  .modal-card:hover  {{ background: #f1f3f4; }}
  .modal-card.ativo  {{ border-color: #1a73e8; background: #e8f0fe; }}
  .modal-card.sem-rota {{ opacity: .65; cursor: default; }}
  .modal-card.sem-rota:hover {{ background: none; }}
  .modal-icone {{ font-size: 22px; margin-top: 1px; flex-shrink: 0; }}
  .modal-info  {{ flex: 1; min-width: 0; }}
  .modal-nome    {{ font-size: 13px; font-weight: 500; color: #202124; }}
  .modal-detalhe {{ font-size: 11px; color: #5f6368; margin-top: 1px; }}
  .sub-rota {{
    font-size: 10.5px;
    color: #5f6368;
    margin-top: 1px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .modal-metrica {{ text-align: right; flex-shrink: 0; }}
  .modal-tempo {{ font-size: 15px; font-weight: 600; color: #202124; }}
  .modal-custo {{ font-size: 11px; color: #5f6368; margin-top: 2px; }}
  .modal-dist  {{ font-size: 10px; color: #9aa0a6; margin-top: 1px; }}
  #painel-rodape {{
    padding: 7px 12px;
    background: #f8f9fa;
    border-top: 1px solid #e0e0e0;
    font-size: 10px;
    color: #9aa0a6;
    flex-shrink: 0;
  }}
</style>

<div id="painel-rotas">
  <div id="painel-header">
    <div class="titulo">&#128506; Análise de Rotas Multimodais</div>
    <div class="subtitulo">Cine São Luiz &#8594; Faculdade Nova Roma</div>
  </div>
  <div class="cenario-tabs">
    <button class="tab-btn ativo" data-cenario="pico"
            onclick="painelSelecionarCenario('pico')">&#128359; Pico – 8h</button>
    <button class="tab-btn" data-cenario="fora"
            onclick="painelSelecionarCenario('fora')">&#9728; Fora de pico – 14h</button>
  </div>
  <div id="modais-lista"></div>
  <div id="painel-rodape">Fonte: CTTU Recife &middot; OSMnx &middot; Dijkstra &amp; A*</div>
</div>

<script>
(function () {{
  var LAYER_NAMES = {layers_json};
  var DADOS       = {dados_json};
  var MAP_NAME    = '{map_name}';

  var MODAIS = [
    {{ key: 'carro',     icone: '&#128663;', nome: 'Carro',     detalhe: 'Rota mais rápida (Dijkstra)' }},
    {{ key: 'moto',      icone: '&#129309;', nome: 'Moto',      detalhe: 'Velocidade média 50 km/h' }},
    {{ key: 'bicicleta', icone: '&#128690;', nome: 'Bicicleta', detalhe: '3 rotas alternativas' }},
    {{ key: 'caminhada', icone: '&#128694;', nome: 'Caminhada', detalhe: '2 rotas alternativas' }},
    {{ key: 'onibus',    icone: '&#128652;', nome: 'Ônibus',    detalhe: 'Setúbal (estimativa)', semRota: true }},
  ];

  var cenarioAtual = 'pico';
  var modalAtual   = 'carro';

  function resolverCamada(nome) {{ return window[nome] || null; }}

  function obterMapa() {{ return window[MAP_NAME] || null; }}

  function mostrarRota(modal, cenario) {{
    var mapa = obterMapa();
    if (!mapa) return;

    // Oculta todas as camadas
    Object.values(LAYER_NAMES).forEach(function (nome) {{
      var layer = resolverCamada(nome);
      if (layer) mapa.removeLayer(layer);
    }});

    // Exibe a camada selecionada
    var chave = (modal === 'carro' || modal === 'moto')
      ? modal + '_' + cenario
      : modal;

    var layer = resolverCamada(LAYER_NAMES[chave]);
    if (layer) mapa.addLayer(layer);
  }}

  window.painelSelecionarCenario = function (cenario) {{
    cenarioAtual = cenario;
    document.querySelectorAll('.tab-btn').forEach(function (b) {{
      b.classList.toggle('ativo', b.getAttribute('data-cenario') === cenario);
    }});
    renderizarCards();
    mostrarRota(modalAtual, cenario);
  }};

  function selecionarModal(modal) {{
    modalAtual = modal;
    document.querySelectorAll('.modal-card').forEach(function (c) {{
      c.classList.toggle('ativo', c.getAttribute('data-modal') === modal);
    }});
    mostrarRota(modal, cenarioAtual);
  }}

  function formatarTempo(min) {{
    if (min >= 60) {{
      var h = Math.floor(min / 60);
      var m = Math.round(min % 60);
      return h + 'h' + (m > 0 ? ' ' + m + 'min' : '');
    }}
    return Math.round(min) + ' min';
  }}

  function renderizarCards() {{
    var lista   = document.getElementById('modais-lista');
    var cenario = DADOS[cenarioAtual];
    lista.innerHTML = '';

    MODAIS.forEach(function (m) {{
      var d        = cenario[m.key];
      var tempoStr, custoStr, distStr = '', subRotas = '';

      if (Array.isArray(d)) {{
        var melhor = d.reduce(function (a, b) {{
          return a.tempo_min < b.tempo_min ? a : b;
        }});
        tempoStr = formatarTempo(melhor.tempo_min);
        custoStr = 'Gratuito';
        subRotas = d.map(function (r) {{
          return '<div class="sub-rota">&bull; ' + r.nome + ': ' + formatarTempo(r.tempo_min) + '</div>';
        }}).join('');
      }} else {{
        tempoStr = formatarTempo(d.tempo_min);
        custoStr = d.custo > 0 ? 'R$ ' + d.custo.toFixed(2) : 'Gratuito';
        distStr  = d.distancia_km ? d.distancia_km.toFixed(1) + ' km' : '';
      }}

      var isAtivo = (m.key === modalAtual && !m.semRota);
      var card    = document.createElement('div');
      card.className = 'modal-card'
        + (isAtivo   ? ' ativo'    : '')
        + (m.semRota ? ' sem-rota' : '');
      card.setAttribute('data-modal', m.key);

      if (!m.semRota) {{
        card.onclick = (function (key) {{
          return function () {{ selecionarModal(key); }};
        }})(m.key);
      }}

      card.innerHTML =
        '<div class="modal-icone">' + m.icone + '</div>' +
        '<div class="modal-info">' +
          '<div class="modal-nome">'    + m.nome    + '</div>' +
          '<div class="modal-detalhe">' + m.detalhe + '</div>' +
          subRotas +
        '</div>' +
        '<div class="modal-metrica">' +
          '<div class="modal-tempo">' + tempoStr + '</div>' +
          '<div class="modal-custo">' + custoStr + '</div>' +
          (distStr ? '<div class="modal-dist">' + distStr + '</div>' : '') +
        '</div>';

      lista.appendChild(card);
    }});
  }}

  // Aguarda o mapa Leaflet estar disponível antes de inicializar
  function inicializar() {{
    if (obterMapa()) {{
      renderizarCards();
      mostrarRota('carro', 'pico');
    }} else {{
      setTimeout(inicializar, 200);
    }}
  }}

  inicializar();
}})();
</script>
"""


# ---------------------------------------------------------------------------
# Função principal: cria e salva o mapa completo
# ---------------------------------------------------------------------------

def criar_mapa_interativo(
    cenarios_resultados,
    graph_walk,
    graph_bike,
    coords_origem,
    coords_destino,
    arquivo='mapa_rotas.html',
):
    """
    Cria o mapa interativo com painel de seleção por modal e cenário.

    Para cada modal (carro, moto, bicicleta, caminhada) cria um FeatureGroup
    separado; para carro e moto, um grupo por cenário (pico/fora de pico).
    O painel lateral em HTML permite ao usuário alternar entre modais e cenários.

    Complexidade: O(V + E) para converter rotas em coordenadas (percorre arestas).

    Parâmetros:
        cenarios_resultados: lista com dois dicts retornados por executar_cenario()
        graph_walk:          grafo de pedestres
        graph_bike:          grafo de bicicleta
        coords_origem:       tupla (lat, lon) da origem
        coords_destino:      tupla (lat, lon) do destino
        arquivo:             caminho do arquivo HTML de saída
    """
    pico = cenarios_resultados[0]
    fora = cenarios_resultados[1]

    # Ponto central do mapa: média entre origem e destino
    centro = (
        (coords_origem[0] + coords_destino[0]) / 2,
        (coords_origem[1] + coords_destino[1]) / 2,
    )
    mapa     = folium.Map(location=centro, zoom_start=13, tiles='CartoDB positron')
    map_name = mapa.get_name()

    # Marcadores de origem e destino
    folium.Marker(
        coords_origem,
        tooltip='Origem – Cine São Luiz',
        icon=folium.Icon(color='blue', icon='play', prefix='fa'),
    ).add_to(mapa)
    folium.Marker(
        coords_destino,
        tooltip='Destino – Faculdade Nova Roma',
        icon=folium.Icon(color='red', icon='flag', prefix='fa'),
    ).add_to(mapa)

    # FeatureGroups: carro por cenário (pesos CTTU diferentes)
    fg_carro_pico = folium.FeatureGroup(name='carro_pico', show=True)
    _linhas_carro(
        fg_carro_pico,
        pico['graph_c'],
        pico['carro']['rota_tempo'],
        pico['carro']['rota_distancia'],
        pico['carro']['tempo_seg'] / 60,
    )
    fg_carro_pico.add_to(mapa)

    fg_carro_fora = folium.FeatureGroup(name='carro_fora', show=False)
    _linhas_carro(
        fg_carro_fora,
        fora['graph_c'],
        fora['carro']['rota_tempo'],
        fora['carro']['rota_distancia'],
        fora['carro']['tempo_seg'] / 60,
    )
    fg_carro_fora.add_to(mapa)

    # FeatureGroups: moto por cenário
    fg_moto_pico = folium.FeatureGroup(name='moto_pico', show=False)
    _linhas_moto(
        fg_moto_pico,
        pico['graph_c'],
        pico['moto']['rota'],
        pico['moto']['tempo_seg'] / 60,
    )
    fg_moto_pico.add_to(mapa)

    fg_moto_fora = folium.FeatureGroup(name='moto_fora', show=False)
    _linhas_moto(
        fg_moto_fora,
        fora['graph_c'],
        fora['moto']['rota'],
        fora['moto']['tempo_seg'] / 60,
    )
    fg_moto_fora.add_to(mapa)

    # FeatureGroup: bicicleta (mesma rota nos dois cenários)
    fg_bike = folium.FeatureGroup(name='bicicleta', show=False)
    _linhas_bike(fg_bike, graph_bike, pico['bicicleta'])
    fg_bike.add_to(mapa)

    # FeatureGroup: caminhada (mesma rota nos dois cenários)
    fg_walk = folium.FeatureGroup(name='caminhada', show=False)
    _linhas_caminhada(fg_walk, graph_walk, pico['caminhada'])
    fg_walk.add_to(mapa)

    # Mapa das chaves de modal para os nomes de variável JS dos FeatureGroups
    layers_js = {
        'carro_pico': fg_carro_pico.get_name(),
        'carro_fora': fg_carro_fora.get_name(),
        'moto_pico':  fg_moto_pico.get_name(),
        'moto_fora':  fg_moto_fora.get_name(),
        'bicicleta':  fg_bike.get_name(),
        'caminhada':  fg_walk.get_name(),
    }

    # Dados de tempo/custo para o painel lateral
    dados = _dados_painel(cenarios_resultados)

    # Injeta o painel HTML no mapa
    painel_html = _html_painel(map_name, layers_js, dados)
    mapa.get_root().html.add_child(folium.Element(painel_html))

    # Salva e abre no navegador
    mapa.save(arquivo)
    webbrowser.open(arquivo)
    print(f"Mapa salvo em '{arquivo}' e aberto no navegador.")
