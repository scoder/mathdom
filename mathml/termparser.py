#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Implementation of an infix term parser.

Generates an AST that can be converted to SAX events using the
mathml.xmlterm module.

Usage examples:
(remember to run 'from mathml import mathdom, xmlterm, termparser' first!)

* arithmetic terms:

>>> from termparser import parse_term, parse_bool_expression, tree_converters
>>> term = ".1*pi+2*(1+3i)-5.6-6*-1/sin(-45*a.b) + 1"
>>> parsed = parse_term(term)
>>> parsed
('+', ('*', (u'const:real', Decimal("0.1")), (u'name', u'pi')), ('-', ('*', (u'const:integer', 2), (u'const:complex', (Decimal("1"), Decimal("3")))), (u'const:real', Decimal("5.6")), ('*', (u'const:integer', 6), ('/', ('-', (u'const:integer', 1)), (u'sin', ('*', ('-', (u'const:integer', 45)), (u'name', u'a.b')))))), (u'const:integer', 1))
>>> converter = tree_converters['infix']
>>> converter.build(parsed)
u'0.1 * pi + 2 * (1+3i) - 5.6 - 6 * ( - 1 ) / sin ( ( - 45 ) * a.b ) + 1'


* boolean terms:

>>> bool_term = "%(term)s = 1 or %(term)s > 5 and true" % {'term':term}
>>> parsed = parse_bool_expression(bool_term)
>>> parsed
(u'or', ('=', ('+', ('*', (u'const:real', Decimal("0.1")), (u'name', u'pi')), ('-', ('*', (u'const:integer', 2), (u'const:complex', (Decimal("1"), Decimal("3")))), (u'const:real', Decimal("5.6")), ('*', (u'const:integer', 6), ('/', ('-', (u'const:integer', 1)), (u'sin', ('*', ('-', (u'const:integer', 45)), (u'name', u'a.b')))))), (u'const:integer', 1)), (u'const:integer', 1)), (u'and', ('>', ('+', ('*', (u'const:real', Decimal("0.1")), (u'name', u'pi')), ('-', ('*', (u'const:integer', 2), (u'const:complex', (Decimal("1"), Decimal("3")))), (u'const:real', Decimal("5.6")), ('*', (u'const:integer', 6), ('/', ('-', (u'const:integer', 1)), (u'sin', ('*', ('-', (u'const:integer', 45)), (u'name', u'a.b')))))), (u'const:integer', 1)), (u'const:integer', 5)), (u'const:bool', True)))
>>> converter = tree_converters['postfix']
>>> converter.build(parsed)
u'0.1 pi * 2 (1+3i) * 5.6 6 1 +- 45 +- a.b * sin / * - - 1 + + 1 = 0.1 pi * 2 (1+3i) * 5.6 6 1 +- 45 +- a.b * sin / * - - 1 + + 5 > true and or'


* currently broken:

>>> tree_converters["infix"].build( parse_term("-2^2") ) # WORKS
u'( - 2 ) ^ 2'
>>> tree_converters["infix"].build( parse_term("-(2+2)^2") ) # BREAKS PARSER
u'- ( 2 + 2 ) ^ 2'
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

    _p_int = Combine( Optional(p_sign) + Word(nums) )

    _p_float_woE  = Literal('.') + Word(nums)
    _p_float_woE |= Word(nums) + Literal('.') + Optional(Word(nums))
    _p_float = Combine( Optional(p_sign) + _p_float_woE )

    p_enotation = (Combine(Optional(p_sign) + _p_float_woE) | _p_int) + Suppress(Literal('E')) + _p_int
    p_enotation.setName('e-notation')
    p_enotation.setParseAction(__parse_enotation)

    p_complex = Optional((_p_float|_p_int) + FollowedBy(oneOf('+ -'))) + (_p_float|_p_int) + Suppress(oneOf('i j'))
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
    "Abstract superclass for term builders."
    OPERATOR_ORDER = list(op for ops in (ArithmeticParser.operator_order, '| in',
                                         BoolExpressionParser.cmp_operators, 'and xor or')
                          for op in ops.split() )
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
        "Call this method to build the term representation."
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
    "Abstract superclass for literal term builders."
    def _handle_name(self, operator, operands, affin):
        return [ unicode(str(operands[0]), 'ascii') ]

    def _handle_const_boolean(self, operator, operands, affin):
        return [ operands[0] and 'true' or 'false' ]

    def _handle_const_complex(self, operator, operands, affin):
        value = operands[0]
        return [ u'(%s%s%si)' % (value.real_str, (value.imag >= 0) and '+' or '', value.imag_str) ]

    def _handle_const_rational(self, operator, operands, affin):
        value = operands[0]
        return [ u'(%s/%s)' % (value.num_str, value.denom_str) ]

    def _handle_const_enotation(self, operator, operands, affin):
        return [ unicode(operands[0]) ]

    def _handle_const(self, operator, operands, affin):
        return [ unicode(str(operands[0]).lower(), 'ascii') ]

    def _handle_range(self, operator, operands, affin):
        assert operator == 'range'
        return [ u'(%s)' % u':'.join(operands) ]

    def _handle_list(self, operator, operands, affin):
        assert operator == 'list'
        return [ u'(%s)' % u','.join(operands) ]


class InfixTermBuilder(LiteralTermBuilder):
    "Convert the parse tree into a literal infix term."
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
        my_affin, parent_affin = self._find_affin(operator, affin_status)
        if my_affin >= parent_affin:
            if len(operands) == 1:
                return ['(', operator, operands[0], ')'] # safe bet
            else:
                return chain(chain(*zip(chain('(', repeat(operator)), operands)), ')')
        else:
            if len(operands) == 1:
                return [operator, operands[0]]
            else:
                return chain((operands[0],), chain(*zip(chain(repeat(operator)),
                                                        islice(operands,1,None))))

    def _handle(self, operator, operands, affin_status):
        return [ operator, '(', ','.join(operands), ')' ]

class PostfixTermBuilder(LiteralTermBuilder):
    "Convert the parse tree into a literal postfix term."
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
    "Convert the parse tree into a literal prefix term."
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
    "Objects of this class are used to reference the different converters."
    __CONVERTERS = {}
    def __init__(self):
        pass

    def register_converter(self, output_type, converter):
        "Register a converter for an output type."
        if not hasattr(converter, 'build'):
            raise TypeError, "Converters must provide a 'build' method."
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
    del sys, bind_all
except:
    pass


if __name__ == '__main__':
    import doctest
    doctest.testmod()
