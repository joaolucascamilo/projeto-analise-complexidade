"""
Ponto de entrada do sistema de análise de rotas multimodais.

Percurso analisado:
    Cine São Luiz (Centro) → Faculdade Nova Roma (Boa Viagem) – Recife/PE

Executa dois cenários de teste para análise empírica:
    Cenário A – Horário de pico da manhã  (8h)   → tráfego intenso
    Cenário B – Horário fora de pico      (14h)  → tráfego reduzido

Para cada cenário:
  - Calcula rotas para todos os modais (carro, moto, bicicleta, caminhada)
  - Compara Dijkstra vs A* com medição de tempo de execução
  - Exibe tabela comparativa com tempo, distância e custo por modal

Complexidade dos algoritmos:
    Dijkstra: O((V + E) log V)
    A*:       O((V + E) log V) — pior caso; expande menos nós na prática
    Onde V = vértices (cruzamentos) e E = arestas (segmentos de via)
"""

from src.utils.grafo import (
    COORDS_ORIGEM,
    COORDS_DESTINO,
    baixar_grafo_carro,
    baixar_grafo_pedestre,
    processar_velocidades_cttu,
    injetar_pesos_carro,
    injetar_tempo_caminhada,
    injetar_tempo_bicicleta,
)
from src.utils.visualizacao import criar_mapa_interativo
from src.utils.comparacao import gerar_tabela_comparativa
from src.utils.benchmark  import medir_tempo

# Módulos de cálculo por modal
from src.carro.algoritmo     import calcular_rotas_carro
from src.moto.algoritmo      import calcular_rota_moto
from src.caminhada.algoritmo import calcular_rotas_caminhada
from src.bicicleta.algoritmo import calcular_rotas_bicicleta

# Arquivos de dados da CTTU
ARQUIVO_VELOCIDADE = (
    './data/resources_c2d9c049-6511-4dc4-9691-b76a43e4f7e3'
    '_fotossensores-2025-dezembro-quantitativo-das-vias-por-velocidade-media.csv'
)
ARQUIVO_LOCALIZACAO = (
    './data/resources_36c2b47b-f439-4895-8b65-3f3dda36a4a7'
    '_lista-de-equipamentos-de-fiscalizacao-de-transito.csv'
)

# Arquivo de saída do mapa interativo
ARQUIVO_MAPA = 'mapa_rotas.html'

# Cenários de teste: (hora_cttu, nome_do_cenario)
CENARIOS = [
    (8,  'Pico - manhã (8h)'),
    (14, 'Fora de pico (14h)'),
]


def executar_cenario(graph_carro, graph_walk, graph_bike, hora, nome_cenario):
    """
    Executa o cálculo completo de rotas para um único cenário de tráfego.

    Parâmetros:
        graph_carro:   grafo viário de carros (sem pesos injetados)
        graph_walk:    grafo de pedestres com tempo_caminhada
        graph_bike:    grafo de bicicleta com tempo_bicicleta
        hora:          hora do dia para filtrar dados da CTTU (0-23)
        nome_cenario:  descrição do cenário (para exibição)

    Retorna:
        dict com todos os resultados calculados no cenário
    """
    print(f"\n{'='*60}")
    print(f"  CENÁRIO: {nome_cenario}")
    print(f"{'='*60}\n")

    # Processa velocidades da CTTU para a hora do cenário
    df_radares = processar_velocidades_cttu(
        ARQUIVO_VELOCIDADE, ARQUIVO_LOCALIZACAO, hora=hora
    )

    # Injeta os pesos no grafo de carros (cria cópia para não contaminar outros cenários)
    graph_c = injetar_pesos_carro(graph_carro.copy(), df_radares)

    # Cálculo das rotas com medição de tempo total do cenário
    print("[Carro]")
    resultado_carro, t_carro = medir_tempo(calcular_rotas_carro, graph_c)
    print(f"  tempo total da função: {t_carro:.1f} ms\n")

    print("[Moto]")
    resultado_moto = calcular_rota_moto(graph_c, resultado_carro['rota_tempo'])

    # Adiciona a distância do carro ao resultado da moto (mesma via)
    resultado_moto['distancia_metros'] = resultado_carro['distancia_metros']

    print("[Bicicleta]")
    rotas_bike, t_bike = medir_tempo(calcular_rotas_bicicleta, graph_bike)
    print(f"  tempo total da função: {t_bike:.1f} ms\n")

    print("[Caminhada]")
    rotas_walk, t_walk = medir_tempo(calcular_rotas_caminhada, graph_walk)
    print(f"  tempo total da função: {t_walk:.1f} ms\n")

    # Tabela comparativa: tempo + custo por modal
    resultados_para_tabela = {
        'carro':     resultado_carro,
        'moto':      resultado_moto,
        'bicicleta': rotas_bike,
        'caminhada': rotas_walk,
    }
    gerar_tabela_comparativa(resultados_para_tabela)

    return {
        'cenario':        nome_cenario,
        'hora':           hora,
        'carro':          resultado_carro,
        'moto':           resultado_moto,
        'bicicleta':      rotas_bike,
        'caminhada':      rotas_walk,
        'graph_c':        graph_c,
        'benchmark_algo': resultado_carro['benchmark'],
    }


