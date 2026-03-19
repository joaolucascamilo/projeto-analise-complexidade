# Rota de Ônibus

**Percurso:** Cine São Luiz (Centro) -> Faculdade Nova Roma (Boa Viagem)

## Rotas mapeadas

| Rota | Percurso                      | Tempo estimado |
|------|-------------------------------|---------------|
| 1    | Setúbal (Príncipe)            | 34 min        |
| 2    | Catamarã                      | 35 min        |
| 3    | TI Recife / TI Joana Bezerra  | 38 min        |
| 4    | Candeias                      | 41 min        |

## Status

> **Em desenvolvimento** - aguardando integração com dados GTFS do Grande Recife.

## O que é necessário para implementar

### 1. Dados GTFS (General Transit Feed Specification)

Baixar os arquivos do Grande Recife Consórcio de Transporte:
- `routes.txt` - linhas de ônibus e BRT
- `trips.txt` - viagens por linha e sentido
- `stop_times.txt` - horários de cada parada em cada viagem
- `stops.txt` - localização geográfica das paradas
- `shapes.txt` - traçado geográfico das linhas

**Fonte:** https://www.granderecife.pe.gov.br/

### 2. Construção do grafo multimodal

O grafo de transporte público terá uma estrutura diferente dos outros modais:
- **Nós:** paradas de ônibus, terminais e interseções com rotas de caminhada
- **Arestas de transporte:** tempo de deslocamento entre paradas (dado GTFS)
- **Arestas de espera:** tempo médio de espera na parada (headway da linha)
- **Arestas de caminhada:** conexão entre o usuário e as paradas mais próximas

### 3. Pesos das arestas

| Tipo de aresta | Peso |
|----------------|------|
| Deslocamento a bordo | `stop_times.departure_time` - `stop_times.arrival_time` |
| Espera na parada | `headway` (intervalo entre ônibus) ÷ 2 |
| Caminhada até a parada | distância / 5 km/h |
| Custo tarifário | Anel A / B / G (Grande Recife) |

### 4. Algoritmo sugerido

**Dijkstra** com peso combinado de tempo + espera, ou
**A\*** com heurística de distância de Haversine até o destino.

## Complexidade esperada

Com grafo GTFS integrado ao OSM:
- V ≈ número de paradas + cruzamentos relevantes
- E ≈ segmentos de linha + arestas de caminhada
- Dijkstra: **O((V + E) log V)**

## Dependências futuras

- [`src/utils/grafo.py`](../utils/grafo.py)
- [`src/utils/helpers.py`](../utils/helpers.py)
- Biblioteca `gtfs-kit` ou `pandas` para processar os arquivos GTFS
