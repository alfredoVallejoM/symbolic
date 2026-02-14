"""
src/symbolic_core/kernel/sectors.py
Definición de la Topología de Memoria v4.0.
Configuración granular de Arenas por Tipo de Operación.
"""
from typing import Dict
from ..opcodes import *
from ..memory.allocator import MemoryPool

# Configuración de rendimiento: Tamaño de página por defecto y específicos
DEFAULT_PAGE_SIZE = 4096
SECTOR_CONFIG = {
    OP_SCALAR: 65536,  # Escalares: Muy numerosos, páginas grandes
    OP_SYMBOL: 16384,  # Símbolos: Numerosos
    OP_ADD:    8192,   # Operaciones comunes
    OP_MUL:    8192,
    OP_HAMT:   1024,   # Estructuras pesadas, crecimiento más conservador
    OP_BLOB:   4096,   # Datos binarios
}

class SectorManager:
    """
    Orquestador de Memoria.
    Mapea OpCodes a Pools optimizados.
    """
    _sectors: Dict[int, MemoryPool] = {}

    @classmethod
    def get_pool(cls, op_code: int) -> MemoryPool:
        if op_code not in cls._sectors:
            # Determinamos el tamaño de página óptimo
            p_size = SECTOR_CONFIG.get(op_code, DEFAULT_PAGE_SIZE)
            pool_name = f"Sector-{hex(op_code)}"
            
            # Inicialización Lazy
            cls._sectors[op_code] = MemoryPool(name=pool_name, page_size=p_size)
            
        return cls._sectors[op_code]

    @classmethod
    def stats(cls):
        """Informe completo del estado de la memoria."""
        return {
            op: pool.stats() 
            for op, pool in cls._sectors.items()
        }

    @classmethod
    def reset(cls):
        """
        UTILIDAD DE TEST: Borra toda la memoria física.
        ¡PELIGRO! Solo usar en setUp/tearDown de tests.
        """
        cls._sectors.clear()

# Pre-calentamiento estratégico (opcional, evita lag en la primera operación)
# SectorManager.get_pool(OP_SCALAR)