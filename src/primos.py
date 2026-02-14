import sys
import math
import time
from multiprocessing import Pool, cpu_count
from sympy import isprime

class PureGraphEngine:
    """
    Motor Topodinámico Puro.
    Opera exclusivamente con la Matriz de Adyacencia T(x).
    Sin reducciones a trazas o cadenas de Lucas.
    """

    @staticmethod
    def _jacobi(a, n):
        """Jacobi Bitwise."""
        if a == 0: return 0
        if a == 1: return 1
        a %= n
        t = 1
        while a != 0:
            while (a & 1) == 0:
                a >>= 1
                if (n & 7) in (3, 5): t = -t
            a, n = n, a
            if (a & 3) == 3 and (n & 3) == 3: t = -t
            a %= n
        return t if n == 1 else 0

    @staticmethod
    def _mat_mul(A, B, n):
        """
        Producto Tensorial de Grafos (Composición).
        """
        # A, B = [a, b, c, d]
        return [
            (A[0]*B[0] + A[1]*B[2]) % n,
            (A[0]*B[1] + A[1]*B[3]) % n,
            (A[2]*B[0] + A[3]*B[2]) % n,
            (A[2]*B[1] + A[3]*B[3]) % n
        ]

    @staticmethod
    def _mat_sq(A, n):
        """Iteración del Grafo."""
        # A^2 optimizado
        a, b, c, d = A
        bc = (b * c) % n
        return [
            (a*a + bc) % n,
            (b * (a + d)) % n,
            (c * (a + d)) % n,
            (d*d + bc) % n
        ]

    @staticmethod
    def _mat_pow(A, exp, n):
        """Evolución Topológica."""
        res = [1, 0, 0, 1] # Identidad
        base = A
        while exp > 0:
            if exp & 1:
                res = PureGraphEngine._mat_mul(res, base, n)
            base = PureGraphEngine._mat_sq(base, n)
            exp >>= 1
        return res

    @staticmethod
    def analyze_graph(n):
        """
        Análisis Estructural del Grafo T(x).
        """
        if n == 2 or n == 3: return True
        if n < 2 or (n & 1) == 0: return False
        if math.isqrt(n)**2 == n: return False

        # 1. Calibración de Energía (Buscando Inercia)
        # Necesitamos un x tal que x^2-4 sea no-residuo.
        x = 0
        found = False
        for k in range(100):
            cand = k + 3
            # Discriminante del Grafo T(x) con Q=1
            disc = cand*cand - 4
            
            g = math.gcd(disc, n)
            if g > 1 and g < n: return False # Fractura algebraica
            
            if PureGraphEngine._jacobi(disc, n) == -1:
                x = cand
                found = True
                break
        
        if not found: return False 

        # 2. Construcción del Operador
        # T = [[x, -1], [1, 0]]
        # Nota: -1 mod n es n-1
        T = [x, n - 1, 1, 0]

        # 3. Descomposición del Ciclo
        # Ciclo ideal: N+1
        delta = n + 1
        s = 0
        while (delta & 1) == 0:
            delta >>= 1
            s += 1
        d = delta

        # 4. Estado Base
        # G_d = T^d
        G = PureGraphEngine._mat_pow(T, d, n)

        # Definimos las matrices topológicas clave
        Identity = [1, 0, 0, 1]
        Antipode = [n - 1, 0, 0, n - 1] # -I = [[-1, 0], [0, -1]]

        # CHECK 1: Resonancia Base
        # Si G == I, el ciclo se cerró en d.
        if G == Identity:
            return True
        # Si G == -I, estamos en antípodas (buen camino).
        if G == Antipode:
            return True

        # CHECK 2: Ascenso Diádico
        # Buscamos la transición -I -> I
        for _ in range(s - 1):
            G = PureGraphEngine._mat_sq(G, n)
            
            if G == Antipode:
                return True
            if G == Identity:
                return False # Fractura: Llegamos a I sin pasar por -I

        return False

# ==============================================================================
# AUDITORÍA (10^7)
# ==============================================================================

def audit_worker(args):
    _, start, end = args
    if (start & 1) == 0: start += 1
    
    fails = []
    curr = start
    while curr < end:
        res_graph = PureGraphEngine.analyze_graph(curr)
        res_true = isprime(curr) # Ground truth
        
        if res_graph != res_true:
            err = "FALSO POSITIVO" if res_graph else "FALSO NEGATIVO"
            fails.append((curr, err))
            print(f"🚨 FRACTURA: N={curr} | {err}", flush=True)
            
        curr += 2
    return fails

def run_pure_audit():
    TARGET = 10_000_000
    CORES = cpu_count()
    BATCHES = CORES * 8
    
    print(f"[*] INICIANDO AUDITORÍA TOPODINÁMICA PURA (MATRICIAL)")
    print(f"[*] Objeto: Matriz T(x) Completa (Q=1).")
    print(f"[*] Criterio: Existencia de matriz Antípodas (-I) en la órbita.")
    print("-" * 65)
    
    step = TARGET // BATCHES
    tasks = [(i+1, 2 + i*step, 2 + (i+1)*step) for i in range(BATCHES)]
    if tasks: tasks[-1] = (BATCHES, tasks[-1][1], TARGET)
    
    t0 = time.time()
    errs = 0
    with Pool(CORES) as pool:
        for i, res in enumerate(pool.imap_unordered(audit_worker, tasks)):
            errs += len(res)
            if i % 10 == 0: print(f"   -> Progreso: Lotes {i} OK", flush=True)
            
    print("-" * 65)
    print(f"[*] Tiempo: {time.time()-t0:.2f}s")
    if errs == 0:
        print("\n🏆 GRAFOS VALIDADOS: CERO ERRORES.")
    else:
        print(f"\n❌ ERRORES DETECTADOS: {errs}")

if __name__ == '__main__':
    run_pure_audit()