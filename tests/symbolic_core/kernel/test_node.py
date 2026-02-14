"""
tests/symbolic_core/kernel/test_node.py
Tests de la Fachada Node.
Verifica: Sobrecarga de operadores, Auto-boxing, Igualdad y Hashabilidad.
"""
import unittest
from symbolic_core.kernel.node import Node
from symbolic_core.kernel.universe import Universe
from symbolic_core.opcodes import *


"""
tests/symbolic_core/kernel/test_node.py
Tests de la Fachada Node v4.0 (Holographic Facade).
Verifica:
1. Interfaz de Usuario (Operadores, Auto-boxing).
2. Introspección Holográfica (.qec, .entropy).
3. Hashing de Avalancha (Proyección no lineal).
4. Métricas de Similitud Espectral (LSH).
"""
import unittest
from symbolic_core.kernel.node import Node
from symbolic_core.kernel.universe import Universe
from symbolic_core.opcodes import *
from symbolic_core.hashing.invariants import SHIFT_QEC

class TestNodeFacade(unittest.TestCase):

    def setUp(self):
        Universe._lookup.clear()
        Universe._blob_lookup.clear()
        # [OPCIONAL] Si SectorManager mantiene estado global, reinícialo.
        # SectorManager.reset() # (Si implementaste un método reset)

    # =========================================================================
    # 1. INTERFAZ BÁSICA Y FACTORY
    # =========================================================================

    def test_factory_methods(self):
        """
        Verifica que los métodos estáticos creen los tipos correctos.
        [Robustez] Asegura que el Blob del nombre se mantenga vivo.
        """
        # Símbolo
        sym = Node.symbol("alpha")
        self.assertIsInstance(sym, Node)
        self.assertEqual(Universe.get_op(sym.uid), OP_SYMBOL)
        
        # Recuperación de argumentos (Hijos)
        args = Universe.get_args(sym.uid)
        self.assertEqual(len(args), 1, "El símbolo debe tener 1 hijo (el Blob del nombre).")
        
        name_blob_id = args[0]
        # Recuperamos el contenido del Blob
        # Si esto falla con ValueError, es que el GC recolectó el Blob prematuramente.
        name_bytes = Universe.get_args(name_blob_id)
        self.assertEqual(name_bytes, b"alpha")

        # Valor (Escalar)
        val = Node.val(42)
        self.assertIsInstance(val, Node)
        self.assertEqual(Universe.get_op(val.uid), OP_SCALAR)
        self.assertEqual(Universe.get_args(val.uid)[0], 42)

    def test_auto_boxing(self):
        """Verifica conversión automática de Python int -> Node."""
        x = Node.symbol("x")
        # Suma: Node + int
        expr = x + 10
        self.assertEqual(Universe.get_op(expr.uid), OP_ADD)
        
        # Reverse operator: int + Node
        expr2 = 20 * x
        self.assertEqual(Universe.get_op(expr2.uid), OP_MUL)

    def test_operator_overloading(self):
        """Verifica sintaxis algebraica completa."""
        a, b = Node.symbol("a"), Node.symbol("b")
        
        # Aritmética estándar
        self.assertEqual(Universe.get_op((a + b).uid), OP_ADD)
        self.assertEqual(Universe.get_op((a * b).uid), OP_MUL)
        self.assertEqual(Universe.get_op((a ** b).uid), OP_POW)
        
        # Aritmética cuántica/tensorial (NUEVO v4.0)
        self.assertEqual(Universe.get_op((a @ b).uid), OP_TENSOR)
        self.assertEqual(Universe.get_op((~a).uid), OP_DUAL)

    # =========================================================================
    # 2. INTROSPECCIÓN HOLOGRÁFICA (AdS/CFT)
    # =========================================================================

    def test_holographic_properties(self):
        """
        Verifica que el Nodo expone sus componentes duales.
        """
        x = Node.symbol("omega")
        
        # 1. Entropía (AdS - Contenido)
        # Debe ser un entero grande (256 bits) no nulo
        self.assertGreater(x.entropy, 0)
        self.assertGreater(x.entropy.bit_length(), 64) 
        
        # 2. QEC (CFT - Estructura)
        # Debe ser un entero de 64 bits (Vector Espectral)
        self.assertGreater(x.qec, 0)
        self.assertLess(x.qec.bit_length(), 65)

    def test_duality_coupling(self):
        """
        Verifica que la Identidad (UID) es la fusión de Entropía y QEC.
        No puede haber UID sin ambos.
        """
        x = Node.symbol("x")
        
        # Reconstrucción parcial para verificar bits
        reconstructed_qec = (x.uid >> SHIFT_QEC) & 0xFFFFFFFFFFFFFFFF
        self.assertEqual(x.qec, reconstructed_qec)

    # =========================================================================
    # 3. HASHING AVANZADO (AVALANCHE MIXER)
    # =========================================================================

    def test_hash_avalanche(self):
        """
        Verifica que el __hash__ de Python tiene efecto avalancha.
        Cambio mínimo en valor -> Cambio masivo en hash.
        """
        n1 = Node.val(123456789)
        n2 = Node.val(123456790) # 1 bit diff
        
        h1 = hash(n1)
        h2 = hash(n2)
        
        # XOR de hashes y conteo de bits cambiados
        diff_bits = (h1 ^ h2).bit_count()
        
        # En 64 bits, esperamos ~32. Si es <10, el hash es lineal/malo.
        self.assertGreater(diff_bits, 15, "Efecto avalancha insuficiente en __hash__.")

    def test_hash_distribution(self):
        """
        Verifica ausencia de colisiones en espacio denso.
        """
        N = 5000
        nodes = {Node.val(i) for i in range(N)}
        self.assertEqual(len(nodes), N, "El __hash__ provocó colisiones de identidad en el Set.")

    # =========================================================================
    # 4. SIMILITUD ESPECTRAL (LSH)
    # =========================================================================

    def test_similarity_metric(self):
        """
        Verifica la métrica de distancia topológica.
        """
        # Caso 1: Identidad
        a = Node.symbol("Alpha_Symbol_A") # Nombres más largos para mejor dispersión QEC
        self.assertEqual(a.similarity(a), 1.0)
        
        # Caso 2: Ortogonalidad (Aprox)
        # En HDC, vectores aleatorios distintos son ortogonales (~0.5 similitud).
        # "Alpha" y "Beta" son strings cortos, pero con el encoder v4.3 deberían dispersar bien.
        b = Node.symbol("Beta_Symbol_B")
        
        sim = a.similarity(b)
        
        # Imprimimos para debug si falla
        if not (0.2 < sim < 0.8):
            print(f"\n[DEBUG] Similitud fallida: {sim}")
            print(f"QEC A: {bin(a.qec)}")
            print(f"QEC B: {bin(b.qec)}")

        # En HDC, ortogonalidad es estadística. 
        # Aceptamos un rango amplio para evitar falsos negativos en tests unitarios.
        # Si da > 0.9, es que son CASI IGUALES, lo cual es un bug del encoder.
        self.assertTrue(0.2 <= sim <= 0.85, 
            f"Similitud {sim} fuera de rango ortogonal. Los símbolos distintos parecen iguales.")
        
    def test_structural_isomorphism(self):
        """
        Verifica que grafos recreados son isomorfos (Similitud 1.0).
        """
        g1 = Node.symbol("x") + Node.symbol("y")
        
        # Limpiar memoria para forzar recreación física
        Universe._lookup.clear()
        
        g2 = Node.symbol("x") + Node.symbol("y")
        
        self.assertEqual(g1.similarity(g2), 1.0)
        # También deben ser iguales por identidad (Hash Consing determinista)
        self.assertEqual(g1, g2)

    def test_map_persistence_facade(self):
        """Verifica Node.dict() y acceso."""
        data = {Node.symbol("k"): 100}
        m = Node.dict(data)
        
        self.assertEqual(m[Node.symbol("k")], Node.val(100))
        
        with self.assertRaises(KeyError):
            _ = m[Node.symbol("missing")]


