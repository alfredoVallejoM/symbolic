"""
src/symbolic_core/hashing/invariants.py
Geometría Tier-64 Holográfica y Leyes de Conservación.
Define el layout 'Compact Double Shield' (512 bits).
"""

# =============================================================================
# TIER-64 BIT LAYOUT (512 Bits / 64 Bytes)
# =============================================================================
# Estructura de Memoria del ID:
# [ Lane 3: Entropy (256b) | Lane 2: QEC (64b) | Lane 1: Mass/Depth (128b) | Lane 0: Meta (64b) ]

# Tamaños en bits
BITS_ENTROPY = 256  # Hash Criptográfico (Caos / BLAKE2b)
BITS_QEC     = 64   # Síndrome Algebraico (Orden / Galois Field)
BITS_MASS    = 64   # Invariante Bariónico
BITS_DEPTH   = 64   # Invariante Temporal (Radio Hiperbólico)
BITS_META    = 64   # OpCode (16) + Flags/Padding (48)

# Desplazamientos (Shifts) - Construcción Lógica Little Endian
SHIFT_META    = 0
SHIFT_OP      = 0   # Alias crítico para el Universe (OpCode empieza en bit 0)
SHIFT_DEPTH   = 64
SHIFT_MASS    = 128
SHIFT_QEC     = 192
SHIFT_ENTROPY = 256

# Máscaras de Extracción
MASK_64  = 0xFFFFFFFFFFFFFFFF
MASK_256 = (1 << 256) - 1
MASK_OP  = 0xFFFF

# =============================================================================
# FÍSICA NEWTONIANA & HIPERBÓLICA
# =============================================================================

def compute_mass(op_code: int, children_masses: list[int]) -> int:
    """
    Calcula la Masa Bariónica.
    Ley: La masa se conserva. M(Padre) = Σ M(Hijos) + Energía de Enlace (1).
    """
    if not children_masses: return 1
    # Usamos sum() nativo que es muy rápido en CPython
    return sum(children_masses) + 1

def compute_depth(op_code: int, children_depths: list[int]) -> int:
    """
    Calcula la Profundidad Temporal (Radio en Espacio AdS).
    Ley: T(Padre) = Max(T(Hijos)) + 1.
    Esto define la métrica de distancia hiperbólica d(u,v).
    """
    if not children_depths: return 1
    
    # Búsqueda manual de máximo es ligeramente más rápida que max() en listas pequeñas
    max_d = 0
    for d in children_depths:
        if d > max_d: max_d = d
    return max_d + 1