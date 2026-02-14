"""
src/symbolic_core/hashing/spectral_basis.py
Tabla Periódica Espectral v1.0.
Define los Vectores Base Ortonormales (Enteros) para el LSH Algebraico.

TEORÍA:
Trabajamos en un Espacio Hiperdimensional de 64 bits.
Cada Operador (OpCode) tiene un Vector Base 'Ortogonal' a los demas.
Ortogonalidad aqui significa Distancia de Hamming ~32 bits (Max Entropy).
"""

from ..opcodes import *

# =============================================================================
# CONSTANTES DE BASE (HDC BASIS VECTORS)
# =============================================================================
# Generados para maximizar la distancia de Hamming entre ellos.
# Representan los ejes del espacio semántico.
# =============================================================================

# Elemento Neutro (Vacío)
BASIS_ZERO   = 0x0000000000000000

# Vectores Primitivos (Materia)
BASIS_SCALAR = 0x9e3779b97f4a7c15  # Golden Ratio expansion
BASIS_SYMBOL = 0xbf58476d1ce4e5b9  # Prime Splitter

# Vectores Algebraicos (Interacción)
# Deben ser muy distintos entre sí para separar Sumas de Productos.
BASIS_ADD    = 0x1a87c1439b6e5f20
BASIS_MUL    = 0x85ebca6b320d4193
BASIS_POW    = 0xc6a4a7935bd1e995

# Vectores Estructurales
BASIS_CONS   = 0x4cf5ad432745937f
BASIS_HAMT   = 0x517cc1b727220a95
BASIS_TENSOR = 0x369dea0f31a53f85

# Tabla de Lookup Rápida (OpCode -> Vector Base)
_BASIS_TABLE = {
    OP_SCALAR: BASIS_SCALAR,
    OP_SYMBOL: BASIS_SYMBOL,
    OP_ADD:    BASIS_ADD,
    OP_MUL:    BASIS_MUL,
    OP_POW:    BASIS_POW,
    OP_EXP:    BASIS_POW, # Exp es similar a Pow semánticamente
    OP_CONS:   BASIS_CONS,
    OP_HAMT:   BASIS_HAMT,
    OP_TENSOR: BASIS_TENSOR,
    OP_DUAL:   0x733c942958019275, # Vector de Inversión
}

# =============================================================================
# MOTOR ESPECTRAL (Spectral Engine)
# =============================================================================

class SpectralEngine:
    """
    Calculadora de Topología Algebraica sin Floats.
    Usa aritmética modular y rotaciones de bits.
    """
    __slots__ = ()

    @staticmethod
    def get_basis(op_code: int) -> int:
        """Retorna el Vector Base del operador. Si no existe, usa un fallback determinista."""
        return _BASIS_TABLE.get(op_code, 0xaaaaaaaaaaaaaaaa ^ op_code)

    @staticmethod
    def rotate_right(val: int, shift: int) -> int:
        """
        Rotación Circular (ROL) de 64 bits.
        Equivalente a multiplicar por una matriz de rotación en el espacio complejo,
        pero en enteros y en 1 ciclo de CPU.
        """
        shift &= 63  # Modulo 64
        return ((val >> shift) | (val << (64 - shift))) & 0xFFFFFFFFFFFFFFFF

    @staticmethod
    def mix_commutative(op_vector: int, children_hashes: list[int]) -> int:
        """
        Mezcla Bosónica (Simétrica).
        Para Suma, Producto, etc. El orden de los hijos NO importa.
        
        Fórmula: V_parent = V_op + (V_child1 + V_child2 + ...)
        Usamos Suma Modular para acumular 'masa'.
        """
        accumulator = op_vector
        for h in children_hashes:
            # Suma modular con wrapping (simula superposición de ondas)
            accumulator = (accumulator + h) & 0xFFFFFFFFFFFFFFFF
            
            # Pequeña rotación dependiente del contenido para evitar cancelaciones triviales
            # (ej: x + (-x) no debería ser 0 absoluto en estructura, solo en valor)
            # Pero para LSH estructural puro, la suma simple es mejor.
        return accumulator

    @staticmethod
    def mix_non_commutative(op_vector: int, children_hashes: list[int]) -> int:
        """
        Mezcla Fermiónica (Posicional).
        Para Potencia, Resta, Listas. El orden SI importa.
        
        Fórmula: V_parent = V_op + R_1(V_child1) + R_2(V_child2) ...
        Cada posición rota el vector del hijo un ángulo diferente.
        """
        accumulator = op_vector
        for i, h in enumerate(children_hashes):
            # Rotamos el hijo 'i' veces 'K' pasos.
            # Esto coloca a cada hijo en una dimensión de fase distinta.
            rotated_child = SpectralEngine.rotate_right(h, (i + 1) * 7)
            
            # Acumulamos
            accumulator = (accumulator + rotated_child) & 0xFFFFFFFFFFFFFFFF
        return accumulator