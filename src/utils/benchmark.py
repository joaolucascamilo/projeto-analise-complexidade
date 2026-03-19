"""
Utilitários de medição de desempenho (benchmarking).

Permite registrar o tempo de execução de funções e comparar
algoritmos em diferentes cenários de teste.
"""

import time


def medir_tempo(funcao, *args, **kwargs):
    """
    Executa uma função e mede seu tempo de execução.

    Parâmetros:
        funcao: função a ser medida
        *args, **kwargs: argumentos repassados para a função

    Retorna:
        Tupla (resultado, tempo_ms) onde tempo_ms é o tempo em milissegundos
    """
    inicio = time.perf_counter()
    resultado = funcao(*args, **kwargs)
    fim = time.perf_counter()
    tempo_ms = (fim - inicio) * 1000
    return resultado, tempo_ms


def comparar_algoritmos(nome_a, funcao_a, nome_b, funcao_b, *args, **kwargs):
    """
    Executa dois algoritmos com os mesmos argumentos e compara o tempo.

    Parâmetros:
        nome_a:   nome do primeiro algoritmo (para exibição)
        funcao_a: função do primeiro algoritmo
        nome_b:   nome do segundo algoritmo
        funcao_b: função do segundo algoritmo
        *args, **kwargs: argumentos repassados para ambas as funções

    Retorna:
        dict com chaves:
            'resultado_a', 'resultado_b': retornos das funções
            'tempo_ms_a', 'tempo_ms_b': tempos em milissegundos
            'mais_rapido': nome do algoritmo mais rápido
            'diferenca_ms': diferença absoluta em ms
    """
    resultado_a, tempo_a = medir_tempo(funcao_a, *args, **kwargs)
    resultado_b, tempo_b = medir_tempo(funcao_b, *args, **kwargs)

    mais_rapido = nome_a if tempo_a <= tempo_b else nome_b
    diferenca   = abs(tempo_a - tempo_b)

    print(f"  {nome_a}: {tempo_a:.1f} ms")
    print(f"  {nome_b}: {tempo_b:.1f} ms")
    print(f"  → mais rápido: {mais_rapido} (por {diferenca:.1f} ms)")

    return {
        'resultado_a':   resultado_a,
        'resultado_b':   resultado_b,
        'tempo_ms_a':    tempo_a,
        'tempo_ms_b':    tempo_b,
        'mais_rapido':   mais_rapido,
        'diferenca_ms':  diferenca,
    }
