"""
src/symbolic_core/opcodes.py
Ontología Fundamental v3.2 (Clean Ontology).
Define los Tipos de Materia y sus Simetrías Físicas.
"""
from enum import IntFlag

# =============================================================================
# BIT LAYOUT (Physical Pointer / 64-bit Signed Integer)
# =============================================================================
# [63]    : TAG BIT (1 = Inmediato/SmallInt, 0 = Puntero)
# [62]    : SIGN BIT (Para SmallInts)
# [56-62] : OPCODE (7 bits -> 128 Tipos posibles) si Tag=0
# [0-55]  : PAYLOAD/INDEX (56 bits -> 72 Petabytes de direccionamiento)
# =============================================================================

MASK_TAG      = 0x8000000000000000
MASK_OPCODE   = 0x7F00000000000000
MASK_PAYLOAD  = 0x00FFFFFFFFFFFFFF

SHIFT_OPCODE  = 56

# =============================================================================
# ALGEBRAIC TRAITS (Leyes de Simetría)
# =============================================================================
class OpTraits(IntFlag):
    NONE          = 0
    COMMUTATIVE   = 1 << 0  # A·B = B·A (El Canonizer ordena los hijos)
    ASSOCIATIVE   = 1 << 1  # (A·B)·C = A·(B·C) (El Strategy aplana)
    IDEMPOTENT    = 1 << 2  # A·A = A
    IDENTITY_ZERO = 1 << 3  # Elemento neutro es 0
    IDENTITY_ONE  = 1 << 4  # Elemento neutro es 1
    INVOLUTIVE    = 1 << 5  # f(f(x)) = x
    ANTISYMMETRIC = 1 << 6  # A·B = -B·A

# =============================================================================
# OPCODES (Tipos de Materia)
# =============================================================================

# --- GRUPO 0: PRIMITIVOS & MEMORIA ---
OP_SCALAR     = 0x01  # Enteros, Floats (Átomos)
OP_BLOB       = 0x02  # Datos binarios (Imágenes, Weights)
OP_CHUNK      = 0x03  # VList Chunk

# --- GRUPO 1: ÁLGEBRA ---
OP_SYMBOL     = 0x10  # Variable simbólica 'x'
OP_ADD        = 0x11  # Suma
OP_MUL        = 0x12  # Producto
OP_POW        = 0x13  # Potencia
OP_EXP        = 0x14  # Exponencial

# --- GRUPO 2: ESTRUCTURAS DE DATOS ---
OP_CONS       = 0x20  # Lista Enlazada (Head, Tail)
OP_QUEUE      = 0x21  # Cola Persistente
OP_HAMT       = 0x22  # Nodo Interno de Mapa (Bitmap, Children)
OP_KV         = 0x23  # Hoja Clave-Valor (Colisiones HAMT)
OP_VECTOR     = 0x24  # Nodo RRB-Tree (Array)

# --- GRUPO 3: NAVEGACIÓN ---
OP_ZIPPER     = 0x30  # (Focus, Path)
OP_LENS       = 0x31  # (Getter, Setter)

# --- GRUPO 4: LÓGICA & CATEGORÍA ---
OP_TENSOR     = 0x40  # Producto Tensorial
OP_DUAL       = 0x41  # Espacio Dual
OP_CONTRACT   = 0x42  # Traza / Contracción
OP_LAMBDA     = 0x43  # Función Anónima

# --- GRUPO 5: META & IA ---
OP_GRAD       = 0x50  # Nodo Gradiente (AutoDiff)
OP_COST       = 0x51  # Nodo de Coste
OP_NATIVE     = 0x52  # Puntero a función JIT

# =============================================================================
# REGISTRO DE LEYES (Vinculación Ontológica)
# =============================================================================
TRAITS_REGISTRY = {
    OP_ADD:    OpTraits.COMMUTATIVE | OpTraits.ASSOCIATIVE | OpTraits.IDENTITY_ZERO,
    OP_MUL:    OpTraits.COMMUTATIVE | OpTraits.ASSOCIATIVE | OpTraits.IDENTITY_ONE,
    OP_TENSOR: OpTraits.ASSOCIATIVE | OpTraits.IDENTITY_ONE, # ¡No Conmutativo!
    OP_DUAL:   OpTraits.INVOLUTIVE,
    
    # Estructuras de Datos: Orden Estricto (No Conmutativo)
    OP_CONS:   OpTraits.NONE, 
    OP_HAMT:   OpTraits.NONE, # Vital: El orden de hijos es posicional (Bitmap), no por ID.
    OP_KV:     OpTraits.NONE, # Vital: Key != Value.
    
    OP_SYMBOL: OpTraits.NONE,
}

def get_traits(op_code: int) -> OpTraits:
    """Retorna las leyes físicas del operador."""
    return TRAITS_REGISTRY.get(op_code, OpTraits.NONE)