def imprimir_resumo_cenarios(cenarios_resultados):
    """
    Compara os dois cenários lado a lado, destacando a diferença
    de tempo de rota e de execução do algoritmo entre pico e fora de pico.

    Parâmetros:
        cenarios_resultados: lista com dois dicts retornados por executar_cenario
    """
    if len(cenarios_resultados) < 2:
        return

    a, b = cenarios_resultados[0], cenarios_resultados[1]

    print("\n" + "="*60)
    print("  ANÁLISE COMPARATIVA ENTRE CENÁRIOS")
    print("="*60)

    # Tempo de rota de carro
    t_a = a['carro']['tempo_seg'] / 60
    t_b = b['carro']['tempo_seg'] / 60
    diff_rota = t_a - t_b
    print(f"\nTempo de percurso (carro – Dijkstra):")
    print(f"  {a['cenario']}: {t_a:.1f} min")
    print(f"  {b['cenario']}: {t_b:.1f} min")
    print(f"  → pico é {diff_rota:.1f} min mais lento (congestionamento)")

    # Tempo de execução Dijkstra
    d_a = a['benchmark_algo']['dijkstra_ms']
    d_b = b['benchmark_algo']['dijkstra_ms']
    print(f"\nTempo de execução – Dijkstra:")
    print(f"  {a['cenario']}: {d_a:.1f} ms")
    print(f"  {b['cenario']}: {d_b:.1f} ms")

    # Tempo de execução A*
    as_a = a['benchmark_algo']['astar_ms']
    as_b = b['benchmark_algo']['astar_ms']
    print(f"\nTempo de execução – A*:")
    print(f"  {a['cenario']}: {as_a:.1f} ms")
    print(f"  {b['cenario']}: {as_b:.1f} ms")

    print(f"\nObs: diferença de rota entre cenários deve-se ao impacto do")
    print(f"congestionamento (leve/médio/pesado) nos pesos das arestas.")
    print("="*60 + "\n")


def main():
    print("=" * 60)
    print("  Sistema de Análise de Rotas Multimodais – Recife/PE")
    print("  Cine São Luiz → Faculdade Nova Roma")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Download dos grafos (feito uma única vez, reutilizado nos cenários)
    # ------------------------------------------------------------------
    print("\n[1/3] Baixando grafos do OpenStreetMap...")
    graph_carro_base = baixar_grafo_carro(COORDS_ORIGEM)
    graph_walk_base  = baixar_grafo_pedestre(COORDS_ORIGEM)
    graph_walk_base  = injetar_tempo_caminhada(graph_walk_base)

    graph_bike_base  = graph_walk_base.copy()
    graph_bike_base  = injetar_tempo_bicicleta(graph_bike_base)

    # ------------------------------------------------------------------
    # 2. Execução dos cenários de teste (análise empírica)
    # ------------------------------------------------------------------
    print("\n[2/3] Executando cenários de teste...")
    cenarios_resultados = []

    for hora, nome in CENARIOS:
        resultado = executar_cenario(
            graph_carro_base, graph_walk_base, graph_bike_base, hora, nome
        )
        cenarios_resultados.append(resultado)

    # ------------------------------------------------------------------
    # 3. Análise comparativa entre cenários
    # ------------------------------------------------------------------
    imprimir_resumo_cenarios(cenarios_resultados)

    # ------------------------------------------------------------------
    # 4. Geração do mapa usando o cenário de pico (cenário A)
    # ------------------------------------------------------------------
    print("[3/3] Gerando mapa interativo...")
    criar_mapa_interativo(
        cenarios_resultados,
        graph_walk_base,
        graph_bike_base,
        COORDS_ORIGEM,
        COORDS_DESTINO,
        ARQUIVO_MAPA,
    )


if __name__ == '__main__':
    main()
