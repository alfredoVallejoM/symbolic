"""
src/symbolic_core/ds/queue.py
Estructura de Datos Persistente: Banker's Queue.
Amortized O(1) FIFO operations.
"""
from typing import Optional, Tuple, Iterator
from ..kernel.universe import Universe
from ..kernel.node import Node
from ..opcodes import *
from .list import ConsList

class ImmutableQueue:
    """
    Cola FIFO Persistente.
    Implementada con dos ConsLists: Front (Salida) y Rear (Entrada).
    Invariant: Si Front está vacía, Rear también debe estarlo (se vuelca).
    """
    __slots__ = ('uid',)

    def __init__(self, uid: int):
        self.uid = uid

    @staticmethod
    def empty() -> 'ImmutableQueue':
        """Crea una cola vacía."""
        # Representación física: Queue(Nil, Nil)
        nil = ConsList.nil()
        uid = Universe.intern(OP_QUEUE, (nil.uid, nil.uid))
        return ImmutableQueue(uid)

    @staticmethod
    def _make(front: ConsList, rear: ConsList) -> 'ImmutableQueue':
        if front.is_empty:
            if not rear.is_empty:
                # CORRECCIÓN:
                # Rear (Stack): Top->[3, 2, 1]->Nil.  list(rear) -> [3, 2, 1]
                # Queremos Front (Queue): Head->1->2->3->Nil.
                # ConsList.from_python([A, B]) crea Head->A->B.
                # Por tanto, necesitamos pasarle [1, 2, 3].
                # Solución: reversed(list(rear))
                
                items = list(rear)
                front = ConsList.from_python(list(reversed(items)))
                rear = ConsList.nil()
        
        uid = Universe.intern(OP_QUEUE, (front.uid, rear.uid))
        return ImmutableQueue(uid)

    def enqueue(self, item: Node) -> 'ImmutableQueue':
        """Añade al final. O(1)."""
        front, rear = self._unpack()
        # Añadimos al principio de la lista 'rear' (que actúa como pila de entrada)
        new_rear = ConsList.cons(item, rear)
        return ImmutableQueue._make(front, new_rear)

    def dequeue(self) -> Tuple[Optional[Node], 'ImmutableQueue']:
        """
        Retorna (Head, NewQueue).
        Si está vacía, retorna (None, Self).
        Amortizado O(1).
        """
        front, rear = self._unpack()
        
        if front.is_empty:
            return None, self
            
        head = front.head
        new_front = front.tail
        
        # Usamos _make para rebalancear si new_front quedó vacía
        return head, ImmutableQueue._make(new_front, rear)

    def peek(self) -> Optional[Node]:
        """Mira el primer elemento sin sacarlo."""
        front, _ = self._unpack()
        if front.is_empty: return None
        return front.head

    @property
    def is_empty(self) -> bool:
        front, _ = self._unpack()
        return front.is_empty

    def _unpack(self) -> Tuple[ConsList, ConsList]:
        args = Universe.get_args(self.uid)
        return ConsList(args[0]), ConsList(args[1])

    def __len__(self) -> int:
        f, r = self._unpack()
        return len(f) + len(r)

    def __repr__(self):
        # Para debug, mostramos la secuencia lógica completa
        # Esto es costoso O(N), solo para print
        items = []
        curr = self
        while not curr.is_empty:
            head, curr = curr.dequeue()
            if head: items.append(repr(head))
        return f"Queue[{', '.join(items)}]"