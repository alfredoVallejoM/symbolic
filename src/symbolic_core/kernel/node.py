"""
src/symbolic_core/kernel/node.py
Facade Algebraica v3.6.
Corrección Crítica: Hashing Inyectivo para HAMT y soporte de Mapas Persistentes.
"""
from typing import Any, Union, Dict
from ..opcodes import *
from .universe import Universe
from ..hashing.invariants import SHIFT_ENTROPY, SHIFT_QEC, MASK_64 # Importamos la geometría completa
from ..hashing.utils import holographic_hash


class Node:
    """
    Handle inmutable Tier-64.
    Facade para manipulación algebraica y estructuras de datos persistentes.
    """
    __slots__ = ('uid',)

    def __init__(self, uid: int):
        self.uid = uid

    # --- Constructores Estáticos ---
    @staticmethod
    def symbol(name: str) -> 'Node':
        name_bytes = name.encode('utf-8')
        name_id = Universe.intern_blob(name_bytes)
        uid = Universe.intern(OP_SYMBOL, (name_id,))
        return Node(uid)

    @staticmethod
    def val(value: Union[int, float]) -> 'Node':
        uid = Universe.intern(OP_SCALAR, (value,))
        return Node(uid)

    @staticmethod
    def dict(data: Dict[Any, Any]) -> 'Node':
        """
        Crea un Mapa Persistente (HAMT) a partir de un dict de Python.
        Convierte recursivamente claves y valores a Nodos.
        """
        prepared_map = {}
        for k, v in data.items():
            # Aseguramos que k y v sean UIDs válidos
            k_node = Node._ensure_static(k)
            v_node = Node._ensure_static(v)
            prepared_map[k_node.uid] = v_node.uid
            
        # Delegamos al Universo la construcción masiva
        uid = Universe.from_map(prepared_map)
        return Node(uid)

    # --- Aritmética Básica ---
    def __add__(self, other: Any) -> 'Node':
        uid = Universe.intern(OP_ADD, (self.uid, self._ensure_node(other).uid))
        return Node(uid)

    def __mul__(self, other: Any) -> 'Node':
        uid = Universe.intern(OP_MUL, (self.uid, self._ensure_node(other).uid))
        return Node(uid)

    def __pow__(self, power: Any) -> 'Node':
        uid = Universe.intern(OP_POW, (self.uid, self._ensure_node(power).uid))
        return Node(uid)

    # --- Aritmética Extendida ---
    def __neg__(self) -> 'Node':
        return self * Node.val(-1)

    def __sub__(self, other: Any) -> 'Node':
        return self + (-self._ensure_node(other))

    # --- Operadores Cuánticos ---
    def __invert__(self) -> 'Node':
        """ ~A -> Dual(A) """
        uid = Universe.intern(OP_DUAL, (self.uid,))
        return Node(uid)

    def __matmul__(self, other: Any) -> 'Node':
        """ A @ B -> Tensor(A, B) """
        uid = Universe.intern(OP_TENSOR, (self.uid, self._ensure_node(other).uid))
        return Node(uid)

    # --- Acceso a Estructuras de Datos (Mapas) ---
    def __getitem__(self, key: Any) -> 'Node':
        """
        Acceso a Mapa Persistente: nodo[clave].
        Requiere que el nodo sea OP_HAMT.
        """
        if Universe.get_op(self.uid) != OP_HAMT:
            raise TypeError(f"Este nodo no es un Mapa (OpCode: {hex(Universe.get_op(self.uid))})")
        
        # Importación Local para evitar ciclos (Node -> HAMT -> Node)
        from ..ds.hamt import HAMT
        
        # Usamos la lógica de búsqueda del HAMT
        val_node = HAMT(self.uid).get(self._ensure_node(key))
        
        if val_node is None:
            raise KeyError(f"Clave no encontrada: {key}")
        return val_node

    # --- Dunders de Reflexión ---
    def __radd__(self, other): return self + other
    def __rmul__(self, other): return self * other
    def __rsub__(self, other): return self._ensure_node(other) + (-self)

    @property
    def entropy(self) -> int:
        """
        Retorna la Firma Entrópica (BLAKE2b).
        Representa el 'Volumen' o contenido de información.
        """
        return (self.uid >> SHIFT_ENTROPY) # Bits altos
        
    @property
    def qec(self) -> int:
        """
        Retorna la Firma Algebraica (Quantum Error Correction / Syndrome).
        Representa la 'Topología' o estructura matemática.
        Vital para comprobar isomorfismos de grafos sin mirar el contenido.
        """
        return (self.uid >> SHIFT_QEC) & MASK_64

    # --- IDENTIDAD Y HASHING (AVALANCHE MIXER) ---

    def __eq__(self, other):
        """
        Igualdad Estricta O(1).
        Verifica la identidad del UID completo (512 bits).
        """
        if isinstance(other, Node):
            return self.uid == other.uid
        if isinstance(other, (int, float)):
            # Optimización: Solo internamos si es necesario comparar
            return self.uid == Node.val(other).uid
        return False

    def __hash__(self):
        """
        Holographic Avalanche Mixer v5.0.
        Delega en la utilidad central para consistencia absoluta con Universe.
        """
        return holographic_hash(self.uid)
    # --- Utilidades ---
    def _ensure_node(self, obj: Any) -> 'Node':
        return self._ensure_static(obj)
    
    def similarity(self, other: Any) -> float:
        """
        Medición de Similitud Topológica (Métrica CFT).
        Calcula la correlación estructural entre dos nodos basándose en su
        Firma Espectral (QEC/LSH).
        
        Escala:
        - 1.0 : Estructuralmente Idénticos (Isomorfos o el mismo objeto).
        - 0.5 : Ortogonales (Sin relación estructural directa, independientes).
        - 0.0 : Anti-correlacionados (Opuestos topológicos, ej: A vs -A en ciertos contextos).
        """
        # 1. Guardián de Tipos
        if not isinstance(other, Node):
            # Si comparamos con algo que no es un Nodo, la similitud estructural es nula/indefinida.
            # (O podríamos intentar convertirlo si es un escalar).
            return 0.0
            
        # 2. Extracción de Firmas (Lane 2 del Tier-64)
        # Usamos las propiedades ya cacheadas o extraídas bitwise.
        sig_a = self.qec
        sig_b = other.qec
        
        # 3. Cálculo de Distancia de Hamming (XOR)
        # diff tiene un 1 donde los bits de las firmas difieren.
        diff = sig_a ^ sig_b
        
        # 4. Normalización Hiperdimensional
        # En un espacio de 64 dimensiones:
        # Similitud = 1 - (Bits_Diferentes / Total_Dimensiones)
        return 1.0 - (diff.bit_count() / 64.0)

    def is_isomorphic(self, other: 'Node', threshold: float = 0.95) -> bool:
        """
        Helper para detección rápida de isomorfismos aproximados.
        Útil para el problema del subgrafo o simplificación.
        """
        return self.similarity(other) >= threshold

    @staticmethod
    def _ensure_static(obj: Any) -> 'Node':
        """Helper estático para conversiones inteligentes."""
        if isinstance(obj, Node): return obj
        if isinstance(obj, (int, float)): return Node.val(obj)
        # [MEJORA] Si es string, conviértelo a Escalar String (para claves de dict)
        # o a Símbolo, según tu semántica preferida. 
        # Para map keys ("k_0"), lo normal es scalar string.
        if isinstance(obj, str): return Node.val(obj) 
        
        raise TypeError(f"No se puede convertir {type(obj)} a Node")
    def __repr__(self):
        try:
            op = Universe.get_op(self.uid)
            if op == OP_SCALAR:
                return str(Universe.get_args(self.uid)[0])
            if op == OP_SYMBOL:
                name_id = Universe.get_args(self.uid)[0]
                name_bytes = Universe.get_args(name_id)
                return name_bytes.decode('utf-8')
            if op == OP_HAMT:
                return f"<Map:{self.uid & 0xFFFF}>"
            
            return f"<{OP_NAMES.get(op, 'OP')}:{self.uid & 0xFFFF}>"
        except:
            return f"<DeadNode:{self.uid}>"

# Diccionario inverso para debug
OP_NAMES = {
    OP_SCALAR: "SCALAR", OP_SYMBOL: "SYM", OP_ADD: "ADD", 
    OP_MUL: "MUL", OP_POW: "POW", OP_TENSOR: "TENSOR", 
    OP_DUAL: "DUAL", OP_EXP: "EXP", OP_HAMT: "HAMT", OP_KV: "KV"
}