"""
src/symbolic_core/kernel/strategies.py
Motor de Estrategias v3.5 (Critical Fix).
Corrección de Flujo: Evita el descarte silencioso del Agrupamiento Algebraico.
"""
from typing import Tuple, List, Protocol, Union, Optional, Dict
from ..opcodes import *

class UniverseAccessor(Protocol):
    def get_op(self, uid: int) -> int: ...
    def get_args(self, uid: int) -> Tuple[int, ...]: ...
    def intern_val(self, value: Union[int, float]) -> int: ... 
    def intern(self, op_code: int, args: Tuple[int, ...]) -> int: ...

class NormalizationStrategy:

    @staticmethod
    def normalize(
        op_code: int, 
        args: Tuple[int, ...], 
        accessor: UniverseAccessor
    ) -> Tuple[int, Tuple[int, ...]]:
        
        # 1. INTROSPECCIÓN FÍSICA
        traits = get_traits(op_code)
        
        # 2. APLANAMIENTO
        if traits & OpTraits.ASSOCIATIVE:
            args = NormalizationStrategy._flatten(op_code, args, accessor)

        # 3. ÁLGEBRA ARITMÉTICA (ADD, MUL)
        if (traits & OpTraits.COMMUTATIVE) and op_code in (OP_ADD, OP_MUL):
            # A. Constant Folding
            res_op, res_args = NormalizationStrategy._fold_scalars(op_code, args, accessor)
            if res_op is not None: 
                # Hubo un cambio estructural mayor (ej: aniquilación a 0)
                return res_op, res_args
            
            # B. Grouping (Algebraic Collection)
            if len(res_args) >= 2:
                final_op, final_args = NormalizationStrategy._group_terms(op_code, res_args, accessor)
                
                if final_op is not None: 
                    return final_op, final_args
                
                # CORRECCIÓN CRÍTICA v3.5:
                # Si final_op es None, significa que el operador raíz se mantiene (sigue siendo ADD/MUL),
                # PERO los argumentos pueden haber cambiado (x+x -> 2x). 
                # Debemos actualizar res_args con final_args.
                res_args = final_args

            args = res_args

        # 4. TEORÍA DE CATEGORÍAS (DUAL & TENSOR)
        if op_code == OP_DUAL and len(args) == 1:
            child_id = args[0]
            if accessor.get_op(child_id) == OP_DUAL:
                gc_args = accessor.get_args(child_id)
                if gc_args:
                    return accessor.get_op(gc_args[0]), accessor.get_args(gc_args[0])
            
            if accessor.get_op(child_id) == OP_TENSOR:
                return NormalizationStrategy._distribute_dual_over_tensor(child_id, accessor)

        # 5. IDEMPOTENCIA
        if traits & OpTraits.IDEMPOTENT:
            args = tuple(sorted(set(args)))

        # 6. DEGENERACIÓN UNITARIA
        if (traits & OpTraits.ASSOCIATIVE) and len(args) == 1:
            child_id = args[0]
            return accessor.get_op(child_id), accessor.get_args(child_id)

        # =========================================================================
        # REGLAS DE CÁLCULO
        # =========================================================================
        
        if op_code == OP_POW and len(args) == 2:
            res = NormalizationStrategy._reduce_pow(args[0], args[1], accessor)
            if res: return res

        if op_code == OP_EXP and len(args) == 1:
            res = NormalizationStrategy._reduce_exp(args[0], accessor)
            if res: return res

        return op_code, args

    # =========================================================================
    # MOTORES DE REDUCCIÓN
    # =========================================================================

    @staticmethod
    def _flatten(op_code: int, args: Tuple[int, ...], accessor: UniverseAccessor) -> Tuple[int, ...]:
        dirty = False
        for arg in args:
            if accessor.get_op(arg) == op_code:
                dirty = True
                break
        if not dirty: return args

        new_args = []
        for arg_uid in args:
            if accessor.get_op(arg_uid) == op_code:
                new_args.extend(accessor.get_args(arg_uid))
            else:
                new_args.append(arg_uid)
        return tuple(new_args)

    @staticmethod
    def _fold_scalars(op_code: int, args: Tuple[int, ...], accessor: UniverseAccessor) -> Tuple[Optional[int], Tuple[int, ...]]:
        scalars = []
        symbolic = []
        neutral = 0 if op_code == OP_ADD else 1
        absorber = 0 if op_code == OP_MUL else None

        for uid in args:
            op = accessor.get_op(uid)
            if op == OP_SCALAR:
                val = accessor.get_args(uid)[0]
                if val == absorber: 
                    zero = accessor.intern_val(0)
                    return accessor.get_op(zero), accessor.get_args(zero)
                scalars.append(val)
            else:
                symbolic.append(uid)
        
        if not scalars: return None, args

        accum = neutral
        for s in scalars:
            if op_code == OP_ADD: accum += s
            elif op_code == OP_MUL: accum *= s
        
        if accum == neutral:
            if not symbolic:
                res = accessor.intern_val(neutral)
                return accessor.get_op(res), accessor.get_args(res)
            return None, tuple(symbolic)
        
        accum_id = accessor.intern_val(accum)
        return None, (accum_id,) + tuple(symbolic)

    @staticmethod
    def _group_terms(op_code: int, args: Tuple[int, ...], accessor: UniverseAccessor) -> Tuple[Optional[int], Tuple[int, ...]]:
        """
        Agrupa términos algebraicos idénticos.
        OPTIMIZACIÓN v3.7: Eliminada la preservación de orden redundante.
        Como ADD/MUL son conmutativos, el Canonizer ordenará el resultado después.
        Esto ahorra O(N) de memoria y tiempo en listas auxiliares.
        """
        # 1. Construcción Rápida del Histograma
        # Usamos dict.get para velocidad en CPython
        counts: Dict[int, int] = {}
        for uid in args:
            counts[uid] = counts.get(uid, 0) + 1
            
        # 2. Short-Circuit: Si no hay duplicados, salir inmediatamente.
        # len(counts) == len(args) implica que todos son únicos.
        if len(counts) == len(args): 
            return None, args
        
        # 3. Reconstrucción con Agrupamiento
        new_terms = []
        # Iteramos sobre el dict directamente. El orden será arbitrario (depende de inserción/hash),
        # PERO no importa porque el Universe.intern llamará a Canonizer.sort_args justo después.
        for uid, count in counts.items():
            if count == 1:
                new_terms.append(uid)
            else:
                # Creación del nodo coeficiente/exponente
                count_node = accessor.intern_val(count)
                
                if op_code == OP_ADD:
                    # x + x -> 2*x
                    term = accessor.intern(OP_MUL, (count_node, uid))
                    new_terms.append(term)
                elif op_code == OP_MUL:
                    # x * x -> x^2
                    term = accessor.intern(OP_POW, (uid, count_node))
                    new_terms.append(term)
        
        return None, tuple(new_terms)

    @staticmethod
    def _distribute_dual_over_tensor(tensor_id: int, accessor: UniverseAccessor) -> Tuple[int, Tuple[int, ...]]:
        tensor_components = accessor.get_args(tensor_id)
        new_components = []
        for comp_uid in tensor_components:
            dual_comp = accessor.intern(OP_DUAL, (comp_uid,))
            new_components.append(dual_comp)
        return OP_TENSOR, tuple(new_components)

    @staticmethod
    def _reduce_pow(base_id: int, exp_id: int, accessor: UniverseAccessor):
        # 1. Escalar
        exp_op = accessor.get_op(exp_id)
        if exp_op == OP_SCALAR:
            exp_val = accessor.get_args(exp_id)[0]
            if exp_val == 0:
                one = accessor.intern_val(1)
                return accessor.get_op(one), accessor.get_args(one)
            if exp_val == 1:
                return accessor.get_op(base_id), accessor.get_args(base_id)
        
        # 2. Anidada
        base_op = accessor.get_op(base_id)
        if base_op == OP_POW:
            inner_base, inner_exp = accessor.get_args(base_id)
            new_exp = accessor.intern(OP_MUL, (inner_exp, exp_id))
            return OP_POW, (inner_base, new_exp)

        return None

    @staticmethod
    def _reduce_exp(arg_id: int, accessor: UniverseAccessor):
        op = accessor.get_op(arg_id)
        if op == OP_SCALAR and accessor.get_args(arg_id)[0] == 0:
            one = accessor.intern_val(1)
            return accessor.get_op(one), accessor.get_args(one)
        return None