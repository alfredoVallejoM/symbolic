import unittest
from symbolic_core.kernel.sectors import SectorManager
from symbolic_core.kernel.universe import Universe
from symbolic_core.kernel.node import Node
from symbolic_core.opcodes import *

class TestLogosEngine(unittest.TestCase):

    def test_singleton_property(self):
        """
        Dos nodos creados idénticamente deben tener el mismo UID.
        """
        x1 = Node.symbol("x")
        x2 = Node.symbol("x")
        
        self.assertEqual(x1.uid, x2.uid)
        self.assertIs(x1 == x2, True)

    def test_algebraic_commutativity(self):
        """
        Verifica que A + B == B + A a nivel de memoria.
        """
        a = Node.symbol("a")
        b = Node.symbol("b")
        
        sum1 = a + b
        sum2 = b + a
        
        self.assertEqual(sum1.uid, sum2.uid, "La normalización conmutativa falló.")
        # Como son el mismo ID, son matemáticamente el mismo objeto

    def test_associativity_structure(self):
        """
        Verifica construcción anidada y APLANAMIENTO.
        (a + b) + c -> Add(a, b, c)
        """
        a = Node.symbol("a")
        b = Node.symbol("b")
        c = Node.symbol("c")
        
        term1 = (a + b) + c
        
        op_outer = Universe.get_op(term1.uid)
        self.assertEqual(op_outer, OP_ADD)
        
        args = Universe.get_args(term1.uid)
        
        # --- CAMBIO CRÍTICO POR NUEVA ESTRATEGIA ---
        # ANTES (Binario): len(args) == 2 -> (sum_ab, c)
        # AHORA (Plano):   len(args) == 3 -> (a, b, c)
        self.assertEqual(len(args), 3, "El aplanamiento no funcionó (se esperaban 3 hijos planos).")
        
        # Verificar que los hijos son los átomos originales
        expected_ids = sorted([a.uid, b.uid, c.uid])
        self.assertEqual(list(args), expected_ids)
        
    def test_blob_storage(self):
        """
        Verifica el almacenamiento de datos binarios.
        """
        data = b"DATA_HEAVY"
        uid = Universe.intern_blob(data)
        
        retrieved = Universe.get_args(uid)
        self.assertEqual(retrieved, data)

    def test_python_integers_auto_boxing(self):
        """
        Verifica que Node.val(5) y x + 5 funcionen.
        """
        x = Node.symbol("x")
        expr = x + 5  # El 5 se convierte en Node automáticamente
        
        op = Universe.get_op(expr.uid)
        self.assertEqual(op, OP_ADD)
    def test_recursive_garbage_collection(self):
        """
        Verifica que al borrar un nodo padre, los hijos decrementan sus referencias.
        [MODIFICADO v3]: Usamos SYMBOL en lugar de VAL para evitar Constant Folding.
        """
        # 1. Crear Hojas (Símbolos para evitar que Add(1,1) se convierta en 2)
        leaf_1 = Node.symbol("L1").uid
        leaf_2 = Node.symbol("L2").uid
        
        # Recuperamos sus índices físicos para chequear el pool
        _, idx1 = Universe._decode_id(leaf_1)
        _, idx2 = Universe._decode_id(leaf_2)
        
        pool_sym = SectorManager.get_pool(OP_SYMBOL)
        
        # Estado inicial: RefCount = 1 (Su propia existencia)
        self.assertEqual(pool_sym._ref_counts[idx1], 1)
        
        # 2. Crear Padre (Estructura) -> Add(L1, L2)
        # Como son símbolos, NO se pliegan. Se crea un nodo ADD real.
        parent = Universe.intern(OP_ADD, (leaf_1, leaf_2))
        
        # Estado Conectado: RefCount = 2 (Existencia + Padre)
        # ESTO ES LO QUE FALLABA ANTES POR CULPA DEL FOLDING
        self.assertEqual(pool_sym._ref_counts[idx1], 2, "El padre no retuvo al hijo 1")
        self.assertEqual(pool_sym._ref_counts[idx2], 2, "El padre no retuvo al hijo 2")
        
        # 3. Borrar Padre
        Universe.delete(parent)
        
        # Estado Final: RefCount = 1 (El padre soltó a los hijos)
        self.assertEqual(pool_sym._ref_counts[idx1], 1, "GC falló: El hijo 1 sigue retenido")
        self.assertEqual(pool_sym._ref_counts[idx2], 1, "GC falló: El hijo 2 sigue retenido")
    def test_lookup_cleanup_no_leaks(self):
        """
        Verifica que el diccionario _lookup no crece infinitamente.
        """
        initial_size = Universe.debug_lookup_size()
        
        # Crear y borrar 1000 objetos
        for i in range(1000):
            uid = Universe.intern(OP_SCALAR, (i + 9000,))
            Universe.delete(uid)
            
        final_size = Universe.debug_lookup_size()
        
        # Si el GC funciona, el tamaño debe ser igual al inicial (o muy cerca si había colisiones previas)
        self.assertEqual(final_size, initial_size, "Memory Leak: Universe._lookup no se está limpiando.")

    def test_resurrection(self):
        """
        Verifica que se puede recrear un objeto que fue borrado.
        """
        # 1. Crear
        uid_1 = Universe.intern(OP_SCALAR, (555,))
        # 2. Borrar
        Universe.delete(uid_1)
        
        # 3. Recrear (Mismos argumentos)
        uid_2 = Universe.intern(OP_SCALAR, (555,))
        
        # Debe ser un objeto válido
        val = Universe.get_args(uid_2)[0]
        self.assertEqual(val, 555)
        
        # Nota: uid_2 PUEDE ser igual a uid_1 si el Allocator reutilizó el slot (LIFO).
        # Esto es comportamiento esperado y deseable.

    def test_blob_gc(self):
        """
        Verifica limpieza de BLOBs (imágenes/tensores).
        """
        data = b'HUGE_TENSOR_DATA'
        uid = Universe.intern_blob(data)
        
        # Verificar existencia en blob_lookup
        self.assertIn(data, Universe._blob_lookup)
        
        # Borrar
        Universe.delete(uid)
        
        # Verificar limpieza
        self.assertNotIn(data, Universe._blob_lookup)

