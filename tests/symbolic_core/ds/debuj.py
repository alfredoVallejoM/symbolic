import sys
import math
import time
from multiprocessing import Pool, cpu_count, Lock
from sympy import isprime

# =========================================================
# 1. HERRAMIENTAS MATEMÁTICAS BLINDADAS
# =========================================================

# Escudo de Primos (Primorial hasta 113)
PRIMORIAL_SHIELD = 3 * 5 * 7 * 11 * 13 * 17 * 19 * 23 * 29 * 31 * 37 * 41 * 43 * 47 * 53 * 59 * 61 * 67 * 71 * 73 * 79 * 83 * 89 * 97 * 101 * 103 * 107 * 109 * 113

def is_perfect_square(n):
    """Filtro Anti-Cuadrados (O(1))."""
    if n < 0: return False
    if n == 0: return True
    sqrt_n = math.isqrt(n)
    return sqrt_n * sqrt_n == n

def matrix_mul_mod(A, B, m):
    """Multiplicación 2x2 optimizada."""
    return [
        [(A[0][0]*B[0][0] + A[0][1]*B[1][0]) % m, (A[0][0]*B[0][1] + A[0][1]*B[1][1]) % m],
        [(A[1][0]*B[0][0] + A[1][1]*B[1][0]) % m, (A[1][0]*B[0][1] + A[1][1]*B[1][1]) % m]
    ]

def chebyshev_T_mod(n, x, m):
    """Motor Chebyshev (Bitwise)."""
    if n == 0: return 1
    if n == 1: return x % m
    
    base = [[(2 * x) % m, -1], [1, 0]]
    res = [[1, 0], [0, 1]]
    p = n - 1
    while p > 0:
        if p & 1: 
            res = matrix_mul_mod(res, base, m)
        base = matrix_mul_mod(base, base, m)
        p >>= 1 
    return (res[0][0] * x + res[0][1]) % m

ORTHOGONAL_BASES = [
    3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 
    59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113
]

def get_adaptive_strength(M):
    """Escalado logarítmico."""
    k = 5 + (M.bit_length() // 5)
    return min(k, len(ORTHOGONAL_BASES))

def dipole_check_kernel(M):
    """
    KERNEL V4 (CORREGIDO): GCD INTELIGENTE
    """
    if M <= 2 or M % 2 != 0: return False
    L, R = M - 1, M + 1

    # CAPA 1: Anti-Cuadrados
    if is_perfect_square(L) or is_perfect_square(R):
        return False

    # CAPA 2: Compuerta GCD (CORREGIDA)
    # Si gcd > 1, solo es compuesto si gcd != N.
    # Si gcd == N, significa que N es uno de los primos del escudo (5, 7, 11...),
    # así que lo dejamos pasar a la prueba espectral (o lo aprobamos).
    
    g_left = math.gcd(L, PRIMORIAL_SHIELD)
    if g_left > 1 and g_left != L: 
        return False # Es compuesto (múltiplo)
        
    g_right = math.gcd(R, PRIMORIAL_SHIELD)
    if g_right > 1 and g_right != R:
        return False # Es compuesto (múltiplo)

    # CAPA 3: Topodinámica Espectral
    MOD_RING = 2 * (M * M - 1)
    limit = get_adaptive_strength(M)
    
    for i in range(limit):
        x = ORTHOGONAL_BASES[i]
        
        # Pequeña optimización: si x divide a M-1 o M+1, la prueba es trivial.
        # Pero el escudo GCD ya filtra la mayoría.
        
        T_left = chebyshev_T_mod(L, x, MOD_RING)
        T_right = chebyshev_T_mod(R, x, MOD_RING)
        
        # Ecuación Maestra
        if ((M + 1) * T_left + (M - 1) * T_right) % MOD_RING != (2 * M * x) % MOD_RING:
            return False
            
    return True

# =========================================================
# 2. WORKER CON REPORTE INMEDIATO
# =========================================================

def audit_worker_realtime(args):
    """
    Worker que imprime errores AL INSTANTE.
    """
    batch_id, start, end = args
    
    curr = start
    if curr % 6 != 0: curr += (6 - (curr % 6))
    
    errors_found = 0
    
    while curr < end:
        M = curr
        curr += 6
        
        # 1. Teoría (Tu Algoritmo)
        res_theory = dipole_check_kernel(M)
        
        # 2. Verdad (SymPy) - SIEMPRE calculada para verificar falsedad y verdad
        is_p1 = isprime(M-1)
        is_p2 = isprime(M+1)
        res_truth = is_p1 and is_p2
        
        # 3. Comparación
        if res_theory != res_truth:
            errors_found += 1
            # IMPRESIÓN INMEDIATA (flush=True fuerza la salida a la consola)
            err_type = "FALSO POSITIVO (Dijiste SÍ, es NO)" if res_theory else "FALSO NEGATIVO (Dijiste NO, es SÍ)"
            print(f"🚨 ERROR CRÍTICO DETECTADO: M={M} | Teoría={res_theory} vs Verdad={res_truth} | {err_type}", flush=True)
            
    return (batch_id, errors_found)

# =========================================================
# 3. ORQUESTADOR PRINCIPAL
# =========================================================

def run_realtime_audit():
    # OBJETIVO MASIVO
    TARGET_M = 10_000_000_000 # 10 Millones
    CORES = cpu_count()
    # Más lotes = feedback de progreso más suave
    NUM_BATCHES = CORES * 50000
    step = TARGET_M // NUM_BATCHES
    
    print(f"[*] INICIANDO AUDITORÍA V4 (TIEMPO REAL)")
    print(f"[*] Corrección GCD: ACTIVADA (Permite primos pequeños)")
    print(f"[*] Reporte: INMEDIATO (Los errores saldrán al instante)")
    print(f"[*] Objetivo: {TARGET_M:,} casos")
    print(f"[*] Numero de Batches: {NUM_BATCHES:,} de tamaño {step:,}")
    print("-" * 70)
    
    
    tasks = []
    for i in range(NUM_BATCHES):
        s = 6 + (i * step)
        e = 6 + ((i + 1) * step)
        if i == NUM_BATCHES - 1: e = TARGET_M + 1
        tasks.append((i+1, s, e))
    
    start_time = time.time()
    total_discrepancies = 0
    
    # Pool
    with Pool(processes=CORES) as pool:
        for batch_id, count in pool.imap_unordered(audit_worker_realtime, tasks):
            # Solo imprimimos el check verde si NO hubo errores en ese lote
            # Si hubo errores, ya se imprimieron dentro del worker.
            if count == 0:
                print(f"   -> [Lote {batch_id}/{NUM_BATCHES}] Limpio. ✅")
            else:
                print(f"   -> [Lote {batch_id}/{NUM_BATCHES}] Finalizado con {count} ERRORES ❌")
                total_discrepancies += count

    end_time = time.time()
    
    print("-" * 70)
    print(f"[*] Auditoría completada en {end_time - start_time:.2f}s")
    
    if total_discrepancies == 0:
        print("\n🏆 PERFECCIÓN TOTAL.")
        print("   Se han verificado tanto los positivos como los negativos.")
        print("   No hay discrepancias con la base de datos de primalidad.")
    else:
        print(f"\n❌ AUDITORÍA FALLIDA: {total_discrepancies} ERRORES TOTALES.")

if __name__ == '__main__':
    run_realtime_audit()