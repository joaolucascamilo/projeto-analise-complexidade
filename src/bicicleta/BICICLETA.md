# Rota de Bicicleta

**Percurso:** Cine São Luiz (Centro) -> Faculdade Nova Roma (Boa Viagem)

## Rotas mapeadas

| Rota | Percurso                  | Tempo estimado |
|------|---------------------------|---------------|
| 1    | Via Mangue                | 34 min        |
| 2    | Av. Boa Viagem            | 33 min        |
| 3    | Rua Arquiteto Luiz Nunes  | 39 min        |

## Como funciona

O módulo `algoritmo.py` calcula as três rotas usando **Dijkstra** com o
peso `tempo_bicicleta` (distância da aresta dividida por 20 km/h em m/s).

### Grafo utilizado

Usa o grafo de **pedestres** (`network_type='walk'`) como base, pois ele inclui:
- Ciclovias e calçadas largas
- Atalhos e passagens que carros não podem usar
- Caminhos ao longo de parques e orla

### Waypoints por rota

Cada rota é forçada a passar por um waypoint intermediário,
garantindo que o algoritmo siga o trajeto real e não apenas
o caminho mais curto em linha reta.

| Rota | Waypoint intermediário | Coordenada aprox. |
|------|------------------------|-------------------|
| 1    | Via Mangue             | -8.090, -34.895   |
| 2    | Av. Boa Viagem         | -8.107, -34.900   |
| 3    | Rua Arq. Luiz Nunes    | -8.112, -34.902   |

Se o waypoint não for encontrado pelo nome no OSM, o algoritmo
registra um aviso e calcula a rota direta origem->destino.

### Velocidade adotada

Velocidade média de **20 km/h** - valor padrão para ciclistas urbanos
em vias com cruzamentos semaforizados.

## Complexidade

- Dijkstra: **O((V + E) log V)**
- Concatenação de waypoints: **O(k · (V + E) log V)**, onde k = número de trechos
- Cálculo de tempo da rota: **O(n)**, onde n = número de nós no caminho

## Dependências

- [`src/utils/grafo.py`](../utils/grafo.py): download do grafo e injeção de `tempo_bicicleta`
- [`src/utils/helpers.py`](../utils/helpers.py): `no_na_rua`, `rota_via_waypoints`, `tempo_rota`
