#!/usr/bin/python
# -*- coding: utf-8 -*-
__doc__ = """
Implementation of the standard AST output converters.
"""

__all__ = (
    'TermBuilder', 'LiteralTermBuilder',
    'InfixTermBuilder', 'PrefixTermBuilder', 'PostfixTermBuilder',
    'tree_converters'
    )


try:
    from psyco.classes import *
except ImportError:
    pass

from itertools import *

from mathml.termparser import (ConverterRegistry,
                               TERM_OPERATOR_ORDER, BOOL_CMP_OPERATORS)

class TermBuilder(object):
    "Abstract superclass for term builders."
    OPERATOR_ORDER = list(op for ops in (TERM_OPERATOR_ORDER, '| in',
                                         BOOL_CMP_OPERATORS, 'and xor or')
                          for op in ops.split() )
    OPERATOR_SET = frozenset(OPERATOR_ORDER)

    _OPERATOR_MAP = {}

    def __init__(self):
        self.__dispatcher = self._register_handlers({})
        self.__map_operator = self._OPERATOR_MAP.get

    def _register_handlers(self, dispatcher_dict):
        """Subclasses can modify the dictionary returned by this
        method to register additional handlers.
        Note that all handler methods must return iterables!"""
        for name in dir(self):
            if name.startswith('_handle_'):
                method = getattr(self, name)
                if callable(method):
                    dispatcher_dict[ name[8:] ] = method
        return dispatcher_dict

    def build(self, tree):
        "Call this method to build the term representation."
        status = self._init_build_status()
        return ' '.join( self._recursive_build(tree, status) )

    def _init_build_status(self):
        "To be overwritten by subclasses."
        return None

    def _map_operator(self, operator):
        "To be overwritten by subclasses."
        return self.__map_operator(operator, operator)

    def _build_children(self, operator, children, status):
        if operator == 'name' or operator[:6] == 'const:':
            return children
        return [ ' '.join(operand)
                 for operand in imap(self._recursive_build, children, repeat(status)) ]

    def _handle(self, operator, operands, status):
        "Unknown operators (including functions) end up here."
        raise NotImplementedError, "_handle(%s)" % operator

    def _handleOP(self, operator, operands, status):
        "Arithmetic and boolean operators end up here. Default is to call self._handle()"
        return self._handle(operator, operands, status)

    def _recursive_build(self, tree, status):
        dispatcher = self.__dispatcher
        operator = tree[0]
        operands = self._build_children(operator, tree[1:], status)

        dispatch_name = operator.replace(u':', u'_') # const:*, list:*

        dispatch = dispatcher.get(dispatch_name)
        if dispatch:
            return dispatch(operator, operands, status)

        splitpos = operator.find(':')
        if splitpos > 0:
            dispatch = dispatcher.get(operator[:splitpos])
            if dispatch:
                return dispatch(operator, operands, status)

        if operator in self.OPERATOR_SET:
            return self._handleOP(operator, operands, status)
        else:
            return self._handle(operator, operands, status)


class LiteralTermBuilder(TermBuilder):
    "Abstract superclass for literal term builders."
    _INTERVAL_NOTATION = {
        u'closed'      : u'[%s]',
        u'closed-open' : u'[%s)',
        u'open-closed' : u'(%s]',
        u'open'        : u'(%s)'
        }

    _NAME_MAP = {}

    def _handle_name(self, operator, operands, affin):
        name = unicode(str(operands[0]), 'ascii')
        return [ self._NAME_MAP.get(name, name) ]

    def _handle_const_bool(self, operator, operands, status):
        return [ operands[0] and 'true' or 'false' ]

    def _handle_const_complex(self, operator, operands, status):
        value = operands[0]
        return [ u'(%s%s%si)' % (value.real_str, (value.imag >= 0) and '+' or '', value.imag_str) ]

    def _handle_const_rational(self, operator, operands, status):
        value = operands[0]
        return [ u'(%s/%s)' % (value.num_str, value.denom_str) ]

    def _handle_const_enotation(self, operator, operands, status):
        return [ unicode(operands[0]) ]

    def _handle_const(self, operator, operands, status):
        return [ unicode(str(operands[0]).lower(), 'ascii') ]

    def _handle_list(self, operator, operands, status):
        assert operator == u'list'
        return [ u'(%s)' % u','.join(operands) ]

    def _handle_interval(self, operator, operands, status):
        assert operator[:9] == u'interval:'
        return [ self._INTERVAL_NOTATION[ operator[9:] ] % u','.join(operands) ]


