"""
src/symbolic_core/kernel/universe.py
Versión 4.8 (Holographic Industrial Kernel).
Puente entre la Identidad Matemática (Tier-64) y la Memoria Física.

NOVEDADES v4.8:
- Integración de 'holographic_hash' centralizado (Fix Unsigned).
- Constructor 'from_map' con Root Wrapper (Fix TypeError).
- GC Explícito para SYMBOL y KV (Fix Zombie Nodes).
"""
import threading
from typing import Tuple, Dict, Any, List, Optional

from ..opcodes import *
from .sectors import SectorManager
from .strategies import NormalizationStrategy
from ..memory.allocator import MemoryPool

# --- IMPORTACIONES HOLÓNICAS ---
# [CRÍTICO] Usamos la utilidad central para garantizar aritmética idéntica a Node/HAMT
from ..hashing.utils import holographic_hash
from ..hashing.encoder import compute_signature, compute_scalar_signature
from ..hashing.canonization import Canonizer
from ..hashing.invariants import SHIFT_DEPTH, SHIFT_MASS, MASK_64, SHIFT_OP, MASK_OP

class Universe:
    # Candado Reentrante para operaciones recursivas
    _lock = threading.RLock()    
    
    # Hash Consing: UID -> Índice Físico
    _lookup: Dict[int, int] = {}
    
    # Cache de Blobs: Contenido -> Índice Físico
    _blob_lookup: Dict[bytes, int] = {}

    # =========================================================================
    # SINGLE ITEM INTERN (Unitario)
    # =========================================================================
    @classmethod
    def intern(cls, op_code: int, args: Tuple[int, ...]) -> int:
        """
        Crea o recupera un nodo individual.
        """
        # 1. Seguridad de Tipos
        if op_code == OP_SCALAR:
            if len(args) != 1: raise ValueError("OP_SCALAR requiere aridad 1.")
            return cls.intern_val(args[0])

        # 2. Normalización y Canonización
        new_op, new_args = NormalizationStrategy.normalize(op_code, args, cls)
        if new_op == OP_SCALAR: return cls.intern_val(new_args[0])
        args_canonical = Canonizer.sort_args(new_op, new_args)

        # 3. Cálculo de Firma
        args_meta = []
        if new_op == OP_HAMT:
            if not args_canonical: raise ValueError("OP_HAMT sin argumentos.")
            bitmap = args_canonical[0] 
            children_uids = args_canonical[1:] 
            for uid in children_uids:
                args_meta.append(cls._extract_meta_fast(uid))
            sig = compute_signature(new_op, children_uids, args_meta, extra_payload=bitmap)
        else:
            for uid in args_canonical:
                args_meta.append(cls._extract_meta_fast(uid))
            sig = compute_signature(new_op, args_canonical, args_meta)

        full_id = sig.full_id

        # 4. Hash Consing Optimista
        if full_id in cls._lookup: return full_id

        # 5. Materialización (Zona Crítica)
        with cls._lock:
            if full_id in cls._lookup: return full_id
            pool = SectorManager.get_pool(new_op)
            
            # --- GESTIÓN DE REFERENCIAS (GC) v4.8 ---
            # Definimos explícitamente qué argumentos son punteros que mantienen vida.
            
            if new_op == OP_HAMT:
                # args[0] es Bitmap (Data). args[1:] son Nodos (Punteros).
                for i in range(1, len(args_canonical)):
                    cls._retain_node(args_canonical[i])
            
            elif new_op == OP_KV:
                # args[0] es Key, args[1] es Value. Ambos se retienen.
                cls._retain_node(args_canonical[0])
                cls._retain_node(args_canonical[1])
                
            elif new_op == OP_SYMBOL:
                # args[0] es el UID del Blob (Nombre). Se retiene.
                cls._retain_node(args_canonical[0])
                
            elif new_op not in (OP_SCALAR, OP_BLOB, OP_CHUNK):
                # Caso estándar (ADD, MUL, etc.): Todos son hijos.
                for arg_uid in args_canonical:
                    cls._retain_node(arg_uid)
            # ----------------------------------------

            phys_idx = pool.alloc(args_canonical)
            cls._lookup[full_id] = phys_idx
            
            return full_id

    # =========================================================================
    # BATCH PROCESSING (Vectorial)
    # =========================================================================
    @classmethod
    def intern_batch(cls, op_code: int, list_of_args: List[Tuple[int, ...]]) -> List[int]:
        """Procesamiento Vectorial Masivo."""
        results = [0] * len(list_of_args)
        to_alloc_indices = []
        to_alloc_ids = []
        to_alloc_data = []

        # Fase 1: Cálculo CPU
        for i, args in enumerate(list_of_args):
            if op_code == OP_HAMT:
                if not args: continue
                bitmap = args[0]
                children_uids = args[1:]
                args_meta = [cls._extract_meta_fast(uid) for uid in children_uids]
                sig = compute_signature(op_code, children_uids, args_meta, extra_payload=bitmap)
            else:
                args_meta = [cls._extract_meta_fast(uid) for uid in args]
                sig = compute_signature(op_code, args, args_meta)
            
            full_id = sig.full_id
            if full_id in cls._lookup:
                results[i] = full_id
            else:
                to_alloc_indices.append(i)
                to_alloc_ids.append(full_id)
                to_alloc_data.append(args)

        if not to_alloc_ids: return results

        # Fase 2: Alloc Masivo
        with cls._lock:
            pool = SectorManager.get_pool(op_code)
            final_alloc_data = []
            final_alloc_map_indices = []
            
            for k, full_id in enumerate(to_alloc_ids):
                if full_id in cls._lookup:
                    results[to_alloc_indices[k]] = full_id
                else:
                    final_alloc_data.append(to_alloc_data[k])
                    final_alloc_map_indices.append(k)

            if final_alloc_data:
                phys_indices = pool.alloc_batch(final_alloc_data)
                
                # GC Batch
                if op_code == OP_HAMT:
                    for args_tuple in final_alloc_data:
                        for i in range(1, len(args_tuple)): cls._retain_node(args_tuple[i])
                elif op_code == OP_KV:
                    for args_tuple in final_alloc_data:
                        cls._retain_node(args_tuple[0])
                        cls._retain_node(args_tuple[1])
                elif op_code not in (OP_SCALAR, OP_BLOB, OP_SYMBOL, OP_CHUNK):
                    for args_tuple in final_alloc_data:
                        for arg_uid in args_tuple: cls._retain_node(arg_uid)

                for k, phys_idx in enumerate(phys_indices):
                    map_idx = final_alloc_map_indices[k]
                    original_idx = to_alloc_indices[map_idx]
                    uid = to_alloc_ids[map_idx]
                    cls._lookup[uid] = phys_idx
                    results[original_idx] = uid

        return results

    # =========================================================================
    # MAPAS / HAMT (Construcción Canónica)
    # =========================================================================
    @classmethod
    def from_map(cls, python_dict: Dict[int, int]) -> int:
        """
        Construye un HAMT topológicamente perfecto (Bottom-Up).
        Usa 'holographic_hash' para garantizar consistencia Unsigned.
        """
        if not python_dict:
            return cls.intern(OP_HAMT, (0,))

        # 1. Crear Hojas KV
        items = list(python_dict.items())
        pair_uids = cls.intern_batch(OP_KV, items)
        
        # 2. Asociar Hash Holográfico (Unsigned) con Hoja
        leaf_nodes = []
        for (k_uid, _), kv_node_uid in zip(items, pair_uids):
            # [CRÍTICO] Usamos la utilidad centralizada.
            # Esto evita discrepancias de signo con HAMT.get()
            h_val = holographic_hash(k_uid)
            leaf_nodes.append((h_val, kv_node_uid))
            
        leaf_nodes.sort(key=lambda x: x[0])
        
        # 3. Construir Árbol
        root_uid = cls._build_hamt_recursive(leaf_nodes, 0)
        
        # 4. Root Wrapper (Fix TypeError)
        # Si el resultado es una hoja KV suelta (mapa de 1 elemento),
        # debemos envolverla en un HAMT para que sea un contenedor válido.
        if cls.get_op(root_uid) == OP_KV:
            h_val = leaf_nodes[0][0]
            idx = h_val & 0x1F
            bitmap = 1 << idx
            root_uid = cls.intern(OP_HAMT, (bitmap, root_uid))
            
        return root_uid

    @classmethod
    def _build_hamt_recursive(cls, sorted_items: List[Tuple[int, int]], shift: int) -> int:
        """Recursión de partición por buckets de 5 bits."""
        # Caso Base: Hoja Única o Colisión Perfecta
        if len(sorted_items) == 1:
            return sorted_items[0][1]

        # Partición en 32 buckets
        buckets = [[] for _ in range(32)]
        mask = 0x1F
        
        for h_val, uid in sorted_items:
            idx = (h_val >> shift) & mask
            buckets[idx].append((h_val, uid))
            
        # Construcción del Nodo
        bitmap = 0
        children_uids = []
        
        for i, bucket in enumerate(buckets):
            if bucket:
                bitmap |= (1 << i)
                child_uid = cls._build_hamt_recursive(bucket, shift + 5)
                children_uids.append(child_uid)
                
        return cls.intern(OP_HAMT, (bitmap,) + tuple(children_uids))

    # =========================================================================
    # VALORES & BLOBS
    # =========================================================================
    @classmethod
    def intern_val(cls, value: Any) -> int:
        sig = compute_scalar_signature(OP_SCALAR, value)
        uid = sig.full_id
        if uid in cls._lookup: return uid
        with cls._lock:
            if uid in cls._lookup: return uid
            pool = SectorManager.get_pool(OP_SCALAR)
            phys_idx = pool.alloc((value,))
            cls._lookup[uid] = phys_idx
            return uid

    @classmethod
    def intern_blob(cls, data: bytes) -> int:
        if data in cls._blob_lookup:
            phys_idx = cls._blob_lookup[data]
            pool = SectorManager.get_pool(OP_BLOB)
            stored_data = pool.get(phys_idx)
            if stored_data: return stored_data[0] 

        sig = compute_signature(OP_BLOB, (), [], extra_payload=data)
        uid = sig.full_id
        if uid in cls._lookup: return uid

        with cls._lock:
            if uid in cls._lookup: return uid
            pool = SectorManager.get_pool(OP_BLOB)
            phys_idx = pool.alloc((uid, data))
            cls._lookup[uid] = phys_idx
            cls._blob_lookup[data] = phys_idx
            return uid

    # =========================================================================
    # LIFECYCLE
    # =========================================================================
    @classmethod
    def delete(cls, uid: int):
        if uid not in cls._lookup: return
        op_code, phys_idx = cls._decode_id(uid)
        pool = SectorManager.get_pool(op_code)
        raw_data = pool.get(phys_idx)
        if raw_data is None: return 

        is_dead = pool.release(phys_idx)

        if is_dead:
            with cls._lock:
                if uid in cls._lookup:
                    del cls._lookup[uid]
                    if op_code == OP_BLOB and raw_data[1] in cls._blob_lookup:
                        del cls._blob_lookup[raw_data[1]]

            # Recursión GC v4.8
            if op_code == OP_HAMT:
                # Saltar bitmap
                for i in range(1, len(raw_data)):
                    cls.delete(raw_data[i])
            elif op_code == OP_KV:
                # Borrar Key y Value
                cls.delete(raw_data[0])
                cls.delete(raw_data[1])
            elif op_code == OP_SYMBOL:
                # Borrar Blob del nombre
                cls.delete(raw_data[0])
            elif op_code not in (OP_SCALAR, OP_BLOB, OP_CHUNK):
                for child_uid in raw_data:
                    cls.delete(child_uid)

    @classmethod
    def retain(cls, uid: int):
        cls._retain_node(uid)

    @classmethod
    def _retain_node(cls, uid: int):
        if uid not in cls._lookup: return 
        op_code = cls.get_op(uid) 
        phys_idx = cls._lookup[uid]
        pool = SectorManager.get_pool(op_code)
        pool.retain(phys_idx)

    # =========================================================================
    # INTROSPECCIÓN
    # =========================================================================
    @staticmethod
    def _extract_meta_fast(uid: int) -> Tuple[int, int]:
        return ((uid >> SHIFT_DEPTH) & MASK_64, (uid >> SHIFT_MASS) & MASK_64)

    @staticmethod
    def get_op(uid: int) -> int: return (uid >> SHIFT_OP) & MASK_OP
    @staticmethod
    def get_mass(uid: int) -> int: return (uid >> SHIFT_MASS) & MASK_64
    @staticmethod
    def get_depth(uid: int) -> int: return (uid >> SHIFT_DEPTH) & MASK_64
    @staticmethod
    def get_qec(uid: int) -> int: return (uid >> 192) & MASK_64

    @classmethod
    def get_args(cls, uid: int) -> Tuple[int, ...]:
        if uid not in cls._lookup:
            raise ValueError(f"CRITICAL: Acceso a nodo muerto o inexistente UID={hex(uid)}")
        phys_idx = cls._lookup[uid]
        op_code = cls.get_op(uid)
        pool = SectorManager.get_pool(op_code)
        data = pool.get(phys_idx)
        if op_code == OP_BLOB: return data[1] 
        return data

    @classmethod
    def debug_lookup_size(cls): return len(cls._lookup)
    
    @classmethod
    def _decode_id(cls, uid: int) -> Tuple[int, int]:
        op_code = (uid >> SHIFT_OP) & MASK_OP
        if uid not in cls._lookup:
            raise ValueError(f"CRITICAL: Intento de decodificar UID muerto: {hex(uid)}")
        phys_idx = cls._lookup[uid]
        return op_code, phys_idx