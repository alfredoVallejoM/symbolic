"""
src/symbolic_core/ds/list.py
Estructura de Datos Persistente: Lista Enlazada (Cons List).
Versión 2.0: Functional-Ready & Stack-Safe.
"""
from typing import Optional, Iterator, Any, List as PyList, Callable, TypeVar, Generic
from ..kernel.universe import Universe
from ..kernel.node import Node
from ..opcodes import *

# Definimos el ID de NIL de forma segura
_NIL_ID = Universe.intern(OP_SYMBOL, (Universe.intern_blob(b"__NIL__"),))

T = TypeVar('T')

class ConsList:
    """
    Lista Inmutable Persistente.
    Soporta operaciones funcionales (Map, Filter, Fold) y recursión segura.
    """
    __slots__ = ('uid',)

    def __init__(self, uid: int):
        self.uid = uid

    @staticmethod
    def nil() -> 'ConsList':
        return ConsList(_NIL_ID)

    @staticmethod
    def cons(head: Node, tail: 'ConsList') -> 'ConsList':
        """O(1) Prepend."""
        # Validación defensiva: tail debe ser una lista
        if not isinstance(tail, ConsList):
             raise TypeError(f"Tail must be ConsList, got {type(tail)}")
        
        uid = Universe.intern(OP_CONS, (head.uid, tail.uid))
        return ConsList(uid)

    @staticmethod
    def from_python(items: PyList[Node]) -> 'ConsList':
        """O(N). Construye desde una lista Python."""
        acc = ConsList.nil()
        # Iteración inversa para construir O(N) sin recursión
        for item in reversed(items):
            acc = ConsList.cons(item, acc)
        return acc

    @property
    def is_empty(self) -> bool:
        return self.uid == _NIL_ID

    @property
    def head(self) -> Node:
        if self.is_empty: raise IndexError("Head of empty list")
        args = Universe.get_args(self.uid)
        return Node(args[0])

    @property
    def tail(self) -> 'ConsList':
        if self.is_empty: raise IndexError("Tail of empty list")
        args = Universe.get_args(self.uid)
        # Aquí asumimos que el segundo argumento SIEMPRE es una lista válida
        # gracias a la integridad del constructor 'cons'.
        return ConsList(args[1])

    # --- FUNCTIONAL API (High Order Functions) ---

    def map(self, fn: Callable[[Node], Node]) -> 'ConsList':
        """
        Aplica fn(node) a cada elemento y retorna una NUEVA lista persistente.
        Implementación ITERATIVA para evitar Stack Overflow en listas grandes.
        """
        if self.is_empty: return self
        
        # 1. Recolectar resultados en lista Python temporal (rápido en RAM)
        temp_items = []
        curr = self
        while not curr.is_empty:
            temp_items.append(fn(curr.head))
            curr = curr.tail
        
        # 2. Reconstruir ConsList
        return ConsList.from_python(temp_items)

    def filter(self, predicate: Callable[[Node], bool]) -> 'ConsList':
        """Retorna nueva lista solo con nodos que cumplan predicate(node)."""
        if self.is_empty: return self
        
        temp_items = []
        curr = self
        while not curr.is_empty:
            head = curr.head
            if predicate(head):
                temp_items.append(head)
            curr = curr.tail
            
        return ConsList.from_python(temp_items)

    def fold(self, fn: Callable[[Any, Node], Any], initial: Any) -> Any:
        """Reduce la lista a un valor acumulado (Left Fold)."""
        acc = initial
        curr = self
        while not curr.is_empty:
            acc = fn(acc, curr.head)
            curr = curr.tail
        return acc

    # --- PYTHON MAGIC METHODS ---

    def __iter__(self) -> Iterator[Node]:
        """Iterador seguro O(N)."""
        curr = self
        while not curr.is_empty:
            yield curr.head
            curr = curr.tail

    def __len__(self) -> int:
        """O(N) Iterativo. Safe for 1M+ items."""
        count = 0
        curr = self
        while not curr.is_empty:
            count += 1
            curr = curr.tail
        return count

    def __repr__(self):
        """Impresión segura. Trunca si es muy larga."""
        if self.is_empty: return "Nil"
        
        items = []
        count = 0
        limit = 10 # Safety limit para logs
        
        curr = self
        while not curr.is_empty and count < limit:
            items.append(repr(curr.head))
            curr = curr.tail
            count += 1
            
        if not curr.is_empty:
            items.append("...")
            
        return f"List[{', '.join(items)}]"

    def __eq__(self, other):
        """Igualdad estructural O(1)."""
        if not isinstance(other, ConsList): return False
        return self.uid == other.uid