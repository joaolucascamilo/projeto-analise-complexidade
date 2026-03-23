"""
Módulo de cálculo de rota para moto.

A moto usa a mesma malha viária do carro (grafo 'drive'),
mas percorre as ruas a uma velocidade média maior (50 km/h).
"""

from src.utils.grafo import VELOCIDADE_PADRAO_MOTO_KMH


def calcular_rota_moto(graph, rota_carro):
    """
    Estima o tempo de percurso de moto a partir da rota já calculada para carro.

    A moto trafega pelas mesmas vias, mas com velocidade constante de 50 km/h,
    sem depender dos dados dinâmicos da CTTU.

    Parâmetros:
        graph:      grafo viário de carros (MultiDiGraph)
        rota_carro: lista de nós da rota do carro (mais rápida)

    Retorna:
        dict com chaves:
            'rota':      lista de nós (igual à rota do carro)
            'tempo_seg': tempo total estimado em segundos
    """
    velocidade_ms = VELOCIDADE_PADRAO_MOTO_KMH / 3.6
    tempo_total = 0.0

    # Percorre cada par de nós consecutivos e soma o comprimento das arestas
    for u, v in zip(rota_carro[:-1], rota_carro[1:]):
        edge_data = graph.get_edge_data(u, v)
        if edge_data:
            # Escolhe a aresta de menor comprimento quando há paralelas
            comprimento = min(d.get('length', 0) for d in edge_data.values())
            tempo_total += comprimento / velocidade_ms

    print(f"Moto - rota mais rápida:  {tempo_total / 60:.2f} min")
    print(f"  (mesma via do carro a {VELOCIDADE_PADRAO_MOTO_KMH} km/h)\n")

    return {
        'rota':      rota_carro,
        'tempo_seg': tempo_total,
    }
