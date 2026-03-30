# Rota de Moto

**Percurso:** Cine São Luiz (Centro) -> Faculdade Nova Roma (Boa Viagem)

## Rotas mapeadas

| Rota | Percurso | Tempo estimado |
|------|----------|---------------|
| 1    | PE-009   | 15 min        |
| 2    | Av. Domingos Ferreira | 15 min |
| 3    | Rua Imperial e Av. Domingos Ferreira | 15 min |

## Como funciona

O módulo `algoritmo.py` reutiliza a **rota mais rápida do carro** e recalcula o tempo com a velocidade média de moto.

### Premissas
- A moto trafega pela mesma malha viária do carro (`network_type='drive'`)
- Velocidade constante de **50 km/h** (sem variação por tráfego)
- Não usa os dados dinâmicos da CTTU, é uma estimativa simplificada

### Por que não usar Dijkstra separado?
A moto percorre exatamente as mesmas vias que o carro.
Recalcular o Dijkstra com velocidade uniforme produziria o mesmo caminho,
pois os pesos relativos entre as arestas não mudariam.
O tempo final é apenas `distância / velocidade_moto`.

## Complexidade

A função itera sobre os nós da rota em tempo **O(k)**, onde k é o número de nós no caminho.

## Dependências

- [`src/carro/algoritmo.py`](../carro/algoritmo.py): fornece a rota base
- [`src/utils/grafo.py`](../utils/grafo.py): constante `VELOCIDADE_PADRAO_MOTO_KMH`
