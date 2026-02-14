"""
src/symbolic_core/ds/hamt.py
Estructura de Datos Persistente: Hash Array Mapped Trie (HAMT) v4.5.
GARANTÍA: Lógica de navegación 100% desacoplada del runtime de Python.
"""
from typing import Optional, TYPE_CHECKING, Dict, Any
from ..kernel.universe import Universe
from ..opcodes import *
# [CRÍTICO] Importamos la calculadora de hash real
from ..hashing.utils import holographic_hash

if TYPE_CHECKING:
    from ..kernel.node import Node

SHIFT_STEP = 5
MASK = 0b11111 

class HAMT:
    __slots__ = ('uid',)

    def __init__(self, uid: int):
        self.uid = uid

    @staticmethod
    def empty() -> 'HAMT':
        uid = Universe.intern(OP_HAMT, (0,))
        return HAMT(uid)
    
    @staticmethod
    def from_dict(data: Dict[Any, Any]) -> 'HAMT':
        from ..kernel.node import Node
        prepared_map = {}
        for k, v in data.items():
            k_node = k if isinstance(k, Node) else Node.val(k)
            v_node = v if isinstance(v, Node) else Node.val(v)
            prepared_map[k_node.uid] = v_node.uid
        root_uid = Universe.from_map(prepared_map)
        return HAMT(root_uid)

    def put(self, key: 'Node', value: 'Node') -> 'HAMT':
        # [SEGURIDAD] Usamos holographic_hash directo.
        # Ignoramos key.__hash__() para evitar la interferencia de Python.
        h = holographic_hash(key.uid)
        new_root_uid = self._put_recursive(self.uid, key, value, h, 0)
        return HAMT(new_root_uid)

    def get(self, key: 'Node') -> Optional['Node']:
        # [SEGURIDAD] Idem.
        h = holographic_hash(key.uid)
        return self._get_recursive(self.uid, key, h, 0)
    
    def __getitem__(self, key: 'Node') -> 'Node':
        val = self.get(key)
        if val is None:
            raise KeyError(f"Clave no encontrada: {key}")
        return val

    # --- Lógica Interna Recursiva ---

    def _put_recursive(self, node_uid: int, key: 'Node', value: 'Node', h: int, shift: int) -> int:
        op = Universe.get_op(node_uid)
        args = Universe.get_args(node_uid)

        if op == OP_HAMT:
            bitmap = args[0]
            children = args[1:]
            
            # Aritmética pura de 64 bits (h viene de holographic_hash)
            bit_index = (h >> shift) & MASK
            bit_mask = 1 << bit_index
            
            exists = (bitmap & bit_mask) != 0
            child_idx = (bitmap & (bit_mask - 1)).bit_count()
            
            if exists:
                child_uid = children[child_idx]
                new_child_uid = self._put_recursive(child_uid, key, value, h, shift + SHIFT_STEP)
                
                new_children = list(children)
                new_children[child_idx] = new_child_uid 
                return Universe.intern(OP_HAMT, (bitmap, *new_children))
            else:
                new_leaf_uid = Universe.intern(OP_KV, (key.uid, value.uid))
                
                new_children = list(children)
                new_children.insert(child_idx, new_leaf_uid)
                new_bitmap = bitmap | bit_mask
                
                return Universe.intern(OP_HAMT, (new_bitmap, *new_children))

        elif op == OP_KV:
            existing_key_uid = args[0]
            existing_val_uid = args[1]
            
            if existing_key_uid == key.uid:
                return Universe.intern(OP_KV, (key.uid, value.uid))
            
            # Colisión
            empty_hamt_uid = Universe.intern(OP_HAMT, (0,))
            sub_hamt_uid = self._put_recursive_raw(empty_hamt_uid, existing_key_uid, existing_val_uid, shift)
            return self._put_recursive(sub_hamt_uid, key, value, h, shift)

        raise ValueError(f"CRITICAL: HAMT corrupto. OpCode {hex(op)}")

    def _put_recursive_raw(self, node_uid: int, k_uid: int, v_uid: int, shift: int) -> int:
        from ..kernel.node import Node
        # [SEGURIDAD] Recalcular hash puro desde UID crudo
        h = holographic_hash(k_uid)
        
        # Instanciamos Node wrappers solo para pasar el chequeo de tipos si fuera necesario
        # o pasamos UIDs si refactorizamos _put_recursive para aceptar UIDs.
        # Por ahora, mantenemos la firma con Node.
        k_node = Node(k_uid)
        v_node = Node(v_uid)
        
        return self._put_recursive(node_uid, k_node, v_node, h, shift)

    def _get_recursive(self, node_uid: int, key: 'Node', h: int, shift: int) -> Optional['Node']:
        op = Universe.get_op(node_uid)
        args = Universe.get_args(node_uid)

        if op == OP_HAMT:
            bitmap = args[0]
            bit_index = (h >> shift) & MASK
            bit_mask = 1 << bit_index
            
            if (bitmap & bit_mask) == 0:
                return None
            
            child_idx = (bitmap & (bit_mask - 1)).bit_count()
            child_uid = args[1 + child_idx]
            
            return self._get_recursive(child_uid, key, h, shift + SHIFT_STEP)

        elif op == OP_KV:
            if args[0] == key.uid:
                from ..kernel.node import Node
                return Node(args[1])
            return None

        return None