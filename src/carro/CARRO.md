# Rota de Carro

**Percurso:** Cine São Luiz (Centro) -> Faculdade Nova Roma (Boa Viagem)

## Rotas mapeadas

| Rota | Percurso | Tempo estimado |
|------|----------|---------------|
| 1    | PE-009   | 18 min        |
| 2    | Av. Domingos Ferreira | 18 min |
| 3    | Rua Imperial e Av. Domingos Ferreira | 18 min |

## Como funciona

O módulo `algoritmo.py` usa o **algoritmo de Dijkstra** com dois critérios:

### Rota mais rápida (`rota_tempo`)
- Peso das arestas: `tempo_dinamico` (segundos)
- Os tempos são calculados com base nas velocidades reais medidas pelos fotossensores da CTTU no horário de pico das 8h
- Arestas sem radar próximo recebem velocidade padrão de **40 km/h**

### Rota mais curta (`rota_distancia`)
- Peso das arestas: `length` (metros, dado nativo do OSMnx)
- Ignora condições de tráfego; prioriza o menor trajeto físico

## Complexidade

O algoritmo de Dijkstra tem complexidade **O((V + E) log V)**, onde:
- V = número de vértices (cruzamentos)
- E = número de arestas (segmentos de via)

## Dependências

- [`src/utils/grafo.py`](../utils/grafo.py): download do grafo e injeção de pesos da CTTU
- [`src/utils/helpers.py`](../utils/helpers.py): conversão de rota para coordenadas
