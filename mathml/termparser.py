#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Implementation of an infix term parser. Supports conversion to MathML.
"""

__all__ = (
    'parse_bool_expression', 'parse_term',
    'TermBuilder', 'LiteralTermBuilder',
    'InfixTermBuilder', 'PrefixTermBuilder', 'PostfixTermBuilder',
    'tree_converters',
    'ParseException'   # from pyparsing
    )

try:
    from psyco.classes import *
except ImportError:
    pass

try:
    from decimal import Decimal
except ImportError:
    Decimal = float # Oh, well ...

from itertools import *
from pyparsing import *


def _build_expression_tree(match, pos, tokens):
    #print "B", repr(tokens)
    elem_count = len(tokens)
    if elem_count == 0:
        return []
    elif elem_count == 1:
        return tokens
    elif elem_count == 2:
        return [ tuple(tokens) ]
    else:
        return [ (tokens[1],) + tuple(tokens[::2]) ]

class BaseParser(object):
    """Defines identifiers, attributes and basic data types:
    string, int, float, bool.
    """

    def __parse_attribute(s,p,t):
        return [ (u'name',          t[0]) ]
    def __parse_int(s,p,t):
        return [ (u'const:integer', int(t[0])) ]
    def __parse_float(s,p,t):
        return [ (u'const:real',    Decimal(t[0])) ]
    def __parse_bool(s,p,t):
        return [ (u'const:bool',    unicode(t[0].lower() == 'true').lower()) ]
    def __parse_string(s,p,t):
        return [ (u'const:string',  t[0][1:-1]) ]
    def __parse_complex(s,p,t):
        # t has alread been mangled by __parse_int/float !!
        if len(t) == 1:
            value = complex(0, int(t[0][1]))
        else:
            value = complex(float(t[0][1]), float(t[1][1]))
        return [ (u'const:complex', value) ]

    def __parse_range(s,p,t):
        return [ (u'range',)       + tuple(t) ]
    def __parse_int_list(s,p,t):
        return [ (u'list:int',)    + tuple(t) ]
    def __parse_float_list(s,p,t):
        return [ (u'list:float',)  + tuple(t) ]
    def __parse_string_list(s,p,t):
        return [ (u'list:str',)    + tuple(t) ]
    def __parse_bool_list(s,p,t):
        return [ (u'list:bool',)   + tuple(t) ]

    # atoms: int, float, string
    p_sign = oneOf('+ -')

    p_int = Combine( Optional(p_sign) + Word(nums) )
    p_int.setName('int')
    p_int.setParseAction(__parse_int)

    _p_float_woE  = Literal('.') + Word(nums)
    _p_float_woE |= Optional(p_sign) + Word(nums) + Literal('.') + Optional(Word(nums))
    p_float = Combine( _p_float_woE + Optional(Literal('E') + Optional(p_sign) + Word(nums)) )
    p_float.setName('float')
    p_float.setParseAction(__parse_float)

    p_complex_int   = Optional(p_int   + FollowedBy(oneOf('+ -'))) + p_int   + Suppress('i')
    p_complex_float = Optional(p_float + FollowedBy(oneOf('+ -'))) + p_float + Suppress('i')
    p_complex_int.setParseAction(__parse_complex)
    p_complex_float.setParseAction(__parse_complex)

    p_num = p_complex_int | p_complex_float | p_float | p_int
    #p_num.setName('number')

    p_bool = CaselessLiteral(u'true') | CaselessLiteral(u'false')
    p_bool.setName('bool')
    p_bool.setParseAction(__parse_bool)

    p_string = sglQuotedString | dblQuotedString
    p_string.setName('string')
    p_string.setParseAction(__parse_string)

    # identifier = [a-z][a-z0-9_]*
    p_identifier = Word('abcdefghijklmnopqrstuvwxyz', '_abcdefghijklmnopqrstuvwxyz0123456789')
    p_identifier.setName('identifier')

    p_attribute = Combine(p_identifier + ZeroOrMore( '.' + p_identifier ))
    p_attribute.setName('attribute')
    p_attribute.setParseAction(__parse_attribute)

    # int list = (start:stop:step) | (3,6,43,554)
    _p_int_or_name = p_int | p_attribute
    _p_int_range_def = Literal(':') + _p_int_or_name + Optional(Literal(':') + _p_int_or_name)
    p_int_range = Suppress('(') + Group( _p_int_or_name + Optional(_p_int_range_def) ) + Suppress(')')
    p_int_range.setParseAction(__parse_range)
    p_int_list = delimitedList(Group(_p_int_or_name + Optional(_p_int_range_def)))
    p_int_list.setParseAction(__parse_int_list)

    # typed list = (strings) | (ints) | (floats) | ...
    p_string_list = delimitedList(p_string | p_attribute)
    p_string_list.setParseAction(__parse_string_list)
    p_bool_list   = delimitedList(p_bool | p_attribute)
    p_bool_list.setParseAction(__parse_bool_list)
    p_float_list  = delimitedList(p_float | p_attribute)
    p_float_list.setParseAction(__parse_float_list)

    p_any_list = p_float_list | p_int_list | p_string_list | p_bool_list
    p_typed_tuple = Suppress('(') + p_any_list + Suppress(')')


class ArithmeticParser(object):
    "Defines arithmetic terms."

    operator_order = '^ % / * - +'

    def __parse_list(s,p,t):
        return [ (u'list',)  + tuple(t) ]
    def __parse_function(s,p,t):
        return [ tuple(t) ]
    def __parse_case(s,p,t):
        return [ (u'case',) + tuple(t) ]

    # arithmetic = a+b*c-(3*4)...
    _p_num_atom = Forward()

    _p_exp = _p_num_atom
    # build grammar tree for binary operators in order of precedence
    for __operator in operator_order.split():
        _p_op = Literal(__operator)
        _p_exp = _p_exp + ZeroOrMore( _p_op + _p_exp ) # ZeroOrMore->Optional could speed this up
        _p_exp.setParseAction(_build_expression_tree)

    p_arithmetic_exp = _p_exp

    _p_neg = Literal('-')
    _p_neg_exp = _p_neg + _p_num_atom
    _p_neg_exp.setParseAction(_build_expression_tree)

    # function = identifier(exp,...)
    p_function = BaseParser.p_identifier + Suppress('(') + delimitedList(p_arithmetic_exp) + Suppress(')')
    p_function.setParseAction(__parse_function)

    _p_bool_expression = Forward()
    p_case = (Suppress(CaselessLiteral('CASE') + CaselessLiteral('WHEN')) +
              _p_bool_expression +
              Suppress(CaselessLiteral('THEN')) + _p_exp +
              # Optional => undefined values in expressions!
              #Optional(Suppress(CaselessLiteral('ELSE')) + _p_exp) +
              Suppress(CaselessLiteral('ELSE')) + _p_exp +
              Suppress(CaselessLiteral('END'))
              )
    p_case.setParseAction(__parse_case)

    # numeric values = attribute | number | expression
    _p_num_atom <<= _p_neg_exp | p_case | ( Suppress('(') + p_arithmetic_exp + Suppress(')') ) | BaseParser.p_num | p_function | BaseParser.p_attribute

    _p_arithmethic_range  = Literal(':') + p_arithmetic_exp
    _p_arithmethic_range += Optional(Literal(':') + p_arithmetic_exp)
    p_arithmetic_list = delimitedList(p_arithmetic_exp + Optional(_p_arithmethic_range))
    p_arithmetic_list.setParseAction(__parse_list)

    p_arithmetic_tuple = Suppress('(') + p_arithmetic_list + Suppress(')')


class BoolExpressionParser(object):
    "Defines p_exp for comparisons and p_bool_exp for boolean expressions."

    cmp_operators = '= != <> > < <= >='

    # exp = a op b
    p_cmp_operator  = oneOf(cmp_operators)
    p_cmp_operator.setName('cmp_op')

    p_cmp_in = CaselessLiteral(u'in')

    p_bool_operator = oneOf( u'= <>')
    p_bool_operator.setName('bool_op')
    p_bool_and = CaselessLiteral(u'and')
    p_bool_or  = CaselessLiteral(u'or')
    p_bool_not = CaselessLiteral(u'not')

    p_bool_cmp  = BaseParser.p_bool + OneOrMore( p_bool_operator + BaseParser.p_attribute )
    p_bool_cmp |= (BaseParser.p_bool | BaseParser.p_attribute) + Optional( p_bool_operator + BaseParser.p_bool )

    p_str_cmp   = BaseParser.p_attribute + OneOrMore( p_cmp_operator + BaseParser.p_string )
    p_str_cmp  |= BaseParser.p_string    + OneOrMore( p_cmp_operator + BaseParser.p_attribute )

    p_list_cmp = ArithmeticParser.p_arithmetic_exp + p_cmp_in + ArithmeticParser.p_arithmetic_tuple

    p_factor_cmp = ArithmeticParser.p_arithmetic_exp + Literal('|') + ArithmeticParser.p_arithmetic_exp
    p_cmp_exp = ArithmeticParser.p_arithmetic_exp + p_cmp_operator + ArithmeticParser.p_arithmetic_exp

    p_exp = p_str_cmp | p_list_cmp | p_cmp_exp | p_factor_cmp | p_bool_cmp
    p_exp.setParseAction(_build_expression_tree)

    # bool_exp = a or b and c and (d or e) ...
    _p_atom_exp = Forward()

    _p_bool_and_exp = _p_atom_exp     + ZeroOrMore( p_bool_and + _p_atom_exp )
    _p_bool_and_exp.setParseAction(_build_expression_tree)

    p_bool_exp      = _p_bool_and_exp + ZeroOrMore( p_bool_or  + _p_bool_and_exp )
    p_bool_exp.setParseAction(_build_expression_tree)

    p_not_exp = p_bool_not + _p_atom_exp
    p_not_exp.setParseAction(_build_expression_tree)

    _p_atom_exp <<= p_not_exp | Suppress('(') + p_bool_exp + Suppress(')') | p_exp

    # repair CASE statement in ArithmeticParser
    ArithmeticParser._p_bool_expression <<= p_bool_exp


# optimize parser
CompleteBoolExpression       = BoolExpressionParser.p_bool_exp   + StringEnd()
CompleteArithmeticExpression = ArithmeticParser.p_arithmetic_exp + StringEnd()

CompleteBoolExpression.streamline()
CompleteArithmeticExpression.streamline()


# main module functions:

def parse_bool_expression(expression):
    if not isinstance(expression, unicode):
        expression = unicode(expression, 'ascii')
    return CompleteBoolExpression.parseString(expression)[0]

def parse_term(term):
    if not isinstance(term, unicode):
        term = unicode(term, 'ascii')
    return CompleteArithmeticExpression.parseString(term)[0]



class TermBuilder(object):
    OPERATOR_ORDER = [ op for ops in (ArithmeticParser.operator_order, '| in',
                                      BoolExpressionParser.cmp_operators, 'and xor or')
                       for op in ops.split() ]
    OPERATOR_SET = frozenset(OPERATOR_ORDER)

    def __init__(self):
        self.__dispatcher = self._register_dispatchers({})

    def _register_dispatchers(self, dispatcher_dict):
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
        status = self._init_build_status()
        return ' '.join( self._recursive_build(tree, status) )

    def _init_build_status(self):
        return None

    def _build_children(self, operator, children, status):
        if operator == 'name' or operator[:6] == 'const:':
            return children
        return [ ' '.join(operand)
                 for operand in starmap(self._recursive_build, izip(children, repeat(status))) ]

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

        dispatch_name = operator.replace(':', '_') # const:*, list:*

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
    def _handle_name(self, operator, operands, affin):
        return [ unicode(str(operands[0]), 'ascii') ]

    def _handle_const(self, operator, operands, affin):
        return [ unicode(str(operands[0]), 'ascii') ]

    def _handle_range(self, operator, operands, affin):
        assert operator == 'range'
        return [ u'(%s)' % u':'.join(operands) ]

    def _handle_list(self, operator, operands, affin):
        assert operator == 'list'
        return [ u'(%s)' % u','.join(operands) ]


class InfixTermBuilder(LiteralTermBuilder):
    MAX_AFFIN = len(TermBuilder.OPERATOR_ORDER)+1
    __operator_order = TermBuilder.OPERATOR_ORDER.index
    def _init_build_status(self):
        return (self.MAX_AFFIN, self.MAX_AFFIN)

    def _build_children(self, operator, children, parent_affin):
        try:
            affin = self.__operator_order(operator)
        except ValueError:
            if operator == 'case':
                affin = self.MAX_AFFIN
            else:
                affin = parent_affin
        my_affin = (affin, parent_affin[0])
        return super(InfixTermBuilder, self)._build_children(operator, children, my_affin)

    def _handle_case(self, operator, operands, affin):
        assert operator == 'case'
        result = [ 'CASE', 'WHEN', operands[0], 'THEN', operands[1] ]
        if len(operands) > 2:
            result.append('ELSE')
            result.append(operands[2])
        result.append('END')
        return result

    def _handleOP(self, operator, operands, affin):
        my_affin, parent_affin = affin
        if my_affin > parent_affin:
            return chain(chain(*zip(chain('(', repeat(operator)), operands)), ')')
        else:
            return chain((operands[0],), chain(*zip(chain(repeat(operator)),
                                                    islice(operands,1,None))))

    def _handle(self, operator, operands, affin):
        return [ operator, '(', ','.join(operands), ')' ]

class PostfixTermBuilder(LiteralTermBuilder):
    def _handle_case(self, operator, operands, _):
        assert operator == 'case'
        if len(operands) > 2:
            operator = 'CASE_THEN_ELSE'
        else:
            operator = 'CASE_THEN'
        return chain(reversed(operands), (operator,))

    def _handle(self, operator, operands, _):
        if operator == '-' and len(operands) == 1:
            return [ operands[0], '+-' ]
        else:
            return chain(operands, repeat(operator, max(1, len(operands)-1)))

class PrefixTermBuilder(LiteralTermBuilder):
    def _handle_case(self, operator, operands, _):
        assert operator == 'case'
        if len(operands) > 2:
            operator = 'CASE_THEN_ELSE'
        else:
            operator = 'CASE_THEN'
        return chain((operator,), reversed(operands))

    def _handle(self, operator, operands, _):
        if operator == '-' and len(operands) == 1:
            return [ operands[0], '+-' ]
        else:
            return chain(repeat(operator, max(1, len(operands)-1)), operands)


class OutputConversion(object):
    """This object references the different converters."""
    __CONVERTERS = {}
    def __init__(self):
        pass

    def register_converter(self, output_type, converter):
        "Register a converter for an output type."
        self.__CONVERTERS[output_type] = converter

    def unregister_converter(self, output_type):
        "Remove the registration for an output type."
        del self.__CONVERTERS[output_type]

    def known_types(self):
        "Return the currently registered output types."
        return self.__CONVERTERS.keys()

    def convert_tree(self, tree, output_type):
        "Convert a parse tree into a term of the given output type."
        converter = self.__CONVERTERS[output_type]
        return converter.build(tree)

    def fortype(self, output_type):
        "Return the converter for the given output type."
        return self.__CONVERTERS.get(output_type)

    def __getitem__(self, output_type):
        return self.__CONVERTERS[output_type]


tree_converters = OutputConversion()

tree_converters.register_converter('infix',   InfixTermBuilder())
tree_converters.register_converter('prefix',  PrefixTermBuilder())
tree_converters.register_converter('postfix', PostfixTermBuilder())


try:
    import sys
    from optimize import bind_all
    bind_all(sys.modules[__name__])
    bind_all(pyparsing)
except:
    pass


# Test

if __name__ == '__main__':
    term = ".1*pi+2*(1+3i)-5.6-6*-1/sin(-45*a.b) * CASE WHEN 3|12 THEN 1+3 ELSE e^(4*1) END + 1"
    print term
    print
    print parse_term(term)
    print

    bool_term = "%(term)s = 1 or %(term)s > 5 and true" % {'term':term}
    print bool_term
    print

    parsed = parse_bool_expression(bool_term)
    print "PARSED :",  parsed
    print

    for output_type in ('infix', 'prefix', 'postfix', 'should-fail'):
        try:
            converter = tree_converters[output_type]
            print "%s:" % output_type.upper().ljust(8),  converter.build(parsed)
            print
        except KeyError:
            print "unknown output type: '%s'" % output_type