class TestNodeFacade_2(unittest.TestCase):

    def setUp(self):
        # No necesitamos limpiar el Universo estrictamente para estos tests,
        # ya que probamos la interfaz, no la memoria.
        pass

    def test_factory_methods(self):
        """
        Verifica que los métodos estáticos creen los tipos correctos.
        """
        # 1. Símbolo
        sym = Node.symbol("alpha")
        self.assertIsInstance(sym, Node)
        self.assertEqual(Universe.get_op(sym.uid), OP_SYMBOL)
        
        # Verificar que el nombre se guardó bien
        name_blob_id = Universe.get_args(sym.uid)[0]
        name_bytes = Universe.get_args(name_blob_id)
        self.assertEqual(name_bytes, b"alpha")

        # 2. Valor (Escalar)
        val = Node.val(42)
        self.assertIsInstance(val, Node)
        self.assertEqual(Universe.get_op(val.uid), OP_SCALAR)
        self.assertEqual(Universe.get_args(val.uid)[0], 42)

    def test_operator_overloading_basic(self):
        """
        Verifica x + y, x * y, x ** y.
        """
        a = Node.symbol("a")
        b = Node.symbol("b")

        # SUMA
        res_sum = a + b
        self.assertEqual(Universe.get_op(res_sum.uid), OP_ADD)
        
        # PRODUCTO
        res_mul = a * b
        self.assertEqual(Universe.get_op(res_mul.uid), OP_MUL)
        
        # POTENCIA
        res_pow = a ** b
        self.assertEqual(Universe.get_op(res_pow.uid), OP_POW)

    def test_auto_boxing_integers(self):
        """
        Verifica que operar un Node con un 'int' de Python
        automáticamente convierte el int en Node.val().
        """
        x = Node.symbol("x")
        
        # Suma: Node + int
        expr = x + 10
        
        # Verificar estructura interna
        op = Universe.get_op(expr.uid)
        args = Universe.get_args(expr.uid)
        
        self.assertEqual(op, OP_ADD)
        # Debe haber 2 argumentos: el ID de 'x' y el ID de '10'
        # (Dependiendo de la estrategia de sorting, el orden puede variar)
        
        # Buscamos el escalar 10 en los argumentos
        found_scalar = False
        for arg_id in args:
            if Universe.get_op(arg_id) == OP_SCALAR:
                val = Universe.get_args(arg_id)[0]
                if val == 10:
                    found_scalar = True
        
        self.assertTrue(found_scalar, "El entero 10 no se convirtió correctamente a Node.")

    def test_expression_chaining(self):
        """
        Verifica expresiones complejas: (x + 1) * (y ** 2)
        """
        x = Node.symbol("x")
        y = Node.symbol("y")
        
        expr = (x + 1) * (y ** 2)
        
        # La raíz debe ser MUL
        self.assertEqual(Universe.get_op(expr.uid), OP_MUL)
        
        # Verificar argumentos (Hijos del Mul)
        args = Universe.get_args(expr.uid)
        # Esperamos 2 hijos: (x+1) y (y^2)
        self.assertEqual(len(args), 2)
        
        # Validar tipos de los hijos
        op_h1 = Universe.get_op(args[0])
        op_h2 = Universe.get_op(args[1])
        
        # Como hay sorting, no sabemos el orden exacto, pero uno debe ser ADD y otro POW
        ops = sorted([op_h1, op_h2])
        self.assertEqual(ops, sorted([OP_ADD, OP_POW]))

    def test_equality_semantics(self):
        """
        CRÍTICO: Node(uid) == Node(uid) debe ser True.
        """
        n1 = Node.symbol("omega")
        # Creamos otro wrapper manualmente apuntando al mismo ID
        n2 = Node(n1.uid)
        
        # Igualdad de Python
        self.assertTrue(n1 == n2)
        self.assertFalse(n1 != n2)
        
        # Igualdad contra otros tipos
        self.assertFalse(n1 == "omega")
        self.assertFalse(n1 == 123)

    def test_hashability(self):
        """
        Verifica que los Nodes se pueden usar como claves en diccionarios
        o elementos en sets de Python.
        """
        n1 = Node.symbol("k")
        n2 = Node(n1.uid) # Misma referencia física
        n3 = Node.symbol("other")
        
        # 1. Uso en SET
        s = {n1, n2, n3}
        # n1 y n2 deberían colapsar en una sola entrada
        self.assertEqual(len(s), 2)
        self.assertIn(n1, s)
        self.assertIn(n3, s)
        
        # 2. Uso en DICT
        d = {n1: "valor_asociado"}
        self.assertEqual(d[n2], "valor_asociado")

    def test_repr_debug_experience(self):
        """
        Verifica que __repr__ no explote y dé información útil.
        """
        x = Node.symbol("my_var")
        msg = repr(x)
        self.assertIn("my_var", msg)
        
        val = Node.val(999)
        msg_val = repr(val)
        self.assertIn("999", msg_val)
        
        # Test de nodo complejo (sin crash)
        expr = x + val
        repr(expr) # Solo verificamos que no lance excepción

    def test_type_safety(self):
        """
        Verifica que sumar Node con tipos incompatibles lance error.
        """
        x = Node.symbol("x")
        
        with self.assertRaises(TypeError):
            _ = x + "cadena_invalida"
            
        with self.assertRaises(TypeError):
            _ = x * None

    def test_reverse_operators(self):
        """Verifica 1 + x (donde el int está a la izquierda)."""
        x = Node.symbol("x")
        expr = 1 + x  # Requiere __radd__
        self.assertEqual(Universe.get_op(expr.uid), OP_ADD)
if __name__ == '__main__':
    unittest.main()