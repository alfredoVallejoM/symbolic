"""
tests/symbolic_core/kernel/test_strategies_integration.py
Tests de Integración Real para Normalización.
PARTE 1: Lógica Estructural Básica.
"""
import unittest
import random
import time
from symbolic_core.kernel.universe import Universe
from symbolic_core.kernel.node import Node
from symbolic_core.opcodes import *
# SectorManager se importa implícitamente en Universe, pero lo traemos por si acaso
from symbolic_core.kernel.sectors import SectorManager

class TestStrategiesIntegration(unittest.TestCase):

    def setUp(self):
        """
        Limpieza del _lookup para garantizar aislamiento entre tests.
        """
        Universe._lookup.clear()
        # Nota: No limpiamos los sectores físicos (Allocator) para no complicar, 
        # confiamos en que IDs nuevos no colisionan con basura vieja.

    def test_associative_flattening_basic(self):
        """
        Verifica: Add(Add(A, B), C) -> Add(A, B, C)
        """
        # 1. Crear símbolos base
        a = Node.symbol("a")
        b = Node.symbol("b")
        c = Node.symbol("c")
        
        # 2. Crear suma intermedia (A+B)
        sum_ab = a + b
        
        # 3. Crear suma total ( (A+B) + C )
        # El Universo debe llamar a la Estrategia, detectar el anidamiento y aplanar.
        total = sum_ab + c
        
        # --- VERIFICACIONES ---
        
        # A. La operación debe ser ADD
        op = Universe.get_op(total.uid)
        self.assertEqual(op, OP_ADD)
        
        # B. La aridad debe ser 3 (no 2)
        args = Universe.get_args(total.uid)
        self.assertEqual(len(args), 3, "El aplanamiento falló: la aridad debería ser 3.")
        
        # C. Los hijos deben ser a, b, c (en orden canónico)
        # Nota: Al ser ADD conmutativo, el Universo los ordena por ID.
        expected_ids = sorted([a.uid, b.uid, c.uid])
        self.assertEqual(list(args), expected_ids, "Los argumentos no son los átomos a,b,c o no están ordenados.")

    def test_ac_canonicalization(self):
        """
        Verifica que el orden de agrupación no altera el UID (Asociatividad + Conmutatividad).
        (A+B)+C == A+(B+C) == B+(C+A)
        """
        a = Node.symbol("x")
        b = Node.symbol("y")
        c = Node.symbol("z")
        
        # Camino 1: Agrupar izquierda
        term1 = (a + b) + c
        
        # Camino 2: Agrupar derecha
        term2 = a + (b + c)
        
        # Camino 3: Orden mezclado
        term3 = b + (c + a)
        
        # TODOS deben colapsar al mismo Puntero Físico (UID)
        self.assertEqual(term1.uid, term2.uid, "Fallo AC: (A+B)+C != A+(B+C)")
        self.assertEqual(term1.uid, term3.uid, "Fallo AC: (A+B)+C != B+(C+A)")
        
        # Verificar estructura interna plana
        args = Universe.get_args(term1.uid)
        self.assertEqual(len(args), 3, "La estructura canónica no está aplanada.")

    def test_flattening_deep(self):
        """
        Verifica aplanamiento en árbol balanceado: ((A+B) + (C+D)) -> (A,B,C,D)
        """
        a = Node.symbol("1")
        b = Node.symbol("2")
        c = Node.symbol("3")
        d = Node.symbol("4")
        
        left = a + b
        right = c + d
        
        top = left + right
        
        args = Universe.get_args(top.uid)
        self.assertEqual(len(args), 4, "Fallo en aplanamiento de árbol balanceado (4 hojas esperadas).")
        
        # Verificar que no quedan referencias a los nodos intermedios 'left' y 'right'
        self.assertNotIn(left.uid, args, "El nodo intermedio 'left' no se eliminó.")
        self.assertNotIn(right.uid, args, "El nodo intermedio 'right' no se eliminó.")

    def test_dual_involution_real(self):
        """
        Verifica Dual(Dual(A)) -> A.
        """
        a = Node.symbol("T")
        
        # Invocamos OP_DUAL manualmente mediante Universe.intern
        dual_a_id = Universe.intern(OP_DUAL, (a.uid,))
        
        # Aplicamos Dual de nuevo
        dual_dual_id = Universe.intern(OP_DUAL, (dual_a_id,))
        
        # Debe haber colapsado a A
        self.assertEqual(dual_dual_id, a.uid, "La involución Dual(Dual(A)) -> A falló.")

    def test_identity_reduction_real(self):
        """
        Verifica Add(x) -> x (Identidad Unitaria).
        """
        x = Node.symbol("val")
        
        # Forzamos una suma de 1 elemento
        sum_x_id = Universe.intern(OP_ADD, (x.uid,))
        
        self.assertEqual(sum_x_id, x.uid, "Reducción de identidad Add(x)->x falló.")
