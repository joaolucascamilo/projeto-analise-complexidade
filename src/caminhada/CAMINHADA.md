# Rota a Pé (Caminhada)

**Percurso:** Cine São Luiz (Centro) -> Faculdade Nova Roma (Boa Viagem)

## Rotas mapeadas

| Rota | Percurso        | Tempo estimado |
|------|-----------------|---------------|
| 1    | Av. Domingos Ferreira | ~2h    |
| 2    | Rua Imperial    | ~2h 1min      |

## Como funciona

O módulo `algoritmo.py` usa **Dijkstra** com o peso `tempo_caminhada`
(distância da aresta dividida por 5 km/h em m/s).

### Grafo utilizado

Grafo de **pedestres** (`network_type='walk'`), que inclui calçadas,
passagens, parques e caminhos não disponíveis para veículos.

### Waypoints por rota

| Rota | Waypoints intermediários                       |
|------|------------------------------------------------|
| 1    | Av. Eng. Domingos Ferreira                     |
| 2    | Av. Sul Gov. Cid Sampaio + Av. Mal. Mascarenhas de Morais |

Se um waypoint não for localizado pelo nome no OSM, o trecho correspondente
é ignorado e o algoritmo calcula o caminho direto entre os pontos restantes.

### Velocidade adotada

Velocidade média de **5 km/h** - valor padrão para caminhada em ambiente urbano.

## Complexidade

- Dijkstra: **O((V + E) log V)**
- Com waypoints, o algoritmo é executado uma vez por trecho, totalizando
  **O(k · (V + E) log V)**, onde k = número de trechos

## Dependências

- [`src/utils/grafo.py`](../utils/grafo.py): download do grafo e injeção de `tempo_caminhada`
- [`src/utils/helpers.py`](../utils/helpers.py): `no_na_rua`, `rota_via_waypoints`, `tempo_rota`
