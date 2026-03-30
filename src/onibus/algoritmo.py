"""
Módulo de cálculo de rotas de ônibus.

ATENÇÃO: este módulo está em desenvolvimento.

Para calcular rotas de transporte público com precisão, é necessário
integrar dados GTFS (General Transit Feed Specification) fornecidos
pelo Grande Recife Consórcio de Transporte.

Os dados GTFS contêm:
  - routes.txt    -> linhas de ônibus e BRT
  - trips.txt     -> viagens por linha e sentido
  - stop_times.txt -> horários de cada parada em cada viagem
  - stops.txt     -> localização geográfica (lat/lon) das paradas
  - shapes.txt    -> traçado geográfico de cada linha

Referência: https://www.granderecife.pe.gov.br/
"""


def calcular_rotas_onibus():
    """
    Placeholder para o cálculo de rotas de ônibus.

    Quando implementado, este método deverá:
    1. Carregar os arquivos GTFS do Grande Recife
    2. Construir um grafo multimodal integrando paradas e linhas
    3. Aplicar Dijkstra ou A* com pesos de tempo de viagem e espera
    4. Retornar as rotas com custo tarifário (Anéis A, B, G)

    Levantamento de rotas (Google Maps):
      Rota 1 - Setúbal (Príncipe):           ~34 min
      Rota 2 - Catamarã:                     ~35 min
      Rota 3 - TI Recife / TI Joana Bezerra: ~38 min
      Rota 4 - Candeias:                     ~41 min

    Retorna:
        NotImplementedError até a integração GTFS ser concluída
    """
    raise NotImplementedError(
        "O módulo de ônibus ainda não foi implementado.\n"
        "É necessário baixar e processar os dados GTFS do Grande Recife.\n"
        "Consulte: https://www.granderecife.pe.gov.br/"
    )