import unittest
import random
from symbolic_core.kernel.sectors import SectorManager
from symbolic_core.kernel.universe import Universe
from symbolic_core.kernel.node import Node
from symbolic_core.opcodes import *
from symbolic_core.hashing.invariants import SHIFT_ENTROPY

class TestHolographicKernel(unittest.TestCase):

    def setUp(self):
        # Limpieza brutal antes de cada test para aislamiento total
        Universe._lookup.clear()
        Universe._blob_lookup.clear()
        # Nota: No reseteamos SectorManager para testear la persistencia de pools,
        # pero sí podríamos resetear sus contadores si fuera necesario.

    # =========================================================================
    # NIVEL 1: NUEVOS OPERADORES Y SINTAXIS (Facilidad de uso)
    # =========================================================================
    
    def test_quantum_operators(self):
        """
        Verifica los operadores @ (Tensor) y ~ (Dual).
        """
        ket_0 = Node.symbol("|0>")
        ket_1 = Node.symbol("|1>")
        
        # 1. Producto Tensorial (@)
        bell_state = ket_0 @ ket_1
        self.assertEqual(Universe.get_op(bell_state.uid), OP_TENSOR)
        
        # 2. Espacio Dual (~)
        bra_0 = ~ket_0
        self.assertEqual(Universe.get_op(bra_0.uid), OP_DUAL)
        
        # 3. Resta y Negativo
        diff = ket_0 - ket_1
        self.assertEqual(Universe.get_op(diff.uid), OP_ADD) # A + (-B)

    # =========================================================================
    # NIVEL 2: HASHING HOLOGRÁFICO (Inyectividad y Dualidad)
    # =========================================================================

    def test_holographic_signatures(self):
        """
        Verifica que el Nodo expone QEC y Entropía.
        Valida las propiedades del Hash de Avalancha.
        """
        x = Node.symbol("x")
        entropy = x.entropy
        
        self.assertNotEqual(entropy, 0, "La entropía no debería ser nula.")
        
        # Verificación de Estabilidad y Determinismo del Hash
        h1 = hash(x)
        h2 = hash(x)
        self.assertEqual(h1, h2, "El hash de Python no es determinista.")
        
        # Verificación de Propiedad Holográfica:
        # El hash debe ser diferente a la entropía pura y al UID puro
        # (Demuestra que hubo mezcla/avalanche)
        self.assertNotEqual(h1, entropy)
        self.assertNotEqual(h1, x.uid)

    def test_map_scale_and_integrity(self):
        """
        Crea un mapa masivo y verifica integridad.
        Requiere que hamt.py esté implementado correctamente.
        """
        N_ITEMS = 500
        py_dict = {i: i*2 for i in range(N_ITEMS)}
        
        huge_map = Node.dict(py_dict)
        
        # Verificar muestra aleatoria
        keys_to_check = random.sample(list(py_dict.keys()), 50)
        for k in keys_to_check:
            # Node.__getitem__ -> HAMT.get -> Debe encontrar la clave
            node_val = huge_map[k]
            raw_val = Universe.get_args(node_val.uid)[0]
            self.assertEqual(raw_val, k*2)

    def test_hash_collision_avoidance(self):
        """
        CRÍTICO: Verifica que símbolos distintos tienen hashes de Python distintos.
        Esto previene la degeneración de HAMTs en listas enlazadas.
        """
        symbols = [Node.symbol(f"var_{i}") for i in range(1000)]
        
        # Recolectamos los hashes
        hashes = set(hash(s) for s in symbols)
        
        # Si la inyectividad es perfecta, el tamaño del set debe ser igual a la lista
        self.assertEqual(len(hashes), 1000, "COLISIÓN DETECTADA: El hashing no es suficientemente inyectivo.")

    # =========================================================================
    # NIVEL 3: BATCH PROCESSING & MEMORY ELASTICITY (Stress Test)
    # =========================================================================

    def test_massive_batch_allocation(self):
        """
        Prueba la corrección del Allocator v4.1.
        Intenta allocar más de lo que cabe en una página por defecto (4096).
        Si el fix de '_expand_memory' falla, esto lanzará IndexError.
        """
        BATCH_SIZE = 10000 # Mayor que PAGE_SIZE (4096)
        
        # Generamos datos brutos (tuplas de enteros)
        # Simulamos creación de 10,000 escalares
        raw_data = [(i,) for i in range(BATCH_SIZE)]
        
        # Usamos intern_batch explícitamente
        uids = Universe.intern_batch(OP_SCALAR, raw_data)
        
        self.assertEqual(len(uids), BATCH_SIZE)
        
        # Verificamos que el último existe
        last_val = Universe.get_args(uids[-1])[0]
        self.assertEqual(last_val, BATCH_SIZE - 1)
        
        # Verificamos salud del Allocator
        pool = SectorManager.get_pool(OP_SCALAR)
        stats = pool.stats()
        self.assertGreaterEqual(stats['capacity'], BATCH_SIZE, "El pool no creció lo suficiente.")

    # =========================================================================
    # NIVEL 4: MAPAS PERSISTENTES (Estructuras de Datos)
    # =========================================================================

    def test_persistent_dict_creation(self):
        """
        Verifica Node.dict(...) y acceso __getitem__.
        """
        # Crear mapa {x: 1, y: 2}
        data = {
            Node.symbol("x"): 1,
            Node.symbol("y"): 2
        }
        my_map = Node.dict(data)
        
        self.assertEqual(Universe.get_op(my_map.uid), OP_HAMT)
        
        # Acceso correcto
        val_x = my_map[Node.symbol("x")]
        self.assertEqual(val_x, Node.val(1))
        
        # Acceso incorrecto
        with self.assertRaises(KeyError):
            _ = my_map[Node.symbol("z")]

    
    def test_map_garbage_collection(self):
        """
        [CORREGIDO] Verifica que al borrar un Mapa, se borran sus contenidos.
        Soporta estructuras profundas (HAMT real).
        """
        # 1. Crear mapa
        k = Node.symbol("unique_key_gc")
        v = Node.symbol("unique_val_gc")
        m = Node.dict({k: v})
        
        # 2. Localizar el nodo KV físico (Navegación Robusta)
        # No asumimos que está en el nivel 1. Bajamos hasta encontrar OP_KV.
        
        def find_kv_uid(root_uid):
            op = Universe.get_op(root_uid)
            args = Universe.get_args(root_uid)
            
            if op == OP_KV:
                return root_uid
            elif op == OP_HAMT:
                # args[0] es bitmap. Hijos son args[1:]
                for child_uid in args[1:]:
                    found = find_kv_uid(child_uid)
                    if found: return found
            return None

        kv_uid = find_kv_uid(m.uid)
        self.assertIsNotNone(kv_uid, "No se encontró el nodo KV dentro del Mapa")

        # Verificar existencia física
        _, kv_phys_idx = Universe._decode_id(kv_uid)
        pool_kv = SectorManager.get_pool(OP_KV)
        # Debe tener ref > 0
        self.assertGreater(pool_kv._ref_counts[kv_phys_idx], 0)
        
        # 3. Borrar Mapa
        Universe.delete(m.uid)
        
        # 4. Verificar limpieza
        # El nodo KV debe haber muerto (ref_count=0 o slot liberado)
        # Si el slot se liberó, ref_count podría ser 0 o reutilizado, pero Universe._lookup no debería tenerlo.
        self.assertNotIn(kv_uid, Universe._lookup, "El nodo KV no se borró del Lookup")
if __name__ == '__main__':
    unittest.main()