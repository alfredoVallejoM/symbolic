import unittest
from symbolic_core.ds.queue import ImmutableQueue
from symbolic_core.kernel.node import Node
from symbolic_core.kernel.universe import Universe

class TestImmutableQueue(unittest.TestCase):

    def test_fifo_logic(self):
        """Verifica orden First-In First-Out."""
        q0 = ImmutableQueue.empty()
        
        # Encolar 1, 2, 3
        q1 = q0.enqueue(Node.val(1))
        q2 = q1.enqueue(Node.val(2))
        q3 = q2.enqueue(Node.val(3))
        
        # Desencolar
        v1, q4 = q3.dequeue()
        self.assertEqual(Universe.get_args(v1.uid)[0], 1)
        
        v2, q5 = q4.dequeue()
        self.assertEqual(Universe.get_args(v2.uid)[0], 2)
        
        v3, q6 = q5.dequeue()
        self.assertEqual(Universe.get_args(v3.uid)[0], 3)
        
        v4, q7 = q6.dequeue()
        self.assertIsNone(v4)
        self.assertTrue(q7.is_empty)

    def test_persistence(self):
        """
        q1 = [1]
        q2 = q1.enqueue(2) -> [1, 2]
        q1 debe seguir siendo [1]
        """
        q1 = ImmutableQueue.empty().enqueue(Node.val(1))
        q2 = q1.enqueue(Node.val(2))
        
        # q1 dequeue debe dar 1 y quedar vacía
        v, q1_next = q1.dequeue()
        self.assertEqual(Universe.get_args(v.uid)[0], 1)
        self.assertTrue(q1_next.is_empty)
        
        # q2 dequeue debe dar 1 y quedar con [2]
        v, q2_next = q2.dequeue()
        self.assertEqual(Universe.get_args(v.uid)[0], 1)
        self.assertFalse(q2_next.is_empty)
        self.assertEqual(Universe.get_args(q2_next.peek().uid)[0], 2)

    def test_bankers_flip(self):
        """
        Fuerza el caso donde Front se vacía y Rear se invierte.
        Rear: [3, 2] (Push 2, Push 3) -> Front: [2, 3]
        """
        q = ImmutableQueue.empty()
        q = q.enqueue(Node.val(1)) # Front=[1], Rear=[]
        q = q.enqueue(Node.val(2)) # Front=[1], Rear=[2]
        q = q.enqueue(Node.val(3)) # Front=[1], Rear=[3, 2] (ConsList interna)
        
        # Pop 1 (Front vacía -> Trigger Flip)
        v1, q_flipped = q.dequeue()
        self.assertEqual(Universe.get_args(v1.uid)[0], 1)
        
        # Ahora internamente Front debería ser [2, 3] y Rear []
        # Pop 2
        v2, q_final = q_flipped.dequeue()
        self.assertEqual(Universe.get_args(v2.uid)[0], 2)
        
        # Pop 3
        v3, q_empty = q_final.dequeue()
        self.assertEqual(Universe.get_args(v3.uid)[0], 3)

if __name__ == '__main__':
    unittest.main()