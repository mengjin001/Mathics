# -*- coding: utf8 -*-

"""
Recurrence relation solvers
"""

import sympy
from mathics.builtin.base import Builtin, BinaryOperator, Test
from mathics.core.expression import Expression, from_sympy
from mathics.core.convert import SympyExpression, sympy_symbol_prefix

class RSolve(Builtin):
    """
    <dl>
    <dt>'RSolve[$eqn$, $a[n]$, $n$]'
        <dd>solves a recurrence equation for the function '$a[n]$'.
    </dl>

    >> RSolve[a[n] == a[n+1], a[n], n]
     = {{a[n] -> C[0]}}

    No boundary conditions gives two general paramaters:
    >> RSolve[{a[n + 2] == a[n]}, a, n]
     = {{a -> (Function[{n}, C[1] -1 ^ n + C[0]])}}

    One boundary condition:
    >> RSolve[{a[n + 2] == a[n], a[0] == 1}, a, n]
     = {{a -> (Function[{n}, 1 - C[1] + C[1] -1 ^ n])}}

    Two boundary conditions:
    >> RSolve[{a[n + 2] == a[n], a[0] == 1, a[1] == 4}, a, n]
     = {{a -> (Function[{n}, 5 / 2 - 3 -1 ^ n / 2])}}
    """

    messages = {
        'deqn': 'Equation or list of equations expected instead of `1` in the first argument `1`.',
        'deqx': 'Supplied equations are not difference equations of the given functions.',
        'dsfun': '`1` cannot be used as a function.',
        'dsvar': '`1` cannot be used as a variable.',
    }

    def apply(self, eqns, a, n, evaluation):
        'RSolve[eqns_, a_, n_]'

        #TODO: Do this with rules?
        if not eqns.has_form('List', None):
            eqns = Expression('List', eqns)

        if len(eqns.leaves) == 0:
            return

        for eqn in eqns.leaves:
            if eqn.get_head_name() != 'Equal':
                evaluation.message('RSolve', 'deqn', eqn)
                return

        if (n.is_atom() and not n.is_symbol()) or \
          n.get_head_name() in ('Plus', 'Times', 'Power') or \
          'Constant' in n.get_attributes(evaluation.definitions):
            evaluation.message('RSolve', 'dsvar')
            return

        try:
            a.leaves
            function_form = None
            func = a
        except AttributeError:
            func = Expression(a, n)
            function_form = Expression('List', n)

        if func.is_atom() or len(func.leaves) != 1:
            evaluation.message('RSolve', 'dsfun', a)

        if n not in func.leaves:
            evaluation.message('DSolve', 'deqx')

        # Seperate relations from conditions
        conditions = {}
        def is_relation(eqn):
            left, right = eqn.leaves
            for l,r in [(left, right), (right, left)]:
                if left.get_head_name() == func.get_head_name() and len(left.leaves) == 1 \
                  and isinstance(l.leaves[0].to_python(), int) and r.is_numeric():
                    conditions[l.leaves[0].to_python()] = r.to_sympy()
                    return False
            return True
        relation = filter(is_relation, eqns.leaves)[0]

        left, right = relation.leaves
        relation = Expression('Plus', left, Expression('Times', -1, right)).evaluate(evaluation)

        sym_eq = relation.to_sympy(converted_functions = set([func.get_head_name()]))
        sym_n = sympy.symbols(str(sympy_symbol_prefix + n.name))
        sym_func = sympy.Function(str(sympy_symbol_prefix + func.get_head_name())) (sym_n)

        sym_conds = {}
        for cond in conditions:
            sym_conds[sympy.Function(str(sympy_symbol_prefix + func.get_head_name()))(cond)] = conditions[cond]

        try:
            # Sympy raises error when given empty conditions. Fixed in upcomming sympy release.
            if sym_conds != {}:
                sym_result = sympy.rsolve(sym_eq, sym_func, sym_conds)
            else:
                sym_result = sympy.rsolve(sym_eq, sym_func)

            if not isinstance(sym_result, list):
                sym_result = [sym_result]
        except ValueError as ve:
            return

        if function_form is None:
            return Expression('List', *[Expression('List',
                Expression('Rule', a, from_sympy(soln))) for soln in sym_result])
        else:
            return Expression('List', *[Expression('List', Expression('Rule', a,
                Expression('Function', function_form, from_sympy(soln)))) for soln in sym_result])
