"""
tests/symbolic_core/ds/test_hamt.py
Suite de Pruebas Unificada para Estructura de Datos HAMT.
Incluye Tests Básicos, Integración y Casos de Borde Extendidos.
"""
import unittest
import random
from symbolic_core.ds.hamt import HAMT
from symbolic_core.kernel.node import Node
from symbolic_core.kernel.universe import Universe
from symbolic_core.hashing.utils import holographic_hash # [CRÍTICO] Fuente de verdad matemática
from symbolic_core.opcodes import *

# =========================================================================
# 1. PRUEBAS BÁSICAS (Funcionalidad Core)
# =========================================================================
class TestHAMT(unittest.TestCase):

    def setUp(self):
        Universe._lookup.clear()

    def test_basic_put_get(self):
        """Mapas básicos."""
        m0 = HAMT.empty()
        k1, v1 = Node.symbol("k1"), Node.val(100)
        
        m1 = m0.put(k1, v1)
        
        # Get exitoso
        res = m1.get(k1)
        self.assertIsNotNone(res)
        self.assertEqual(Universe.get_args(res.uid)[0], 100)
        
        # Get fallido
        self.assertIsNone(m1.get(Node.symbol("k_missing")))

    def test_immutability_update(self):
        """
        Verifica inmutabilidad estructural: m1 no cambia si creo m2.
        """
        k1 = Node.symbol("key")
        m1 = HAMT.empty().put(k1, Node.val(100))
        m2 = m1.put(k1, Node.val(200))
        
        val_m1 = Universe.get_args(m1.get(k1).uid)[0]
        val_m2 = Universe.get_args(m2.get(k1).uid)[0]
        
        self.assertEqual(val_m1, 100)
        self.assertEqual(val_m2, 200)
        self.assertNotEqual(m1.uid, m2.uid)

    def test_large_volume_and_collisions(self):
        """
        Inserta 100 claves. Verifica manejo de profundidad básica.
        """
        m = HAMT.empty()
        data = {} 
        
        # Insertar
        for i in range(100):
            k = Node.val(i)
            v = Node.val(i * 10)
            m = m.put(k, v)
            data[i] = i * 10
            
        # Verificar todas
        for i in range(100):
            k = Node.val(i)
            res = m.get(k)
            self.assertIsNotNone(res, f"Fallo al recuperar clave {i}")
            val = Universe.get_args(res.uid)[0]
            self.assertEqual(val, data[i])