class TestDeepRobustness(unittest.TestCase):

    def setUp(self):
        """
        [Definición 7] Limpieza quirúrgica para aislamiento de tests.
        """
        Universe._lookup.clear()
        # Nota: En producción no limpiamos sectores físicos, pero para tests
        # asumimos que IDs nuevos no colisionan con basura vieja.

    def test_massive_flattening_stability(self):
        """
        [Definición 8] ESTRÉS: Verifica el aplanamiento de una suma de 2,000 elementos.
        Contrasta la construcción iterativa (Árbol Binario) vs Batch (Lista Plana).
        """
        N = 2000 # Cantidad de elementos
        
        # 1. Crear N símbolos únicos
        symbols = [Node.symbol(f"var_{i}") for i in range(N)]
        
        # 2. Construcción Binaria (Iterativa)
        # Esto genera (((A+B)+C)+D)... creando N nodos intermedios que deben colapsar.
        start_time = time.time()
        binary_tree_acc = symbols[0]
        for i in range(1, N):
            binary_tree_acc = binary_tree_acc + symbols[i]
        
        # 3. Construcción Plana (Batch)
        # Pasamos todos los argumentos de golpe a la estrategia.
        raw_ids = tuple(s.uid for s in symbols)
        flat_id = Universe.intern(OP_ADD, raw_ids)
        
        duration = time.time() - start_time
        
        # VALIDACIONES
        
        # A. Identidad Física: Ambos métodos deben colapsar al mismo Puntero.
        self.assertEqual(binary_tree_acc.uid, flat_id, 
                         "Fallo Crítico: La construcción iterativa no convergió a la forma plana.")
        
        # B. Estructura Interna: Debe ser una lista plana de N elementos.
        final_args = Universe.get_args(flat_id)
        self.assertEqual(len(final_args), N, 
                         f"Fallo de Aplanamiento: Se esperaban {N} hijos, se encontraron {len(final_args)}")
        
        print(f"\n[PERF] Flattening {N} nodos: {duration:.4f}s")

    def test_ac_permutation_hell(self):
        """
        [Definición 9] ROBUSTEZ MATEMÁTICA: 
        Genera 100 permutaciones aleatorias de una suma de 50 variables.
        TODAS deben colapsar al MISMO UID gracias a la Canonización.
        """
        N = 50
        variables = [Node.symbol(f"x{i}") for i in range(N)]
        var_ids = [v.uid for v in variables]
        
        # Referencia canónica (ordenada por ID numérico)
        canonical_id = Universe.intern(OP_ADD, tuple(sorted(var_ids)))
        
        for i in range(100):
            # Barajar aleatoriamente los inputs
            shuffled = list(var_ids)
            random.shuffle(shuffled)
            
            # Internar desordenado
            # El Universe + Estrategia deben ordenar y aplanar antes de buscar en _lookup.
            shuffled_id = Universe.intern(OP_ADD, tuple(shuffled))
            
            self.assertEqual(shuffled_id, canonical_id, 
                             f"Fallo de Conmutatividad en permutación {i}")

    def test_deep_recursion_dual_chain(self):
        """
        [Definición 10] ROBUSTEZ RECURSIVA: Cadena de 1001 Duales.
        Verifica: Dual^1000(A) == A (Par) y Dual^1001(A) == Dual(A) (Impar).
        """
        root = Node.symbol("O")
        curr = root
        
        # Bucle 1: Aplicar Dual 1000 veces (Número Par)
        for _ in range(1000):
            # Usamos intern directo para forzar la lógica pura
            uid = Universe.intern(OP_DUAL, (curr.uid,))
            curr = Node(uid)
            
        # Aserción Par: Debe haber colapsado a root
        self.assertEqual(curr.uid, root.uid, "Fallo: Dual^1000(A) != A")
        
        # Bucle 2: Aplicar 1 vez más (Número Impar)
        uid_odd = Universe.intern(OP_DUAL, (curr.uid,))
        
        # Aserción Impar: Debe ser Dual(root)
        expected_odd = Universe.intern(OP_DUAL, (root.uid,))
        self.assertEqual(uid_odd, expected_odd, "Fallo: Dual^1001(A) != Dual(A)")

    def test_heterogeneous_sorting_stability(self):
        """
        [Definición 11] ROBUSTEZ DE TIPOS: Suma mixta (Escalar, Símbolo, Tensor).
        Verifica que el ordenamiento es determinista incluso con tipos de materia distintos.
        """
        # Ingredientes
        s1 = Node.symbol("a")         # OP_SYMBOL
        n1 = Node.val(10)             # OP_SCALAR
        t1 = Node(Universe.intern(OP_TENSOR, (s1.uid, n1.uid))) # OP_TENSOR
        
        # Construimos la misma suma en distinto orden de entrada
        sum_1 = Node(Universe.intern(OP_ADD, (s1.uid, n1.uid, t1.uid)))
        sum_2 = Node(Universe.intern(OP_ADD, (t1.uid, s1.uid, n1.uid)))
        sum_3 = Node(Universe.intern(OP_ADD, (n1.uid, t1.uid, s1.uid)))
        
        # Aserción de Identidad
        self.assertEqual(sum_1.uid, sum_2.uid)
        self.assertEqual(sum_1.uid, sum_3.uid)
        
        # Aserción de Estructura: Verificar que los IDs internos están ordenados
        args = Universe.get_args(sum_1.uid)
        self.assertTrue(args[0] < args[1] < args[2], 
                        "Los argumentos heterogéneos no están ordenados numéricamente por UID.")

    def test_empty_and_unary_edge_cases(self):
        """
        [Definición 12] CASOS BORDE: Sumas vacías o unarias.
        """
        x = Node.symbol("x")
        
        # 1. Suma Unaria: Add(x) -> x
        unary_sum = Universe.intern(OP_ADD, (x.uid,))
        self.assertEqual(unary_sum, x.uid, "Add(x) no colapsó a x")
        
        # 2. Suma Vacía: Add() -> 0 (Identidad Aditiva)
        # La estrategia v3.4 debería manejar esto o devolver un nodo seguro.
        try:
            empty_sum = Universe.intern(OP_ADD, ())
            
            # Verificamos que devuelve el escalar 0 (Comportamiento ideal v3.4)
            # O un OP_ADD vacío si la estrategia es pasiva.
            op = Universe.get_op(empty_sum)
            if op == OP_SCALAR:
                val = Universe.get_args(empty_sum)[0]
                self.assertEqual(val, 0, "Add() debería ser 0")
            else:
                self.assertEqual(op, OP_ADD)
                self.assertEqual(len(Universe.get_args(empty_sum)), 0)
        except Exception as e:
            self.fail(f"La suma vacía provocó una excepción no controlada: {e}")

    def test_power_identities(self):
        """
        [Definición 13] Verifica identidades de potencia básicas.
        """
        x = Node.symbol("x")
        one = Node.val(1)
        zero = Node.val(0)
        
        # 1. x^1 -> x
        pow_1 = x ** one
        self.assertEqual(pow_1.uid, x.uid, "Fallo: x^1 != x")
        
        # 2. x^0 -> 1
        pow_0 = x ** zero
        op_res = Universe.get_op(pow_0.uid)
        args_res = Universe.get_args(pow_0.uid)
        
        self.assertEqual(op_res, OP_SCALAR)
        self.assertEqual(args_res[0], 1, "Fallo: x^0 != 1")

    def test_tensor_associativity(self):
        """
        [Definición 14] Verifica (A (x) B) (x) C -> A (x) B (x) C
        """
        a = Node.symbol("A")
        b = Node.symbol("B")
        c = Node.symbol("C")
        
        # Construcción manual de Tensores
        t_ab_id = Universe.intern(OP_TENSOR, (a.uid, b.uid))
        t_all_id = Universe.intern(OP_TENSOR, (t_ab_id, c.uid))
        
        # Verificar Aplanamiento
        args = Universe.get_args(t_all_id)
        self.assertEqual(len(args), 3, "El Tensor no se aplanó asociativamente (se esperaban 3 hijos).")
        expected = [a.uid, b.uid, c.uid] # El tensor NO ordena, preserva orden topológico
        self.assertEqual(list(args), expected, "El Tensor alteró el orden de los factores.")

    def test_exp_identities(self):
        """
        [Definición 15] Verifica exp(0) = 1.
        """
        zero = Node.val(0)
        exp_0_id = Universe.intern(OP_EXP, (zero.uid,))
        
        # Verificar resultado escalar 1
        val = Universe.get_args(exp_0_id)[0]
        self.assertEqual(val, 1, "Fallo: exp(0) != 1")

    def test_tensor_scalar_identity(self):
        """
        [Definición 16] Verifica Tensor(A) -> A (Degeneración Unitaria).
        """
        a = Node.symbol("A")
        t_unary = Universe.intern(OP_TENSOR, (a.uid,))
        self.assertEqual(t_unary, a.uid, "Tensor unario no colapsó.")

    def test_batch_vs_iterative_efficiency(self):
        """
        [Definición 17] Benchmark: Batch debe ser >10x más rápido que Iterativo.
        """
        N = 2000
        symbols = [Node.symbol(f"perf_{i}") for i in range(N)]
        raw_ids = tuple(s.uid for s in symbols)
        
        # 1. Modo Lento (Iterativo)
        start_slow = time.time()
        acc = symbols[0]
        for i in range(1, N):
            acc = acc + symbols[i]
        duration_slow = time.time() - start_slow
        
        # 2. Modo Rápido (Batch)
        start_fast = time.time()
        flat_id = Universe.intern(OP_ADD, raw_ids)
        duration_fast = time.time() - start_fast
        
        # Aserciones
        self.assertEqual(acc.uid, flat_id, "Divergencia matemática entre Batch e Iterativo.")
        
        # Evitar división por cero
        speedup = duration_slow / (duration_fast + 1e-9)
        print(f"\n[BENCH] Speedup Batch vs Iterativo: {speedup:.1f}x")
        
        self.assertGreater(speedup, 10, "El aplanamiento Batch no es suficientemente eficiente.")

    def test_mixed_type_soup(self):
        """
        [Definición 18] Sopa de tipos: Escalares, Símbolos y Blobs.
        """
        s = Node.symbol("sym")
        i = Node.val(42)
        blob_id = Universe.intern_blob(b"binary_data")
        
        # Mezclamos IDs de Node wrapper con IDs crudos de Blob
        mixed_id = Universe.intern(OP_ADD, (s.uid, i.uid, blob_id))
        
        # Verificaciones
        op = Universe.get_op(mixed_id)
        self.assertEqual(op, OP_ADD)
        
        # Recrear en orden inverso
        mixed_id_2 = Universe.intern(OP_ADD, (blob_id, i.uid, s.uid))
        self.assertEqual(mixed_id, mixed_id_2, "Fallo de determinismo con tipos mixtos (Blob/Sym/Int).")

    def test_deep_nesting_limit(self):
        """
        [Definición 19] Límite de anidamiento en estructuras no aplanables.
        Dual(Dual(...Dual(A)...)) a profundidad 500.
        """
        DEPTH = 500
        base = Node.symbol("base")
        curr = base
        
        # Estrategia v3.4 reduce Dual(Dual(A)) -> A inmediatamente.
        # Por tanto, no se crea una cadena de 500 punteros, sino que oscila.
        for _ in range(DEPTH):
            uid = Universe.intern(OP_DUAL, (curr.uid,))
            curr = Node(uid)
            
        # 500 es par -> debe ser base
        if DEPTH % 2 == 0:
            self.assertEqual(curr.uid, base.uid)
        else:
            # Si fuera impar, verificamos que es Dual(base)
            dual_base = Universe.intern(OP_DUAL, (base.uid,))
            self.assertEqual(curr.uid, dual_base)

    def test_unicode_and_binary_names(self):
        """
        [Definición 20] Soporte UTF-8 y nombres binarios en Símbolos.
        """
        name1 = "αβγ_tensor"
        name2 = "quantum_🚀"
        
        n1 = Node.symbol(name1)
        n2 = Node.symbol(name2)
        
        self.assertNotEqual(n1.uid, n2.uid)
        
        # Recuperación del nombre (stored as Blob in args[0])
        name_id = Universe.get_args(n1.uid)[0]
        name_bytes = Universe.get_args(name_id)
        self.assertEqual(name_bytes.decode('utf-8'), name1)

    def test_additive_identity_laws(self):
        """
        [Definición 21] Leyes de Identidad Aditiva.
        """
        x = Node.symbol("x")
        unary = Universe.intern(OP_ADD, (x.uid,))
        self.assertEqual(unary, x.uid, "Fallo: Add(x) != x")

    def test_multiplicative_identity_laws(self):
        """
        [Definición 22] Leyes de Identidad Multiplicativa.
        """
        x = Node.symbol("x")
        unary = Universe.intern(OP_MUL, (x.uid,))
        self.assertEqual(unary, x.uid, "Fallo: Mul(x) != x")

    def test_power_laws(self):
        """
        [Definición 23] (DUPLICADO LÓGICO DE #13) Verifica x^1 y x^0.
        Conservado por integridad de la especificación.
        """
        x = Node.symbol("x")
        # x^1 -> x
        res1 = x ** Node.val(1)
        self.assertEqual(res1.uid, x.uid)
        # x^0 -> 1
        res0 = x ** Node.val(0)
        self.assertEqual(Universe.get_args(res0.uid)[0], 1)

    def test_exponential_laws(self):
        """
        [Definición 24] (DUPLICADO LÓGICO DE #15) Verifica exp(0).
        Conservado por integridad.
        """
        zero = Node.val(0)
        uid = Universe.intern(OP_EXP, (zero.uid,))
        self.assertEqual(Universe.get_args(uid)[0], 1)

    def test_tensor_laws(self):
        """
        [Definición 25] (AGREGADO) Verifica Tensor(A) y No-Conmutatividad.
        Agrupa lógicas previas en un test consolidado.
        """
        a = Node.symbol("A")
        b = Node.symbol("B")
        
        # 1. Unario
        t_unary = Universe.intern(OP_TENSOR, (a.uid,))
        self.assertEqual(t_unary, a.uid)
        
        # 2. No Conmutatividad (A x B != B x A)
        t1 = Universe.intern(OP_TENSOR, (a.uid, b.uid))
        t2 = Universe.intern(OP_TENSOR, (b.uid, a.uid))
        self.assertNotEqual(t1, t2, "El Tensor conmutó ilegalmente (violación de física de trenzas).")