class InfixTermBuilder(LiteralTermBuilder):
    "TermBuilder that converts the parse tree into a literal infix term."
    MAX_AFFIN = len(TermBuilder.OPERATOR_ORDER)+1
    __operator_order = TermBuilder.OPERATOR_ORDER.index
    def _init_build_status(self):
        return (self.MAX_AFFIN, self.MAX_AFFIN)

    def _find_affin(self, operator, affin_status):
        try:
            affin = self.__operator_order(operator)
        except ValueError:
            if operator == 'case':
                affin = self.MAX_AFFIN
            else:
                affin = affin_status
        return (affin, affin_status[0])

    def _build_children(self, operator, children, affin_status):
        if operator == '-' and len(children) == 1:
            affin = (0, affin_status[0])
        else:
            affin = self._find_affin(operator, affin_status)
        return super(InfixTermBuilder, self)._build_children(operator, children, affin)

    def _handle_case(self, operator, operands, affin_status):
        assert operator == 'case'
        result = [ 'CASE', 'WHEN', operands[0], 'THEN', operands[1] ]
        if len(operands) > 2:
            result.append('ELSE')
            result.append(operands[2])
        result.append('END')
        return result

    def _handleOP(self, operator, operands, affin_status):
        output_operator = self._map_operator(operator)
        my_affin, parent_affin = self._find_affin(operator, affin_status)
        if my_affin >= parent_affin:
            if len(operands) == 1:
                return ['(', output_operator, operands[0], ')'] # safe bet
            else:
                return chain(chain(*zip(chain('(', repeat(output_operator)), operands)), ')')
        else:
            if len(operands) == 1:
                return [output_operator, operands[0]]
            else:
                return chain((operands[0],), chain(*zip(chain(repeat(output_operator)),
                                                        islice(operands, 1, None))))

    def _handle(self, operator, operands, affin_status):
        return [ self._map_operator(operator), '(', ', '.join(operands), ')' ]

class PostfixTermBuilder(LiteralTermBuilder):
    "TermBuilder that converts the parse tree into a literal postfix term."
    def _handle_case(self, operator, operands, _):
        assert operator == 'case'
        if len(operands) > 2:
            operator = 'CASE_THEN_ELSE'
        else:
            operator = 'CASE_THEN'
        return chain(reversed(operands), (self._map_operator(operator),))

    def _handle(self, operator, operands, _):
        if operator == '-' and len(operands) == 1:
            return [ operands[0], self._map_operator('+-') ]
        else:
            return chain(operands, repeat(self._map_operator(operator), max(1, len(operands)-1)))

class PrefixTermBuilder(LiteralTermBuilder):
    "TermBuilder that converts the parse tree into a literal prefix term."
    def _handle_case(self, operator, operands, _):
        assert operator == 'case'
        if len(operands) > 2:
            operator = 'CASE_THEN_ELSE'
        else:
            operator = 'CASE_THEN'
        return chain((self._map_operator(operator),), reversed(operands))

    def _handle(self, operator, operands, _):
        if operator == '-' and len(operands) == 1:
            return [ operands[0], self._map_operator('+-') ]
        else:
            return chain(repeat(self._map_operator(operator), max(1, len(operands)-1)), operands)


# converter registry:

class TermGeneration(ConverterRegistry):
    "Objects of this class are used to reference the different converters."
    _METHOD_NAME = 'build'
    def convert_tree(self, tree, output_type):
        "Convert a parse tree into a term of the given output type."
        converter = self._converters[output_type]
        return converter.build(tree)


tree_converters = TermGeneration()

tree_converters.register_converter('infix',   InfixTermBuilder())
tree_converters.register_converter('prefix',  PrefixTermBuilder())
tree_converters.register_converter('postfix', PostfixTermBuilder())
