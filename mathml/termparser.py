#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Implementation of an infix term parser.

Generates an AST that can be converted to SAX events using the
mathml.xmlterm module or to literal terms using the mathml.termbuilder
module.

Usage examples:
(remember to run 'from mathml import termparser, termbuilder' first!)

* arithmetic terms:

>>> from termparser import parse_term, parse_bool_expression
>>> from termbuilder import tree_converters
>>> term = '.1*pi+2*(1+3i)-5.6-6*-1/sin(-45*a.b) + 1'
>>> parsed_ast = parse_term(term)
>>> parsed_ast
('+', ('*', (u'const:real', Decimal("0.1")), (u'name', u'pi')), ('-', ('*', (u'const:integer', 2), (u'const:complex', Complex(1+3j))), (u'const:real', Decimal("5.6")), ('*', (u'const:integer', 6), ('/', (u'const:integer', -1), (u'sin', ('*', (u'const:integer', -45), (u'name', u'a.b')))))), (u'const:integer', 1))
>>> converter = tree_converters['infix']
>>> converter.build(parsed_ast)
u'0.1 * pi + 2 * (1+3i) - 5.6 - 6 * -1 / sin ( -45 * a.b ) + 1'


* boolean terms:

>>> bool_term = '%(term)s = 1 or %(term)s > 5 and true' % {'term':term}
>>> parsed_ast = parse_bool_expression(bool_term)
>>> parsed_ast
(u'or', ('=', ('+', ('*', (u'const:real', Decimal("0.1")), (u'name', u'pi')), ('-', ('*', (u'const:integer', 2), (u'const:complex', Complex(1+3j))), (u'const:real', Decimal("5.6")), ('*', (u'const:integer', 6), ('/', (u'const:integer', -1), (u'sin', ('*', (u'const:integer', -45), (u'name', u'a.b')))))), (u'const:integer', 1)), (u'const:integer', 1)), (u'and', ('>', ('+', ('*', (u'const:real', Decimal("0.1")), (u'name', u'pi')), ('-', ('*', (u'const:integer', 2), (u'const:complex', Complex(1+3j))), (u'const:real', Decimal("5.6")), ('*', (u'const:integer', 6), ('/', (u'const:integer', -1), (u'sin', ('*', (u'const:integer', -45), (u'name', u'a.b')))))), (u'const:integer', 1)), (u'const:integer', 5)), (u'const:bool', True)))
>>> converter = tree_converters['postfix']
>>> converter.build(parsed_ast)
u'0.1 pi * 2 (1+3i) * 5.6 6 -1 -45 a.b * sin / * - - 1 + + 1 = 0.1 pi * 2 (1+3i) * 5.6 6 -1 -45 a.b * sin / * - - 1 + + 5 > true and or'
"""

__all__ = (
    'parse_bool_expression', 'parse_term',
    'ParseException'   # from pyparsing
    )

try:
    from psyco.classes import *
except ImportError:
    pass

from itertools import *
from pyparsing import *


from datatypes import Decimal, Complex, Rational, ENotation


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
        return [ (u'const:bool',    t[0].lower() == 'true') ]
    def __parse_string(s,p,t):
        return [ (u'const:string',  t[0][1:-1]) ]
    def __parse_enotation(s,p,t):
        return [ (u'const:enotation', ENotation(t[0], t[1])) ]
    def __parse_complex(s,p,t):
        if len(t) == 1:
            value = Complex(0, Decimal(t[0]))
        else:
            value = Complex(Decimal(t[0]), Decimal(t[1]))
        return [ (u'const:complex', value) ]

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

    _p_int = Combine( Optional(p_sign) + Word(nums) )
    _p_int.leaveWhitespace()

    _p_float_woE  = Literal('.') + Word(nums)
    _p_float_woE |= Word(nums) + Literal('.') + Optional(Word(nums))
    _p_float = Combine( Optional(p_sign) + _p_float_woE )
    _p_float.leaveWhitespace()

    p_enotation = (Combine(Optional(p_sign) + _p_float_woE) | _p_int) + Suppress(Literal('E')) + _p_int
    p_enotation.leaveWhitespace()
    p_enotation.setName('e-notation')
    p_enotation.setParseAction(__parse_enotation)

    p_complex = Optional((_p_float|_p_int) + FollowedBy(oneOf('+ -'))) + (_p_float|_p_int) + Suppress(oneOf('i j'))
    p_complex.leaveWhitespace()
    p_complex.setParseAction(__parse_complex)

    p_int = _p_int + Empty()
    p_int.setName('int')
    p_int.setParseAction(__parse_int)

    p_float = _p_float + Empty()
    p_float.setName('float')
    p_float.setParseAction(__parse_float)


    p_num = p_complex | p_enotation | p_float | p_int
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

    # int list = (3,6,43,554)
    _p_int_or_name = p_int | p_attribute
    p_int_list = delimitedList(_p_int_or_name)
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


class InfixTermParser(object):
    "Defines arithmetic terms."

    interval_closure = {
        ('[', ']') : u'closed',
        ('[', ')') : u'closed-open',
        ('(', ']') : u'open-closed',
        ('(', ')') : u'open'
        }

    operator_order = '^ % / * - +'

    def __parse_list(s,p,t):
        return [ (u'list',)  + tuple(t) ]
    def __parse_interval(s,p,t):
        return [ (u'interval:%s' % InfixTermParser.interval_closure[(t[0], t[-1])],) + tuple(t[1:-1]) ]
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
        # ZeroOrMore->Optional could speed this up
        if __operator == '-':
            _neg_exp = _p_op + _p_exp
            _neg_exp.setParseAction(_build_expression_tree)
            _p_exp = (_p_exp ^ _neg_exp) + ZeroOrMore( _p_op + _p_exp )
        else:
            _p_exp = _p_exp + ZeroOrMore( _p_op + _p_exp )
        _p_exp.setParseAction(_build_expression_tree)

    p_arithmetic_exp = _p_exp

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
    _p_num_atom <<= p_case | ( Suppress('(') + p_arithmetic_exp + Suppress(')') ) | BaseParser.p_num | p_function | BaseParser.p_attribute

    p_arithmetic_interval = oneOf('( [') + p_arithmetic_exp + Suppress(',') + p_arithmetic_exp + oneOf(') ]')
    p_arithmetic_interval.setParseAction(__parse_interval)

    p_arithmetic_list = delimitedList(p_arithmetic_exp)
    p_arithmetic_list.setParseAction(__parse_list)

    p_arithmetic_tuple = Suppress('(') + p_arithmetic_list + Suppress(')')


class InfixBoolExpressionParser(object):
    "Defines p_exp for comparisons and p_bool_exp for boolean expressions."

    cmp_operators = '= != <> > < <= >='

    # exp = a op b
    p_cmp_operator  = oneOf(cmp_operators)
    p_cmp_operator.setName('cmp_op')

    p_cmp_in = CaselessLiteral(u'in') | CaselessLiteral(u'notin')

    p_bool_operator = oneOf( u'= <>')
    p_bool_operator.setName('bool_op')
    p_bool_and = CaselessLiteral(u'and')
    p_bool_or  = CaselessLiteral(u'or')
    p_bool_not = CaselessLiteral(u'not')

    p_bool_cmp  = BaseParser.p_bool + OneOrMore( p_bool_operator + BaseParser.p_attribute )
    p_bool_cmp |= (BaseParser.p_bool | BaseParser.p_attribute) + Optional( p_bool_operator + BaseParser.p_bool )

    p_str_cmp   = BaseParser.p_attribute + OneOrMore( p_cmp_operator + BaseParser.p_string )
    p_str_cmp  |= BaseParser.p_string    + OneOrMore( p_cmp_operator + BaseParser.p_attribute )

    p_list_cmp = InfixTermParser.p_arithmetic_exp + p_cmp_in + InfixTermParser.p_arithmetic_interval # p_arithmetic_tuple

    p_factor_cmp = InfixTermParser.p_arithmetic_exp + Literal('|') + InfixTermParser.p_arithmetic_exp
    p_cmp_exp = InfixTermParser.p_arithmetic_exp + p_cmp_operator + InfixTermParser.p_arithmetic_exp

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

    # repair CASE statement in InfixTermParser
    InfixTermParser._p_bool_expression <<= p_bool_exp


# optimize parser
CompleteBoolExpression = InfixBoolExpressionParser.p_bool_exp + StringEnd()
CompleteTerm           = InfixTermParser.p_arithmetic_exp     + StringEnd()
CompleteTermList       = InfixTermParser.p_arithmetic_list    + StringEnd()

CompleteBoolExpression.streamline()
CompleteTerm.streamline()
CompleteTermList.streamline()


# main module functions:

def parse_bool_expression(expression):
    if not isinstance(expression, unicode):
        expression = unicode(expression, 'ascii')
    return CompleteBoolExpression.parseString(expression)[0]

def parse_term(term):
    if not isinstance(term, unicode):
        term = unicode(term, 'ascii')
    return CompleteTerm.parseString(term)[0]

def parse_term_list(term):
    if not isinstance(term, unicode):
        term = unicode(term, 'ascii')
    return CompleteTermList.parseString(term)[0]


try:
    import sys
    from optimize import bind_all
    bind_all(sys.modules[__name__])
    bind_all(pyparsing)
    del sys, bind_all
except:
    pass


if __name__ == '__main__':
    import doctest
    doctest.testmod()
