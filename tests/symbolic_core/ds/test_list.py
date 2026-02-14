"""
tests/symbolic_core/ds/test_list.py
Tests para Listas Enlazadas Persistentes.
"""
import time
import unittest
from symbolic_core.ds.list import ConsList
from symbolic_core.kernel.node import Node
from symbolic_core.kernel.universe import Universe

class TestConsList(unittest.TestCase):

    def test_creation_and_traversal(self):
        """
        Verifica cons manual y head/tail.
        """
        nil = ConsList.nil()
        self.assertTrue(nil.is_empty)

        n1 = Node.val(1)
        n2 = Node.val(2)

        # L = [2]
        l1 = ConsList.cons(n2, nil)
        self.assertFalse(l1.is_empty)
        self.assertEqual(l1.head.uid, n2.uid)
        self.assertEqual(l1.tail, nil)

        # L = [1, 2]
        l2 = ConsList.cons(n1, l1)
        self.assertEqual(l2.head.uid, n1.uid)
        self.assertEqual(l2.tail, l1) # Identidad estructural con l1

    def test_structural_sharing_memory(self):
        """
        CRÍTICO: Verifica que dos listas compartan memoria física.
        L1 = [3, 2, 1]
        L2 = [4, 3, 2, 1]
        L2.tail DEBE SER EXACTAMENTE L1 (Mismo ID).
        """
        # Construir base [3, 2, 1]
        base = ConsList.from_python([Node.val(3), Node.val(2), Node.val(1)])
        
        # Construir derivada [4, 3, 2, 1]
        derived = ConsList.cons(Node.val(4), base)
        
        # Verificación O(1) de memoria
        self.assertEqual(derived.tail.uid, base.uid, 
                         "No hay compartición estructural: se duplicó la memoria.")

    def test_python_interop(self):
        """
        Verifica from_python e iteración.
        """
        py_data = [Node.val(i) for i in range(100)]
        
        # 1. Convertir a ConsList
        cons_list = ConsList.from_python(py_data)
        
        # 2. Iterar y reconvertir
        reconstructed = list(cons_list)
        
        self.assertEqual(len(reconstructed), 100)
        
        # Verificar orden y valores
        for orig, recon in zip(py_data, reconstructed):
            self.assertEqual(orig.uid, recon.uid)

    def test_immutability(self):
        """
        Asegura que 'modificar' (crear nueva lista) no altera la original.
        """
        original = ConsList.from_python([Node.val(1)])
        orig_id = original.uid
        
        _ = ConsList.cons(Node.val(2), original)
        
        # Original debe seguir intacta
        self.assertEqual(original.uid, orig_id)
        self.assertEqual(len(original), 1)
    def test_stress_massive_list(self):
        """
        ESTRÉS: Crear lista de 10,000 elementos.
        Verificar que no hay Stack Overflow y que __len__ es correcto.
        """
        N = 10_000
        # Crear N nodos (simulando datos reales)
        # Usamos escalares para velocidad de creación
        py_data = [Node.val(i) for i in range(N)]
        
        start = time.time()
        # from_python usa un bucle iterativo, debería ser seguro
        massive_list = ConsList.from_python(py_data)
        duration = time.time() - start
        
        print(f"\n[PERF] Crear ConsList({N}): {duration:.4f}s")
        
        # 1. Verificar longitud (Iterativo)
        self.assertEqual(len(massive_list), N)
        
        # 2. Verificar integridad del último elemento (Head original)
        # Como from_python invierte, el head de la lista es el index 0 de py_data
        self.assertEqual(massive_list.head.uid, py_data[0].uid)

    def test_functional_map_transformation(self):
        """
        Prueba MAP: Transformar una lista de números [1, 2, 3] -> [2, 4, 6]
        sin mutar la original.
        """
        l1 = ConsList.from_python([Node.val(1), Node.val(2), Node.val(3)])
        
        # Definir función de transformación: x * 2
        def doubler(node: Node) -> Node:
            # 1. Extraer el valor crudo del nodo (int)
            raw_val = Universe.get_args(node.uid)[0]
            # 2. Operar matemáticamente en Python
            new_val = raw_val * 2
            # 3. Empaquetar en un nuevo Nodo
            return Node.val(new_val)
        
        l2 = l1.map(doubler)
        
        # Verificaciones
        # A. Longitud conservada
        self.assertEqual(len(l2), 3)
        
        # B. Valores transformados
        # Node(2), Node(4), Node(6)
        res_values = [Universe.get_args(n.uid)[0] for n in l2]
        self.assertEqual(res_values, [2, 4, 6])
        
        # C. Inmutabilidad (L1 intacta)
        orig_values = [Universe.get_args(n.uid)[0] for n in l1]
        self.assertEqual(orig_values, [1, 2, 3])

    def test_functional_filter_logic(self):
        """
        Prueba FILTER: Filtrar pares de [1, 2, 3, 4] -> [2, 4].
        """
        data = [Node.val(i) for i in [1, 2, 3, 4]]
        l1 = ConsList.from_python(data)
        
        def is_even(node: Node) -> bool:
            val = Universe.get_args(node.uid)[0]
            return val % 2 == 0
            
        filtered = l1.filter(is_even)
        
        # Verificar
        self.assertEqual(len(filtered), 2)
        res_values = [Universe.get_args(n.uid)[0] for n in filtered]
        self.assertEqual(res_values, [2, 4])

    def test_nested_lists_structure(self):
        """
        COMPLEJIDAD: Una lista que contiene otras listas.
        L = [ [1,2], [3] ]
        """
        sub1 = ConsList.from_python([Node.val(1), Node.val(2)])
        sub2 = ConsList.from_python([Node.val(3)])
        
        # Aquí el truco: Las listas son estructuras, pero para meterlas en una ConsList
        # necesitamos sus IDs envueltos en un Node.
        # ¿Cómo representamos una lista dentro de otra?
        # Opción A: Node genérico que apunta al UID de la lista.
        # Opción B: Node con un OpCode especial.
        # Por ahora usamos Node(uid) crudo, ya que Node es un wrapper agnóstico.
        
        node_sub1 = Node(sub1.uid)
        node_sub2 = Node(sub2.uid)
        
        master_list = ConsList.from_python([node_sub1, node_sub2])
        
        self.assertEqual(len(master_list), 2)
        
        # Recuperar y verificar
        first_elem_node = master_list.head
        # Convertir ese Node de vuelta a ConsList
        reconstructed_sub1 = ConsList(first_elem_node.uid)
        
        self.assertEqual(len(reconstructed_sub1), 2)
        self.assertEqual(reconstructed_sub1.head.uid, Node.val(1).uid)

    def test_persistence_branching(self):
        """
        Verifica la ramificación de listas (Y-Shape).
              /-> [10, ...] (L2)
        Base -> [20, ...]
              \-> [30, ...] (L3)
        """
        base = ConsList.from_python([Node.val(20), Node.val(30)])
        
        l2 = ConsList.cons(Node.val(10), base)
        l3 = ConsList.cons(Node.val(99), base)
        
        # Ambas deben compartir la cola 'base'
        self.assertEqual(l2.tail.uid, base.uid)
        self.assertEqual(l3.tail.uid, base.uid)
        
        # Modificar l2 no afecta a l3
        self.assertNotEqual(l2.head.uid, l3.head.uid)

    def test_safety_repr_limit(self):
        """
        Asegura que imprimir una lista gigante no colapse la terminal.
        """
        giant = ConsList.from_python([Node.val(i) for i in range(100)])
        s = repr(giant)
        
        # Debe contener "..." indicando truncamiento
        self.assertIn("...", s)
        # No debe ser ridículamente largo
        self.assertLess(len(s), 1000)
if __name__ == '__main__':
    unittest.main()