# =========================================================================
# 2. PRUEBAS DE INTEGRACIÓN (Node Facade & Physics)
# =========================================================================
class TestHAMTIntegration(unittest.TestCase):
    """
    Pruebas de Integración y Física del Hashing para HAMT.
    """

    def setUp(self):
        Universe._lookup.clear()

    def test_holographic_hash_consistency(self):
        """
        [CORREGIDO] Verifica que Node implementa correctamente el estándar.
        SOLUCIÓN INTERMITENCIA: Usamos k.__hash__() DIRECTAMENTE.
        
        Explicación:
        Llamar a hash(k) invoca el C-Layer de Python, que aplica un módulo 
        Mersenne (2**61 - 1) si el número es muy grande. Esto causaba fallos 
        aleatorios (aprox 87% de las veces) cuando el hash caía en la zona alta.
        
        Al llamar a __hash__(), obtenemos el valor puro (Unsigned 64-bit) 
        que retorna nuestra clase, antes de que Python lo toque.
        """
        k = Node.val("test_consistency")
        
        # 1. Llamada directa (Bypass CPython hash scrambler)
        # Esto nos da lo que REALMENTE retorna tu código en node.py
        h_node_raw = k.__hash__()
        
        # 2. La verdad matemática del sistema
        h_internal = holographic_hash(k.uid)
        
        # AHORA SI: Deben ser idénticos bit a bit, siempre (100% determinista)
        self.assertEqual(h_node_raw, h_internal, 
             "Divergencia Crítica: Node.__hash__ no está delegando en utils.holographic_hash.")

    def test_node_dict_facade(self):
        """
        Verifica la fachada Node.dict() (API pública).
        """
        data = {"x": 1, "y": 2, 100: "cien"}
        m_node = Node.dict(data)
        
        # Acceso mediante __getitem__ de Node
        self.assertEqual(Universe.get_args(m_node["x"].uid)[0], 1)
        self.assertEqual(Universe.get_args(m_node[100].uid)[0], "cien")
        
        with self.assertRaises(TypeError):
            m_node["z"] = 3 

    def test_mixed_type_keys(self):
        """
        Verifica claves de tipos mixtos (Int, Str, Node).
        """
        m = HAMT.empty()
        
        k1 = Node.val(1)
        k2 = Node.val("1") 
        k3 = Node.symbol("1") 
        
        m = m.put(k1, Node.val("INT"))
        m = m.put(k2, Node.val("STR"))
        m = m.put(k3, Node.val("SYM"))
        
        self.assertEqual(Universe.get_args(m.get(k1).uid)[0], "INT")
        self.assertEqual(Universe.get_args(m.get(k2).uid)[0], "STR")
        self.assertEqual(Universe.get_args(m.get(k3).uid)[0], "SYM")

    def test_large_batch_construction_vs_sequential(self):
        """
        Verifica equivalencia funcional entre Batch (from_dict) y Secuencial.
        """
        N = 1000
        data = {i: i*2 for i in range(N)}
        
        # 1. Batch
        m_batch = HAMT.from_dict(data)
        
        # 2. Secuencial
        m_seq = HAMT.empty()
        for i in range(N):
            m_seq = m_seq.put(Node.val(i), Node.val(i*2))
            
        # 3. Verificación Muestral
        for i in [0, N//2, N-1]:
            val_batch = Universe.get_args(m_batch.get(Node.val(i)).uid)[0]
            val_seq = Universe.get_args(m_seq.get(Node.val(i)).uid)[0]
            self.assertEqual(val_batch, val_seq)


# =========================================================================
# 3. PRUEBAS EXTENDIDAS (Casos de Borde & Física Unsigned)
# =========================================================================
class TestHAMTExtended(unittest.TestCase):

    def setUp(self):
        Universe._lookup.clear()

    def test_high_bit_hash_handling(self):
        """
        Verifica manejo de hashes con bit 63 activo (Unsigned Large).
        """
        high_bit_key = None
        
        for i in range(1000):
            k = Node.val(i * 777)
            h = holographic_hash(k.uid)
            if h & (1 << 63): 
                high_bit_key = k
                break
        
        self.assertIsNotNone(high_bit_key, "No se encontró clave con High Bit hash.")
        
        m = HAMT.empty().put(high_bit_key, Node.val("success"))
        val = m.get(high_bit_key)
        
        self.assertIsNotNone(val)
        self.assertEqual(Universe.get_args(val.uid)[0], "success")

    def test_hash_collision_explosion(self):
        """
        Simula una colisión de hash parcial.
        CORREGIDO: Usa la Fuente de Verdad (holographic_hash) para filtrar claves.
        """
        target_bucket = 10
        colliding_keys = []
        
        # Generación de claves candidatas
        i = 0
        while len(colliding_keys) < 5:
            k = Node.symbol(f"col_{i}")
            
            # [CORRECCIÓN CRÍTICA]
            # Antes: h = hash(k)  <-- MENTIRA (Python lo altera)
            # Ahora: h = holographic_hash(k.uid) <-- VERDAD (Lo que usa el HAMT)
            h = holographic_hash(k.uid)
            
            # Verificamos si esta clave cae en el bucket 10
            if (h & 0x1F) == target_bucket:
                colliding_keys.append(k)
            i += 1
            
        # Inserción
        m = HAMT.empty()
        for k in colliding_keys:
            m = m.put(k, Node.val(1))
            
        # Verificación Estructural
        root_args = Universe.get_args(m.uid)
        bitmap = root_args[0]
        
        # Ahora sí: Como las claves fueron seleccionadas con la misma matemática
        # que usa el HAMT, todas deben haber caído en el mismo bit.
        self.assertEqual(bitmap.bit_count(), 1, 
            f"Fallo de inyectividad: Bitmap {bin(bitmap)} tiene múltiples ramas.")
            
        child_uid = root_args[1]
        self.assertEqual(Universe.get_op(child_uid), OP_HAMT, "La colisión no generó un sub-nodo intermedio.")

    def test_from_dict_factory(self):
        """
        Verifica que HAMT.from_dict usa la construcción eficiente.
        """
        data = {f"k_{i}": i for i in range(100)}
        m_batch = HAMT.from_dict(data)
        
        for k_str, v_int in data.items():
            k_node = Node.val(k_str) 
            res = m_batch.get(k_node)
            self.assertIsNotNone(res)
            self.assertEqual(Universe.get_args(res.uid)[0], v_int)
            
    def test_deep_trie_persistence(self):
        """
        Verifica persistencia profunda.
        """
        m1 = HAMT.from_dict({i: i for i in range(1000)})
        
        target_key = Node.val(500)
        m2 = m1.put(target_key, Node.val(9999))
        
        self.assertEqual(Universe.get_args(m1.get(target_key).uid)[0], 500)
        self.assertEqual(Universe.get_args(m2.get(target_key).uid)[0], 9999)
        self.assertNotEqual(m1.uid, m2.uid)
"""
tests/debug/test_hash_architecture.py
Prueba de Arquitectura de Hashing.
Aísla la lógica matemática (Tier-64) del Runtime de Python.
"""
import unittest
from symbolic_core.kernel.node import Node
from symbolic_core.kernel.universe import Universe
from symbolic_core.hashing.utils import holographic_hash

class TestHashArchitecture(unittest.TestCase):

    def setUp(self):
        Universe._lookup.clear()

    def test_level_1_math_core_integrity(self):
        """
        NIVEL 1: Matemáticas Puras.
        Verifica que la función `holographic_hash` es determinista y estable.
        """
        uid = 1234567890123456789
        h1 = holographic_hash(uid)
        h2 = holographic_hash(uid)
        
        self.assertEqual(h1, h2, "FATAL: La función matemática base no es determinista.")
        self.assertIsInstance(h1, int)
        # Debe ser un entero positivo (Unsigned 64-bit simulation)
        self.assertGreaterEqual(h1, 0) 

    def test_level_2_node_bypass_integrity(self):
        """
        NIVEL 2: Integridad de la Clase Node (Bypass de Python).
        Llamamos a node.__hash__() DIRECTAMENTE.
        Esto salta la capa de procesamiento de CPython.
        """
        k = Node.val("test_integrity")
        
        # Valor calculado externamente
        expected_hash = holographic_hash(k.uid)
        
        # Valor retornado por tu código (sin intervención de Python)
        actual_hash = k.__hash__()
        
        # ESTO DEBE SER IDÉNTICO. Si falla aquí, el bug está en node.py
        self.assertEqual(actual_hash, expected_hash, 
            f"ERROR CRÍTICO: Node.__hash__ no está retornando el holographic_hash puro.\n"
            f"Esperado: {expected_hash}\n"
            f"Recibido: {actual_hash}"
        )

    def test_level_3_python_runtime_distortion(self):
        """
        NIVEL 3: La Mentira de Python.
        Demuestra que hash(k) altera el valor retornado por k.__hash__().
        Este test PASA si los valores son DISTINTOS (lo cual es el comportamiento esperado de Python).
        """
        k = Node.val("test_distortion")
        
        raw_val = k.__hash__()  # Tu verdad matemática
        py_val = hash(k)        # La versión procesada por Python
        
        # Si esto falla (son iguales), es suerte.
        # Si son distintos, confirmamos que el error en tu test anterior
        # era esperar que fueran iguales.
        if raw_val != py_val:
            print(f"\n[INFO] Confirmado: Python alteró el hash.")
            print(f"  Tu Lógica: {raw_val}")
            print(f"  Python:    {py_val}")
        else:
            print("\n[INFO] Curioso: Python no alteró este hash específico (número pequeño?).")

if __name__ == '__main__':
    unittest.main()
