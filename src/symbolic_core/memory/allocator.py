"""
src/symbolic_core/memory/allocator.py
Arena Allocator v4.1 (Batch-Safe).
Gestión de memoria física optimizada para inserciones masivas y Thread-Safety robusto.
"""
import threading
from typing import List, Tuple, Deque, Optional, Dict, Iterable, Any
from collections import deque

class MemoryPool:
    """
    Gestor de memoria física LIFO (Hot Cache).
    Optimizado para High-Throughput.
    """
    __slots__ = (
        '_data', '_ref_counts', '_free_list', '_lock', 
        '_capacity', '_name', '_active_count', '_page_size'
    )

    def __init__(self, name: str = "Unknown", page_size: int = 4096):
        self._name = name
        self._page_size = page_size
        
        # [MEJORA 1] RLock (Re-entrant Lock)
        # Permite que el mismo hilo adquiera el candado varias veces sin bloquearse.
        # Vital para operaciones recursivas de limpieza.
        self._lock = threading.RLock()
        
        # Estructuras Físicas
        self._data: List[Optional[Tuple[int, ...]]] = [None] * page_size
        # Array de enteros nativos (mucho más rápido que objetos para el conteo)
        self._ref_counts: List[int] = [0] * page_size
        
        # Cola de reciclaje (LIFO para caché caliente)
        self._free_list: Deque[int] = deque(range(page_size))
        
        self._capacity = page_size
        self._active_count = 0

    def alloc(self, args: Tuple[int, ...]) -> int:
        """Asignación unitaria O(1)."""
        with self._lock:
            if not self._free_list:
                self._expand_memory(1)
            
            idx = self._free_list.pop()
            self._data[idx] = args
            self._ref_counts[idx] = 1 # Ownership inicial
            self._active_count += 1
            return idx

    def alloc_batch(self, batch_args: List[Tuple[int, ...]]) -> List[int]:
        """
        [NUEVO v4.1] Asignación en Lote.
        Garantiza espacio suficiente ANTES de asignar para evitar IndexError.
        Reduce la contención del Lock drásticamente (1 lock vs N locks).
        """
        count = len(batch_args)
        indices = []
        
        with self._lock:
            # 1. Chequeo de Capacidad Crítica
            # Calculamos si tenemos suficientes slots libres.
            free_slots = len(self._free_list)
            
            if free_slots < count:
                # Calculamos el déficit exacto
                needed = count - free_slots
                # Expandimos (al menos lo necesario + margen de seguridad)
                self._expand_memory(needed)
            
            # 2. Asignación Rápida
            # Como ya hemos garantizado el espacio arriba, este bucle es seguro.
            for args in batch_args:
                try:
                    idx = self._free_list.pop()
                    self._data[idx] = args
                    self._ref_counts[idx] = 1
                    indices.append(idx)
                except IndexError:
                    # Defensive Coding: Esto protege contra corrupción de memoria teórica
                    raise RuntimeError(f"CRITICAL: Allocator '{self._name}' corrupto. Falló expansión batch.")
            
            self._active_count += count
            
        return indices

    def retain(self, idx: int):
        """Keep Alive."""
        with self._lock:
            # Check ligero de límites
            if idx < self._capacity:
                self._ref_counts[idx] += 1

    def release(self, idx: int) -> bool:
        """
        Decrementa ref. Retorna True si el objeto murió.
        """
        is_dead = False
        with self._lock:
            if idx < self._capacity and self._ref_counts[idx] > 0:
                self._ref_counts[idx] -= 1
                if self._ref_counts[idx] == 0:
                    is_dead = True
                    self._data[idx] = None # Ayuda al GC de Python
                    self._free_list.append(idx)
                    self._active_count -= 1
        return is_dead

    def release_batch(self, indices: Iterable[int]) -> List[int]:
        """
        [NUEVO] Decrementa referencias en lote.
        Retorna la lista de índices que murieron para que el Universo limpie sus entradas.
        """
        dead_indices = []
        with self._lock:
            for idx in indices:
                if idx < self._capacity and self._ref_counts[idx] > 0:
                    self._ref_counts[idx] -= 1
                    if self._ref_counts[idx] == 0:
                        self._data[idx] = None
                        self._free_list.append(idx)
                        self._active_count -= 1
                        dead_indices.append(idx)
        return dead_indices

    def get(self, idx: int) -> Optional[Tuple[int, ...]]:
        """Lectura sin bloqueo (Optimistic Read)."""
        try:
            return self._data[idx]
        except IndexError:
            return None 

    def _expand_memory(self, min_required: int = 1):
        """
        [MEJORA CRÍTICA] Estrategia de Crecimiento Elástica.
        Asegura que siempre haya espacio para 'min_required' items adicionales.
        """
        # 1. Estrategia Base: Duplicar capacidad o añadir una página (lo que sea mayor)
        growth = max(self._capacity, self._page_size)
        
        # 2. Corrección de Emergencia:
        # Si el lote que intentamos meter es GIGANTE (mayor que la duplicación estándar),
        # forzamos un crecimiento que cubra la demanda + una página de buffer.
        if min_required > growth:
            growth = min_required + self._page_size

        # print(f"[ALLOC] Arena '{self._name}': Expanding +{growth} slots (Capacity: {self._capacity} -> {self._capacity + growth})")
        
        # 3. Expansión Física
        self._data.extend([None] * growth)
        self._ref_counts.extend([0] * growth)
        
        # 4. Actualización de Free List
        # Añadimos el rango de nuevos índices disponibles al final de la cola
        new_indices = range(self._capacity, self._capacity + growth)
        self._free_list.extend(new_indices)
        
        self._capacity += growth

    def stats(self) -> Dict[str, Any]:
        """Introspección para monitoreo de salud."""
        with self._lock:
            return {
                "name": self._name,
                "capacity": self._capacity,
                "active": self._active_count,
                "free": len(self._free_list),
                "fragmentation": 1.0 - (self._active_count / (self._capacity or 1))
            }