"""
src/symbolic_core/hashing/encoder.py
Motor Holográfico v4.3.
Integra:
- Entropía Criptográfica (BLAKE2b).
- Estructura Espectral HDC (Sin aritmética modular, con soporte String/Bytes).
- Física Unsigned estricta.
"""
import hashlib
import struct
from typing import Tuple, List, Any
from ..opcodes import *
from .invariants import *
from .spectral_basis import SpectralEngine
from .utils import holographic_hash # Usamos utilidades comunes si las hay, o lógica interna

class HolonicSignature:
    """Contenedor inmutable del ID Tier-64 (512 bits)."""
    __slots__ = ('full_id', 'depth', 'mass', 'op_code')

    def __init__(self, full_id: int):
        self.full_id = full_id
        # Decodificación Lazy O(1)
        self.depth = (full_id >> SHIFT_DEPTH) & MASK_64
        self.mass  = (full_id >> SHIFT_MASS) & MASK_64
        self.op_code = (full_id >> SHIFT_META) & MASK_OP

    @property
    def qec_syndrome(self) -> int:
        return (self.full_id >> SHIFT_QEC) & MASK_64
    
    @property
    def entropy_hash(self) -> int:
        return (self.full_id >> SHIFT_ENTROPY) & MASK_256

    def __repr__(self):
        return f"<Holon Tier-64 ID={hex(self.full_id)[:18]}... Op={hex(self.op_code)}>"


def compute_signature(op_code: int, 
                      children_ids: Tuple[int, ...], 
                      children_meta: List[Tuple[int, int]],
                      extra_payload: Any = None) -> HolonicSignature:
    """
    Genera la Identidad Holográfica Completa (AdS/CFT).
    """
    
    # ---------------------------------------------------------
    # 1. FÍSICA (Lane 1 - Mass/Depth)
    # ---------------------------------------------------------
    depths = [m[0] for m in children_meta]
    masses = [m[1] for m in children_meta]
    new_depth = compute_depth(op_code, depths)
    new_mass = compute_mass(op_code, masses)

    # ---------------------------------------------------------
    # 2. DOBLE BLINDAJE (Lane 2 & 3)
    # ---------------------------------------------------------
    
    # A) Inicialización Caos (BLAKE2b - Identidad)
    hasher = hashlib.blake2b(digest_size=32)
    hasher.update(struct.pack('<H', op_code)) 
    
    # B) Inicialización Orden (Spectral HDC - Estructura)
    qec_vector = SpectralEngine.get_basis(op_code)
    
    # ---------------------------------------------------------
    # 3. INYECCIÓN DE PAYLOAD (Scalar, Blob, Bitmap)
    # ---------------------------------------------------------
    if op_code == OP_HAMT and extra_payload is not None:
        # Payload: Bitmap (int)
        bitmap_int = extra_payload
        # Serialización dinámica para hasher
        nb = (bitmap_int.bit_length() + 7) // 8 or 1
        hasher.update(bitmap_int.to_bytes(nb, 'little'))
        
        # Estructura: El bitmap rota el vector base
        qec_vector = (qec_vector ^ (bitmap_int & MASK_64)) 
        
    elif op_code == OP_BLOB:
        # Payload: Bytes
        data = extra_payload if extra_payload else b''
        hasher.update(data)
        
        # Estructura: Dispersión masiva
        # Hash FNV-like rápido sobre los primeros bytes para semilla
        if len(data) >= 8:
            blob_seed = int.from_bytes(data[:8], 'little')
        else:
            blob_seed = int.from_bytes(data.ljust(8, b'\0'), 'little')
            
        # Mezclamos usando la base conmutativa
        qec_vector = SpectralEngine.mix_commutative(qec_vector, [blob_seed & MASK_64])
        new_depth, new_mass = 1, 1
        
    elif op_code == OP_SCALAR:
        val = extra_payload
        val_hash = 0
        
        if isinstance(val, int):
            l = (val.bit_length() + 8) // 8
            hasher.update(val.to_bytes(l or 1, 'little', signed=True))
            val_hash = val & MASK_64
            
        elif isinstance(val, float):
             b_val = struct.pack('<d', val)
             hasher.update(b_val)
             val_hash = hash(val) & MASK_64
             
        elif isinstance(val, str):
            # [NUEVO] Soporte String
            b_val = val.encode('utf-8')
            hasher.update(b_val)
            # Usamos hash de Python proyectado a unsigned 64
            val_hash = hash(val) & MASK_64
            
        elif isinstance(val, bytes):
            # [NUEVO] Soporte Bytes directos
            hasher.update(val)
            val_hash = int.from_bytes(val[:8].ljust(8, b'\0'), 'little') & MASK_64
        
        qec_vector = SpectralEngine.mix_commutative(qec_vector, [val_hash])
        new_depth, new_mass = 1, 1

    # ---------------------------------------------------------
    # 4. TOPOLOGÍA DE HIJOS
    # ---------------------------------------------------------
    traits = get_traits(op_code)
    children_qecs = []
    
    for cid in children_ids:
        # -- Caos: Hash del UID completo (Avalancha) --
        cid_bytes = cid.to_bytes((cid.bit_length() + 7) // 8 or 1, 'little')
        hasher.update(cid_bytes)
        
        # -- Orden: Extracción de Lane 2 (QEC) --
        child_qec = (cid >> SHIFT_QEC) & MASK_64
        children_qecs.append(child_qec)
        
    # Mezcla Topológica
    if traits & OpTraits.COMMUTATIVE:
        final_qec = SpectralEngine.mix_commutative(qec_vector, children_qecs)
    else:
        final_qec = SpectralEngine.mix_non_commutative(qec_vector, children_qecs)

    # ---------------------------------------------------------
    # 5. FUSIÓN
    # ---------------------------------------------------------
    digest_entropy = int.from_bytes(hasher.digest(), 'little')
    
    full_id = (
        (digest_entropy << SHIFT_ENTROPY) |
        (final_qec      << SHIFT_QEC)     |
        (new_mass       << SHIFT_MASS)    |
        (new_depth      << SHIFT_DEPTH)   |
        (op_code        << SHIFT_META)
    )
    
    return HolonicSignature(full_id)

def compute_scalar_signature(op_code: int, value: Any) -> HolonicSignature:
    return compute_signature(op_code, (), [], extra_payload=value)

# Helpers Locales
def compute_depth(op, d): return min(max(d) + 1, MASK_64) if d else 1
def compute_mass(op, m): return min(sum(m) + 1, MASK_64)