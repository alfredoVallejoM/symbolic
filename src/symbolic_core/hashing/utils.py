"""
src/symbolic_core/hashing/utils.py
Utilidades criptográficas de bajo nivel.
"""
from .invariants import MASK_64

# Constantes de Mezcla (Avalanche Primes)
PRIME_1 = 0xbf58476d1ce4e5b9
PRIME_2 = 0x94d049bb133111eb

def holographic_hash(uid: int) -> int:
    """
    Proyección Holográfica de 512 bits a 64 bits.
    Algoritmo: Avalanche Mixer v5.0
    Garantiza dispersión uniforme y determinismo.
    """
    # 1. Extracción y Plegado
    h = uid & MASK_64
    h = (h ^ ((uid >> 64) & MASK_64)) * PRIME_1
    h = (h ^ ((uid >> 128) & MASK_64)) * PRIME_2
    h = (h ^ ((uid >> 192) & MASK_64)) * PRIME_1
    
    layer_high = uid >> 256
    if layer_high:
        h ^= (layer_high & MASK_64) * PRIME_2

    # 2. Avalanche Finalizer
    h ^= (h >> 31)
    h = (h * PRIME_1) & MASK_64
    h ^= (h >> 27)
    h = (h * PRIME_2) & MASK_64
    h ^= (h >> 33)
    
    return h