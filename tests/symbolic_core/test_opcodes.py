"""
tests/unit/test_opcodes.py
Verificación Unitaria de la Ontología y Leyes de Simetría.
Combina auditoría de bits (Legacy) con física algebraica (Holonic).
"""
import unittest
import symbolic_core.opcodes as op
from symbolic_core.opcodes import OpTraits, get_traits

class TestOpcodes(unittest.TestCase):

    # =========================================================================
    # 1. AUDITORÍA DE INTEGRIDAD DE BITS (Tus Tests Originales Adaptados)
    # =========================================================================

    def test_uniqueness_of_opcodes(self):
        """
        CRÍTICO: Verifica que no haya dos constantes OP_ con el mismo valor entero.
        Un error aquí corrompería todo el grafo silenciosamente.
        """
        # 1. Introspección: Obtener todos los atributos que empiezan por OP_
        # Filtramos para asegurarnos de que sean enteros (evitar clases o funciones)
        op_attrs = [attr for attr in dir(op) 
                   if attr.startswith("OP_") and isinstance(getattr(op, attr), int)]
        
        values = [getattr(op, attr) for attr in op_attrs]
        
        # 2. Verificar duplicados
        unique_values = set(values)
        
        if len(values) != len(unique_values):
            # Encontrar el culpable para el mensaje de error
            seen = set()
            duplicates = set()
            for x in values:
                if x in seen: duplicates.add(x)
                seen.add(x)
            self.fail(f"FATAL: Se encontraron OPCODES duplicados con valores: {duplicates}")

    def test_bit_masks_integrity(self):
        """
        Verifica que las máscaras de bits cubran 64 bits sin solaparse incorrectamente.
        """
        # 1. TAG (Bit 63) + OPCODE (56-62) + PAYLOAD (0-55)
        
        # Verificar que OPCODE y PAYLOAD no se tocan
        self.assertEqual(op.MASK_OPCODE & op.MASK_PAYLOAD, 0, 
                         "Error de Diseño: MASK_OPCODE y MASK_PAYLOAD se solapan.")
        
        # Verificar que TAG y OPCODE no se tocan
        self.assertEqual(op.MASK_TAG & op.MASK_OPCODE, 0,
                         "Error de Diseño: MASK_TAG y MASK_OPCODE se solapan.")
                         
        # Verificar Cobertura Total (Opcional, asumiendo signed int)
        # La suma de las máscaras debe cubrir la parte baja de 64 bits
        total_mask = op.MASK_TAG | op.MASK_OPCODE | op.MASK_PAYLOAD
        # 0xFFFFFFFFFFFFFFFF en Python es -1, comparamos bits con máscara
        self.assertEqual(total_mask & 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF,
                         "Error de Diseño: Las máscaras dejan huecos en el entero de 64 bits.")

    def test_pointer_tagging_simulation(self):
        """
        Simula la creación y extracción de un ID para asegurar que la
        aritmética de bits funciona como se espera.
        """
        # Escenario: Crear un nodo tipo OP_ADD en el índice 42
        my_op = op.OP_ADD
        my_index = 42
        
        # Construcción manual (Encoding)
        # ID = (0 << 63) | (OP_ADD << 56) | index
        tagged_id = (my_op << op.SHIFT_OPCODE) | my_index
        
        # Decodificación (Extraction)
        extracted_op = (tagged_id & op.MASK_OPCODE) >> op.SHIFT_OPCODE
        extracted_idx = tagged_id & op.MASK_PAYLOAD
        
        self.assertEqual(extracted_op, my_op, "Fallo al decodificar el OPCODE del puntero.")
        self.assertEqual(extracted_idx, my_index, "Fallo al decodificar el ÍNDICE del puntero.")

    def test_payload_limits(self):
        """
        Asegura que no intentamos meter un índice más grande de lo que permiten los 56 bits.
        """
        max_safe_index = (1 << 56) - 1
        
        # Caso bueno
        id_good = (op.OP_SCALAR << op.SHIFT_OPCODE) | max_safe_index
        self.assertEqual(id_good & op.MASK_PAYLOAD, max_safe_index)
        
        # Caso límite: Desbordamiento de Payload
        huge_index = max_safe_index + 1
        id_overflow = (op.OP_SCALAR << op.SHIFT_OPCODE) | huge_index
        
        # Al aplicar la máscara, deberíamos perder el bit de desbordamiento (volviendo a 0)
        self.assertEqual(id_overflow & op.MASK_PAYLOAD, 0)

    # =========================================================================
    # 2. AUDITORÍA DE FÍSICA ALGEBRAICA (Nuevos Tests Holónicos)
    # =========================================================================

    def test_algebraic_traits_assignment(self):
        """
        Verifica que cada partícula tenga las leyes físicas (Traits) correctas.
        Esto es vital para el Hash QEC.
        """
        
        # 1. Suma (Bosón): Debe ser Conmutativa y Asociativa
        traits_add = get_traits(op.OP_ADD)
        self.assertTrue(traits_add & OpTraits.COMMUTATIVE, "OP_ADD debe ser Conmutativo")
        self.assertTrue(traits_add & OpTraits.ASSOCIATIVE, "OP_ADD debe ser Asociativo")
        self.assertTrue(traits_add & OpTraits.IDENTITY_ZERO, "OP_ADD debe tener Identidad 0")

        # 2. Lista (Fermión/Estructura): NO debe ser Conmutativa
        traits_cons = get_traits(op.OP_CONS)
        self.assertFalse(traits_cons & OpTraits.COMMUTATIVE, "OP_CONS NO debe ser Conmutativo")
        self.assertEqual(traits_cons, OpTraits.NONE, "OP_CONS debe ser rígido (NONE)")

        # 3. Tensor: Asociativo pero NO Conmutativo
        traits_tensor = get_traits(op.OP_TENSOR)
        self.assertFalse(traits_tensor & OpTraits.COMMUTATIVE, "OP_TENSOR NO debe ser Conmutativo")
        self.assertTrue(traits_tensor & OpTraits.ASSOCIATIVE, "OP_TENSOR debe ser Asociativo")
        
        # 4. Dual: Involutivo (A** = A)
        traits_dual = get_traits(op.OP_DUAL)
        self.assertTrue(traits_dual & OpTraits.INVOLUTIVE, "OP_DUAL debe ser Involutivo")

    def test_registry_completeness(self):
        """
        Verifica que todos los opcodes definidos tengan una entrada en el registro de Traits
        (aunque sea NONE), para evitar sorpresas.
        """
        op_vars = [attr for attr in dir(op) 
                   if attr.startswith("OP_") and isinstance(getattr(op, attr), int)]
        
        for op_name in op_vars:
            op_val = getattr(op, op_name)
            # get_traits devuelve NONE por defecto, pero queremos asegurar 
            # que al menos la función no explota.
            try:
                t = get_traits(op_val)
                self.assertIsInstance(t, OpTraits)
            except Exception as e:
                self.fail(f"get_traits falló para {op_name}: {e}")

if __name__ == '__main__':
    unittest.main()