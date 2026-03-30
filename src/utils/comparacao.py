"""
Geração da tabela comparativa entre os modais de transporte.

Consolida os resultados de todos os algoritmos em uma única view,
mostrando tempo estimado, distância e custo financeiro por rota.

Referências de custo:
  - Carro:     R$6,90/L gasolina, consumo médio 10 km/L -> R$0,69/km
  - Moto:      R$6,90/L gasolina, consumo médio 20 km/L -> R$0,35/km
  - Ônibus:    Tarifa única Recife/PE -> R$4,30
  - Bicicleta: Custo zero
  - Caminhada: Custo zero
"""

# Custo operacional por modal (R$ por km, exceto ônibus que é tarifa fixa)
CUSTO_KM_CARRO    = 0.69   # R$/km
CUSTO_KM_MOTO     = 0.35   # R$/km
CUSTO_FIXO_ONIBUS = 4.30   # R$ (tarifa única Recife)
CUSTO_BICICLETA   = 0.00
CUSTO_CAMINHADA   = 0.00


def calcular_custo_variavel(distancia_metros, custo_por_km):
    """
    Calcula o custo financeiro com base na distância percorrida.

    Parâmetros:
        distancia_metros: distância em metros
        custo_por_km:     custo em R$ por quilômetro

    Retorna:
        Custo total em reais (float)
    """
    return (distancia_metros / 1000) * custo_por_km


def gerar_tabela_comparativa(resultados):
    """
    Imprime no terminal uma tabela comparando todos os modais.

    Parâmetros:
        resultados: dict com chaves:
            'carro'     -> dict com 'tempo_seg' e 'distancia_metros'
            'moto'      -> dict com 'tempo_seg' e 'distancia_metros'
            'bicicleta' -> lista de dicts com 'nome', 'tempo_seg', 'distancia_metros'
            'caminhada' -> lista de dicts com 'nome', 'tempo_seg', 'distancia_metros'

    Retorna:
        Lista de dicts com as linhas da tabela (para uso programático)
    """
    linhas = []

    # --- Carro ---
    r = resultados['carro']
    dist_km = r['distancia_metros'] / 1000
    custo   = calcular_custo_variavel(r['distancia_metros'], CUSTO_KM_CARRO)
    linhas.append({
        'modal':       'Carro (mais rápido)',
        'tempo_min':   r['tempo_seg'] / 60,
        'distancia_km': dist_km,
        'custo_r$':    custo,
    })

    # --- Moto ---
    r = resultados['moto']
    dist_km = r.get('distancia_metros', resultados['carro']['distancia_metros']) / 1000
    custo   = calcular_custo_variavel(dist_km * 1000, CUSTO_KM_MOTO)
    linhas.append({
        'modal':        'Moto',
        'tempo_min':    r['tempo_seg'] / 60,
        'distancia_km': dist_km,
        'custo_r$':     custo,
    })

    # --- Bicicleta ---
    for item in resultados.get('bicicleta', []):
        dist_km = item.get('distancia_metros', 0) / 1000
        linhas.append({
            'modal':        f"Bicicleta - {item['nome']}",
            'tempo_min':    item['tempo_min'],
            'distancia_km': dist_km,
            'custo_r$':     CUSTO_BICICLETA,
        })

    # --- Caminhada ---
    for item in resultados.get('caminhada', []):
        dist_km = item.get('distancia_metros', 0) / 1000
        linhas.append({
            'modal':        f"Caminhada - {item['nome']}",
            'tempo_min':    item['tempo_min'],
            'distancia_km': dist_km,
            'custo_r$':     CUSTO_CAMINHADA,
        })

    # --- Ônibus (estimativa fixa do README) ---
    linhas.append({
        'modal':        'Ônibus (Setúbal - est.)',
        'tempo_min':    34.0,
        'distancia_km': None,
        'custo_r$':     CUSTO_FIXO_ONIBUS,
    })

    _imprimir_tabela(linhas)
    return linhas


def _imprimir_tabela(linhas):
    """Formata e imprime a tabela comparativa no terminal."""
    cabecalho = f"{'Modal':<35} {'Tempo (min)':>12} {'Distância (km)':>16} {'Custo (R$)':>12}"
    separador = "-" * len(cabecalho)

    print("\n" + separador)
    print("  COMPARATIVO DE ROTAS - Cine São Luiz -> Faculdade Nova Roma")
    print(separador)
    print(cabecalho)
    print(separador)

    for linha in linhas:
        dist = f"{linha['distancia_km']:.2f}" if linha['distancia_km'] else "   -"
        print(
            f"{linha['modal']:<35} "
            f"{linha['tempo_min']:>12.1f} "
            f"{dist:>16} "
            f"{linha['custo_r$']:>12.2f}"
        )

    print(separador + "\n")
