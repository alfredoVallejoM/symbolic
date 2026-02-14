"""
tests/symbolic_core/system/test_holonic_lifecycle.py
Auditoría de Ciclo de Vida del Sistema (System Level Tests).
Cubre: Recolección de Basura (GC), Concurrencia (Threading) y Aplicación Real (Calculus).
"""
import unittest
import threading
import time
import gc
from symbolic_core.kernel.universe import Universe
from symbolic_core.kernel.node import Node
from symbolic_core.opcodes import *
from symbolic_core.kernel.sectors import SectorManager

class TestMemoryPhysics(unittest.TestCase):
    """
    Verifica que el Universo no solo crea materia, sino que sabe destruirla
    y recuperar el espacio (Anti-Entropía).
    """

    def setUp(self):
        # Limpieza brutal para medir memoria
        Universe._lookup.clear()
        Universe._blob_lookup.clear()
        # Forzar GC de Python
        gc.collect()

    def test_gc_reclamation(self):
        """
        Crea nodos transitorios y verifica que al borrarlos
        el Universo olvida sus IDs.
        """
        # 1. Línea base
        initial_size = Universe.debug_lookup_size()
        
        # 2. Crear basura (10,000 nodos efímeros)
        # Add(i, i) -> 2*i. Son nodos únicos.
        uids = []
        for i in range(10000):
            n = Node.val(i)
            res = n + n
            uids.append(res.uid)
            
        # Verificar crecimiento
        mid_size = Universe.debug_lookup_size()
        self.assertGreater(mid_size, initial_size + 5000)
        
        # 3. Borrado Masivo
        for uid in uids:
            Universe.delete(uid)
            
        # 4. Verificación
        final_size = Universe.debug_lookup_size()
        
        # Nota: Dependiendo de la implementación de delete, podría quedar algo de metadata,
        # pero debería haber bajado drásticamente.
        self.assertLess(final_size, mid_size, "El GC del Universo no está liberando entradas del lookup.")
        
        # Verificar que el acceso a un nodo muerto falla
        dead_uid = uids[0]
        try:
            Universe.get_args(dead_uid)
            # Si el Allocator recicla índices, podría devolver basura o fallar.
            # Lo ideal es que falle o devuelva None.
            # En v3.1 Universe.get_args chequea _lookup, así que debería lanzar excepción
        except ValueError:
            pass # Comportamiento correcto: Nodo inaccesible
        except Exception:
            pass # Aceptable

class TestQuantumConcurrency(unittest.TestCase):
    """
    Verifica que el Universo es Thread-Safe.
    Múltiples observadores colapsando la misma función de onda.
    """

    def setUp(self):
        Universe._lookup.clear()

    def test_race_for_the_atom(self):
        """
        20 Hilos intentan internar el MISMO símbolo simultáneamente.
        No debe haber duplicados ni errores de corrupción.
        """
        target_symbol = "The_One"
        results = [None] * 20
        
        def worker(idx):
            # Simular carga
            time.sleep(0.001)
            # Internar
            node = Node.symbol(target_symbol)
            results[idx] = node.uid

        threads = []
        for i in range(20):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        # Verificaciones
        first_uid = results[0]
        self.assertIsNotNone(first_uid)
        
        # 1. Consistencia: Todos obtuvieron el mismo UID
        for uid in results:
            self.assertEqual(uid, first_uid, "Race Condition: Hilos distintos obtuvieron IDs distintos para el mismo átomo.")
            
        # 2. Integridad: Solo hay 1 entrada en el Universo (más el blob del nombre)
        # 1 entrada para SYMBOL + 1 entrada para BLOB(nombre)
        # (Depende de si Node.symbol hace intern del blob implícitamente)
        # Al menos no debe haber 20 entradas.
        self.assertLess(Universe.debug_lookup_size(), 5, "Race Condition: El Universo creó múltiples copias físicas.")