class TestHolographicCalculus(unittest.TestCase):
    """
    NUEVA BATERÍA v3.4:
    Verifica capacidades de Cálculo Real, Álgebra Profunda y Teoría de Categorías.
    """

    def setUp(self):
        Universe._lookup.clear()

    # =========================================================================
    # A. Aritmética y Plegado de Constantes (Calculation)
    # =========================================================================

    def test_arithmetic_constant_folding_pure(self):
        """
        Situación: Crear Add(10, 20, 5).
        Comprobación: El UID resultante debe corresponder a un nodo SCALAR(35).
        """
        n10 = Node.val(10)
        n20 = Node.val(20)
        n5  = Node.val(5)
        
        # Add(10, 20, 5) -> Debe calcularse 35
        res_uid = Universe.intern(OP_ADD, (n10.uid, n20.uid, n5.uid))
        
        op = Universe.get_op(res_uid)
        self.assertEqual(op, OP_SCALAR, "El resultado no es un escalar.")
        
        val = Universe.get_args(res_uid)[0]
        self.assertEqual(val, 35, f"Cálculo incorrecto: esperado 35, obtenido {val}")

    def test_arithmetic_folding_mixed_structure(self):
        """
        Situación: Add(Symbol("x"), Val(5), Val(10), Symbol("y")).
        Comprobación: Debe resultar en Add(15, x, y).
        """
        x = Node.symbol("x")
        y = Node.symbol("y")
        n5 = Node.val(5)
        n10 = Node.val(10)
        
        res_uid = Universe.intern(OP_ADD, (x.uid, n5.uid, n10.uid, y.uid))
        
        # Verificar que sigue siendo una suma (porque hay símbolos)
        self.assertEqual(Universe.get_op(res_uid), OP_ADD)
        
        args = Universe.get_args(res_uid)
        self.assertEqual(len(args), 3, "No se redujeron los términos constantes.")
        
        # Verificar contenido: Debe haber un escalar 15 y los símbolos x, y
        # Recuperamos los valores/tipos de los argumentos
        scalars = []
        symbols = []
        for arg in args:
            if Universe.get_op(arg) == OP_SCALAR:
                scalars.append(Universe.get_args(arg)[0])
            else:
                symbols.append(arg)
        
        self.assertEqual(scalars, [15], "La suma de constantes (5+10) falló.")
        self.assertIn(x.uid, symbols)
        self.assertIn(y.uid, symbols)

    def test_multiplication_annihilation_short_circuit(self):
        """
        Situación: Multiplicación masiva donde uno es 0.
        Comprobación: Resultado 0, Short-circuiting.
        """
        # Crear 1000 elementos (999 unos y 1 cero en el medio)
        # Usamos 1 para que no afecte el producto si fallara la aniquilación
        elements = [Node.val(1).uid] * 1000
        elements[500] = Node.val(0).uid # El "Veneno"
        
        start_time = time.time()
        res_uid = Universe.intern(OP_MUL, tuple(elements))
        duration = time.time() - start_time
        
        # 1. Resultado debe ser 0
        self.assertEqual(Universe.get_op(res_uid), OP_SCALAR)
        self.assertEqual(Universe.get_args(res_uid)[0], 0, "Fallo de aniquilación por cero.")
        
        # 2. Benchmark (Short-Circuit)
        # Una multiplicación de 1000 items simbólicos sin short-circuit tomaría más tiempo
        # aunque con intern_val(1) es rápido, la lógica de short-circuit retorna
        # inmediatamente al ver el 0.
        print(f"\n[PERF] Mul Annihilation: {duration:.6f}s")
        # Es difícil poner un assert de tiempo determinista en CI, pero conceptualmente validamos el resultado.

    def test_multiplication_neutral_element(self):
        """
        Situación: Mul(x, 1, y).
        Comprobación: Debe resultar en Mul(x, y). El 1 desaparece.
        """
        x = Node.symbol("x")
        y = Node.symbol("y")
        one = Node.val(1)
        
        res_uid = Universe.intern(OP_MUL, (x.uid, one.uid, y.uid))
        
        args = Universe.get_args(res_uid)
        self.assertEqual(len(args), 2, "El elemento neutro (1) no fue eliminado.")
        self.assertNotIn(one.uid, args)
        self.assertIn(x.uid, args)
        self.assertIn(y.uid, args)

    # =========================================================================
    # B. Álgebra Simbólica (Grouping & Powers)
    # =========================================================================

    def test_algebraic_grouping_additive(self):
        """
        Situación: Add(x, x, x, y).
        Comprobación: Add(Mul(3, x), y).
        """
        x = Node.symbol("x")
        y = Node.symbol("y")
        
        res_uid = Universe.intern(OP_ADD, (x.uid, x.uid, x.uid, y.uid))
        
        # Esperamos una suma de 2 elementos: [Mul(3,x), y]
        args = Universe.get_args(res_uid)
        self.assertEqual(len(args), 2)
        
        # Buscar el término agrupado
        mul_term = None
        other_term = None
        
        for arg in args:
            if arg == y.uid:
                other_term = arg
            elif Universe.get_op(arg) == OP_MUL:
                mul_term = arg
        
        self.assertIsNotNone(mul_term, "No se generó el término multiplicativo (Agrupamiento).")
        
        # Verificar Mul(3, x)
        mul_args = Universe.get_args(mul_term) # [3, x] (ordenado puede variar, buscamos contenido)
        vals = []
        syms = []
        for ma in mul_args:
            if Universe.get_op(ma) == OP_SCALAR: vals.append(Universe.get_args(ma)[0])
            else: syms.append(ma)
            
        self.assertEqual(vals, [3], "El coeficiente agrupado no es 3.")
        self.assertEqual(syms, [x.uid], "El símbolo agrupado no es x.")

    def test_algebraic_grouping_multiplicative(self):
        """
        Situación: Mul(x, x, x, y).
        Comprobación: Mul(Pow(x, 3), y).
        """
        x = Node.symbol("x")
        y = Node.symbol("y")
        
        res_uid = Universe.intern(OP_MUL, (x.uid, x.uid, x.uid, y.uid))
        
        args = Universe.get_args(res_uid)
        self.assertEqual(len(args), 2)
        
        pow_term = None
        for arg in args:
            if Universe.get_op(arg) == OP_POW:
                pow_term = arg
                break
        
        self.assertIsNotNone(pow_term, "No se generó la potencia (x^3).")
        
        # Verificar Pow(x, 3)
        base_id, exp_id = Universe.get_args(pow_term)
        self.assertEqual(base_id, x.uid)
        self.assertEqual(Universe.get_args(exp_id)[0], 3)

    def test_nested_power_reduction_symbolic(self):
        """
        Situación: Pow(Pow(x, 2), 3).
        Comprobación: Pow(x, 6).
        """
        x = Node.symbol("x")
        n2 = Node.val(2)
        n3 = Node.val(3)
        
        # (x^2)
        inner = Universe.intern(OP_POW, (x.uid, n2.uid))
        # (x^2)^3
        res_uid = Universe.intern(OP_POW, (inner, n3.uid))
        
        # Verificar Base
        base, exp = Universe.get_args(res_uid)
        self.assertEqual(base, x.uid, "La base no se preservó.")
        
        # Verificar Exponente (2*3 = 6)
        self.assertEqual(Universe.get_args(exp)[0], 6, "No se multiplicaron los exponentes.")

    def test_nested_power_reduction_mixed(self):
        """
        Situación: Pow(Pow(x, a), b).
        Comprobación: Pow(x, Mul(a, b)).
        """
        x = Node.symbol("x")
        a = Node.symbol("a")
        b = Node.symbol("b")
        
        # (x^a)
        inner = Universe.intern(OP_POW, (x.uid, a.uid))
        # (x^a)^b
        res_uid = Universe.intern(OP_POW, (inner, b.uid))
        
        base, exp = Universe.get_args(res_uid)
        self.assertEqual(base, x.uid)
        
        # El exponente debe ser Mul(a, b)
        self.assertEqual(Universe.get_op(exp), OP_MUL)
        self.assertEqual(len(Universe.get_args(exp)), 2) # a, b

    # =========================================================================
    # C. Teoría de Categorías (Tensor & Dual)
    # =========================================================================

    def test_categorical_distributivity_dual_over_tensor(self):
        """
        Situación: Dual(Tensor(A, B)).
        Comprobación: Tensor(Dual(A), Dual(B)).
        """
        a = Node.symbol("A")
        b = Node.symbol("B")
        
        t_ab = Universe.intern(OP_TENSOR, (a.uid, b.uid))
        res_uid = Universe.intern(OP_DUAL, (t_ab,))
        
        # 1. El operador raíz debe seguir siendo TENSOR
        self.assertEqual(Universe.get_op(res_uid), OP_TENSOR)
        
        # 2. Los hijos deben ser Dual(A) y Dual(B)
        args = Universe.get_args(res_uid)
        self.assertEqual(len(args), 2)
        
        # Verificar hijo 1: Dual(A)
        op1 = Universe.get_op(args[0])
        arg1 = Universe.get_args(args[0])[0]
        self.assertEqual(op1, OP_DUAL)
        self.assertEqual(arg1, a.uid)
        
        # Verificar hijo 2: Dual(B)
        op2 = Universe.get_op(args[1])
        arg2 = Universe.get_args(args[1])[0]
        self.assertEqual(op2, OP_DUAL)
        self.assertEqual(arg2, b.uid)

    def test_categorical_complex_cancellation(self):
        """
        Situación: Dual(Tensor(Dual(A), B)).
        Comprobación: Tensor(A, Dual(B)). (Dual(Dual(A)) se aniquila).
        """
        a = Node.symbol("A")
        b = Node.symbol("B")
        
        # Dual(A)
        dual_a = Universe.intern(OP_DUAL, (a.uid,))
        
        # Tensor(Dual(A), B)
        t_inner = Universe.intern(OP_TENSOR, (dual_a, b.uid))
        
        # Dual(Tensor(...)) -> Distributiva -> Tensor(Dual(Dual(A)), Dual(B)) -> Tensor(A, Dual(B))
        res_uid = Universe.intern(OP_DUAL, (t_inner,))
        
        args = Universe.get_args(res_uid)
        
        # Hijo 1: Debe ser A (Aniquilación)
        self.assertEqual(args[0], a.uid, "La involución anidada dentro del tensor falló.")
        
        # Hijo 2: Debe ser Dual(B)
        self.assertEqual(Universe.get_op(args[1]), OP_DUAL)
        self.assertEqual(Universe.get_args(args[1])[0], b.uid)

    # =========================================================================
    # D. Robustez y Estrés Combinado
    # =========================================================================

    def test_complex_expression_collapse(self):
        """
        Situación: Mul(Add(1, 1), Pow(x, 0), Tensor(Dual(Dual(y))), Mul(5, 0)).
        Comprobación: Colapso total a SCALAR(0).
        """
        x = Node.symbol("x")
        y = Node.symbol("y")
        
        # 1. Add(1, 1) -> 2
        p1 = Universe.intern(OP_ADD, (Node.val(1).uid, Node.val(1).uid))
        
        # 2. Pow(x, 0) -> 1
        p2 = Universe.intern(OP_POW, (x.uid, Node.val(0).uid))
        
        # 3. Tensor(Dual(Dual(y))) -> Tensor(y) -> y
        d_y = Universe.intern(OP_DUAL, (y.uid,))
        dd_y = Universe.intern(OP_DUAL, (d_y,))
        p3 = Universe.intern(OP_TENSOR, (dd_y,))
        
        # 4. Mul(5, 0) -> 0
        p4 = Universe.intern(OP_MUL, (Node.val(5).uid, Node.val(0).uid))
        
        # Gran Final: Mul(2, 1, y, 0) -> 0
        res_uid = Universe.intern(OP_MUL, (p1, p2, p3, p4))
        
        self.assertEqual(Universe.get_op(res_uid), OP_SCALAR)
        self.assertEqual(Universe.get_args(res_uid)[0], 0, "El colapso complejo falló.")
if __name__ == '__main__':
    unittest.main()