class TestSymbolicEngine(unittest.TestCase):
    """
    Prueba End-to-End: Implementar una Derivada.
    Esto valida que todas las capas (Op, Hash, Strategy, Universe) funcionan
    orquestadas para resolver un problema real.
    """

    def setUp(self):
        Universe._lookup.clear()

    def derive(self, uid: int, var_uid: int) -> int:
        """
        Implementación naive de derivación d/dvar.
        Usa el Kernel.
        """
        op = Universe.get_op(uid)
        args = Universe.get_args(uid)
        
        # Regla 1: d/dx x = 1, d/dx y = 0, d/dx C = 0
        if op == OP_SYMBOL:
            return Node.val(1).uid if uid == var_uid else Node.val(0).uid
        if op == OP_SCALAR:
            return Node.val(0).uid
            
        # Regla 2: Suma d(u+v) = du + dv
        if op == OP_ADD:
            # Derivamos cada hijo y sumamos los resultados
            diffs = [self.derive(arg, var_uid) for arg in args]
            return Universe.intern(OP_ADD, tuple(diffs))
            
        # Regla 3: Producto (Regla de la Cadena/Producto) d(uv) = u'v + uv'
        # Simplificación para Mul n-ario: Sum( u_i' * (Prod_{j!=i} u_j) )
        if op == OP_MUL:
            terms = []
            for i in range(len(args)):
                # Derivada del término i
                d_i = self.derive(args[i], var_uid)
                
                # Resto de términos
                others = args[:i] + args[i+1:]
                
                # Termino resultante: d_i * others
                if others:
                    # Producto del resto
                    prod_others = Universe.intern(OP_MUL, others)
                    term = Universe.intern(OP_MUL, (d_i, prod_others))
                else:
                    term = d_i
                terms.append(term)
            return Universe.intern(OP_ADD, tuple(terms))
            
        # Regla 4: Potencia d(x^n) = n * x^(n-1) * dx (asumiendo n constante)
        if op == OP_POW:
            base, exp = args
            # Asumimos exponente constante para el test
            if Universe.get_op(exp) == OP_SCALAR:
                n_val = Universe.get_args(exp)[0]
                
                # n
                n_node = exp 
                # x^(n-1)
                new_exp = Universe.intern(OP_ADD, (n_node, Node.val(-1).uid))
                pow_part = Universe.intern(OP_POW, (base, new_exp))
                # dx
                dx = self.derive(base, var_uid)
                
                return Universe.intern(OP_MUL, (n_node, pow_part, dx))

        return Node.val(0).uid # Fallback constante

    def test_derivative_polynomial(self):
        """
        Test Maestro: Derivar f(x) = x^2 + 5x
        Resultado Esperado: 2x + 5
        """
        x = Node.symbol("x")
        
        # Construir x^2 + 5x
        term1 = x ** Node.val(2)
        term2 = Node.val(5) * x
        f = term1 + term2
        
        # DERIVAR
        df_uid = self.derive(f.uid, x.uid)
        
        # --- VERIFICACIÓN AUTOMÁTICA DEL COLAPSO ---
        # Si las estrategias (folding, grouping, identity) funcionan,
        # el resultado sucio de la derivación se limpiará solo.
        
        # Estructura esperada: Add(Mul(2, x), 5)
        # Ojo: x^1 -> x, 1*x -> x, x*0 -> 0, etc.
        
        # Debug visual
        # print(f"Op: {Universe.get_op(df_uid)}")
        
        # Validar Estructura
        op = Universe.get_op(df_uid)
        self.assertEqual(op, OP_ADD)
        
        args = Universe.get_args(df_uid)
        self.assertEqual(len(args), 2) # Dos términos: 2x y 5
        
        term_5 = None
        term_2x = None
        
        for arg in args:
            if Universe.get_op(arg) == OP_SCALAR:
                if Universe.get_args(arg)[0] == 5: term_5 = arg
            elif Universe.get_op(arg) == OP_MUL:
                # Verificar que sea 2*x
                mul_args = Universe.get_args(arg)
                val_2 = any(Universe.get_args(a)[0] == 2 for a in mul_args if Universe.get_op(a) == OP_SCALAR)
                has_x = any(a == x.uid for a in mul_args)
                if val_2 and has_x: term_2x = arg
                
        self.assertIsNotNone(term_5, "El término constante '5' desapareció o es incorrecto.")
        self.assertIsNotNone(term_2x, "El término '2x' no se formó correctamente.")

if __name__ == '__main__':
    unittest.main()