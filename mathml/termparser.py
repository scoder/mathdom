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

>>> from termparser import term_parsers
>>> from termbuilder import tree_converters
>>> term = '.1*pi+2*(1+3i)-5.6-6*-1/sin(-45*a.b) + 1'
>>> parsed_ast = term_parsers['infix_term'].parse(term)
>>> parsed_ast
('+', ('*', (u'const:real', Decimal("0.1")), (u'name', u'pi')), ('-', ('*', (u'const:integer', 2), (u'const:complex', Complex(1+3j))), (u'const:real', Decimal("5.6")), ('*', (u'const:integer', 6), ('/', (u'const:integer', -1), (u'sin', ('*', (u'const:integer', -45), (u'name', u'a.b')))))), (u'const:integer', 1))
>>> converter = tree_converters['infix']
>>> converter.build(parsed_ast)
u'0.1 * pi + 2 * (1+3i) - 5.6 - 6 * -1 / sin ( -45 * a.b ) + 1'


* boolean terms:

>>> bool_term = '%(term)s = 1 or %(term)s > 5 and true' % {'term':term}
>>> parsed_ast = term_parsers['infix_bool'].parse(bool_term)
>>> parsed_ast
(u'or', ('=', ('+', ('*', (u'const:real', Decimal("0.1")), (u'name', u'pi')), ('-', ('*', (u'const:integer', 2), (u'const:complex', Complex(1+3j))), (u'const:real', Decimal("5.6")), ('*', (u'const:integer', 6), ('/', (u'const:integer', -1), (u'sin', ('*', (u'const:integer', -45), (u'name', u'a.b')))))), (u'const:integer', 1)), (u'const:integer', 1)), (u'and', ('>', ('+', ('*', (u'const:real', Decimal("0.1")), (u'name', u'pi')), ('-', ('*', (u'const:integer', 2), (u'const:complex', Complex(1+3j))), (u'const:real', Decimal("5.6")), ('*', (u'const:integer', 6), ('/', (u'const:integer', -1), (u'sin', ('*', (u'const:integer', -45), (u'name', u'a.b')))))), (u'const:integer', 1)), (u'const:integer', 5)), (u'const:bool', True)))
>>> converter = tree_converters['postfix']
>>> converter.build(parsed_ast)
u'0.1 pi * 2 (1+3i) * 5.6 6 -1 -45 a.b * sin / * - - 1 + + 1 = 0.1 pi * 2 (1+3i) * 5.6 6 -1 -45 a.b * sin / * - - 1 + + 5 > true and or'
"""

__all__ = (
    'term_parsers',
    'ParseException'   # from pyparsing
    )

try:
    from psyco.classes import *
except ImportError:
    pass

from itertools import *
from pyparsing import *

from datatypes import Decimal, Complex, Rational, ENotation

class CaselessKeyword(Keyword):
    def __init__(self, value):
        Keyword.__init__(self, value, caseless=True)

class cached(object):
    "Property decorator to only calculate the value of a function once."
    def __init__(self, function):
        self.function = function
        self.name = function.__name__
    def __get__(self, instance, owner):
        if instance is None:
            return self
        result = self.function(instance)
        def return_result():
            return result
        setattr(instance, self.name, return_result)
        return return_result


class TermTokenizer(object):
    """Defines identifiers, attributes and basic data types:
    string, int, float, bool.
    """
    def _parse_attribute(self, s,p,t):
        return [ (u'name',           self._filter_name( t[0] )) ]
    def _parse_int(self, s,p,t):
        return [ (u'const:integer',  int(t[0])) ]
    def _parse_float(self, s,p,t):
        return [ (u'const:real',     Decimal(t[0])) ]
    def _parse_bool(self, s,p,t):
        return [ (u'const:bool',     t[0].lower() == 'true') ]
    def _parse_string(self, s,p,t):
        return [ (u'const:string',   t[0][1:-1]) ]
    def _parse_enotation(self, s,p,t):
        return [ (u'const:enotation', ENotation(t[0], t[1])) ]
    def _parse_complex(self, s,p,t):
        if len(t) == 1:
            value = Complex(0, Decimal(t[0]))
        else:
            value = Complex(Decimal(t[0]), Decimal(t[1]))
        return [ (u'const:complex', value) ]

    def _filter_name(self, name):
        return name

    # atoms: int, float, string
    p_sign = oneOf('+ -')

    _p_int = Combine( Optional(p_sign) + Word(nums) )
    _p_int.leaveWhitespace()

    _p_float_woE  = Literal('.') + Word(nums)
    _p_float_woE |= Word(nums) + Literal('.') + Optional(Word(nums))
    _p_float = Combine( Optional(p_sign) + _p_float_woE )
    _p_float.leaveWhitespace()

    @cached
    def p_enotation(self):
        p_enotation = (Combine(Optional(self.p_sign) + self._p_float_woE) | self._p_int) + Suppress(Literal('E')) + self._p_int
        p_enotation.leaveWhitespace()
        p_enotation.setName('e-notation')
        p_enotation.setParseAction(self._parse_enotation)
        return p_enotation

    @cached
    def p_complex(self):
        p_complex = Optional((self._p_float|self._p_int) + FollowedBy(oneOf('+ -'))) + (self._p_float|self._p_int) + Suppress(oneOf('i j'))
        p_complex.leaveWhitespace()
        p_complex.setParseAction(self._parse_complex)
        return p_complex

    @cached
    def p_int(self):
        p_int = self._p_int + Empty()
        p_int.setName('int')
        p_int.setParseAction(self._parse_int)
        return p_int

    @cached
    def p_float(self):
        p_float = self._p_float + Empty()
        p_float.setName('float')
        p_float.setParseAction(self._parse_float)
        return p_float

    @cached
    def p_num(self):
        p_num = self.p_complex() | self.p_enotation() | self.p_float() | self.p_int()
        #p_num.setName('number')
        return p_num

    @cached
    def p_bool(self):
        p_bool = CaselessKeyword(u'true') | CaselessKeyword(u'false')
        p_bool.setName('bool')
        p_bool.setParseAction(self._parse_bool)
        return p_bool

    @cached
    def p_string(self):
        p_string = sglQuotedString | dblQuotedString
        p_string.setName('string')
        p_string.setParseAction(self._parse_string)
        return p_string

    # identifier = [a-z][a-z0-9_]*
    @cached
    def p_simple_identifier(self):
        p_identifier = Word('abcdefghijklmnopqrstuvwxyz', '_abcdefghijklmnopqrstuvwxyz0123456789')
        p_identifier.setName('identifier')
        return p_identifier

    @cached
    def p_attribute(self):
        p_identifier = self.p_simple_identifier()
        p_attribute = Combine(p_identifier + ZeroOrMore( '.' + p_identifier ))
        p_attribute.setName('attribute')
        p_attribute.setParseAction(self._parse_attribute)
        return p_attribute

    @cached
    def p_identifier(self):
        return self.p_attribute()


class ArithmeticParserBase(object):
    def __init__(self):
        super(ArithmeticParserBase, self).__init__()
        self.tokenizer = self.build_tokenizer()

    def build_tokenizer(self):
        return TermTokenizer()

    def _build_expression_tree(self, match, pos, tokens):
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


class TermParserBase(ArithmeticParserBase):
    "Base class for arithmetic term parsers."
    interval_closure = {
        ('[', ']') : u'closed',
        ('[', ')') : u'closed-open',
        ('(', ']') : u'open-closed',
        ('(', ')') : u'open'
        }

    operator_order = '^ % / * - +'

    def _parse_operator(self, s,p,t):
        return t
    def _parse_interval(self, s,p,t):
        return [ (u'interval:%s' % self.interval_closure[(t[0], t[-1])],) + tuple(t[1:-1]) ]
    def _parse_function(self, s,p,t):
        return [ tuple(t) ]
    def _parse_case(self, s,p,t):
        return [ (u'case',) + tuple(t) ]

    def p_arithmetic_interval(self, p_arithmetic_exp):
        p_arithmetic_interval = oneOf('( [') + p_arithmetic_exp + Suppress(',') + p_arithmetic_exp + oneOf(') ]')
        p_arithmetic_interval.setParseAction(self._parse_interval)
        return p_arithmetic_interval


class InfixTermParser(TermParserBase):
    p_bool_expression = Forward()

    # arithmetic = a+b*c-(3*4)...
    def p_operator_cascade(self, p_num_atom, ordered_operator_list):
        p_exp = p_num_atom
        # build grammar tree for binary operators in order of precedence
        for operator in ordered_operator_list:
            p_op = Literal(operator)
            p_op.setParseAction(self._parse_operator)
            # ZeroOrMore->Optional could speed this up
            if operator == '-':
                neg_exp = p_op + p_exp
                neg_exp.setParseAction(self._build_expression_tree)
                p_exp = (p_exp ^ neg_exp) + ZeroOrMore( p_op + p_exp )
            else:
                p_exp = p_exp + ZeroOrMore( p_op + p_exp )
            p_exp.setParseAction(self._build_expression_tree)

        return p_exp

    @cached
    def p_arithmetic_exp(self):
        "Main production: arithmetic expression."
        _p_num_atom = Forward()
        p_arithmetic_exp  = self.p_operator_cascade(_p_num_atom, self.operator_order.split())

        p_num        = self.tokenizer.p_num()
        p_identifier = self.tokenizer.p_identifier()
        p_function   = self.p_function(p_arithmetic_exp)
        p_case       = self.p_case(p_arithmetic_exp, self.p_bool_expression)

        # numeric values = attribute | number | expression
        _p_num_atom <<= p_case | ( Suppress('(') + p_arithmetic_exp + Suppress(')') ) | p_num | p_function | p_identifier

        return p_arithmetic_exp

    # function = identifier(exp,...)
    def p_function(self, p_arithmetic_exp):
        p_function = self.tokenizer.p_simple_identifier() + Suppress('(') + delimitedList(p_arithmetic_exp) + Suppress(')')
        p_function.setParseAction(self._parse_function)
        return p_function

    def p_case(self, p_arithmetic_exp, p_bool_expression):
        p_case = (Suppress(CaselessKeyword(u'CASE') + CaselessKeyword(u'WHEN')) +
                  p_bool_expression +
                  Suppress(CaselessKeyword(u'THEN')) + p_arithmetic_exp +
                  # Optional => undefined values in expressions!
                  #Optional(Suppress(CaselessKeyword('ELSE')) + _p_exp) +
                  Suppress(CaselessKeyword(u'ELSE')) + p_arithmetic_exp +
                  Suppress(CaselessKeyword(u'END'))
                  )
        p_case.setParseAction(self._parse_case)
        return p_case

    """
    # currently unused:

    p_arithmetic_tuple = Suppress('(') + p_arithmetic_list + Suppress(')')

    def _parse_int_list(s,p,t):
        return [ (u'list:int',)    + tuple(t) ]
    def _parse_float_list(s,p,t):
        return [ (u'list:float',)  + tuple(t) ]
    def _parse_string_list(s,p,t):
        return [ (u'list:str',)    + tuple(t) ]
    def _parse_bool_list(s,p,t):
        return [ (u'list:bool',)   + tuple(t) ]

    # int list = (3,6,43,554)
    p_int_list = delimitedList(TermTokenizer.p_int | TermTokenizer.p_attribute)
    p_int_list.setParseAction(_parse_int_list)

    # typed list = (strings) | (ints) | (floats) | ...
    p_string_list = delimitedList(TermTokenizer.p_string | TermTokenizer.p_attribute)
    p_string_list.setParseAction(_parse_string_list)
    p_bool_list   = delimitedList(TermTokenizer.p_bool | TermTokenizer.p_attribute)
    p_bool_list.setParseAction(_parse_bool_list)
    p_float_list  = delimitedList(TermTokenizer.p_float | TermTokenizer.p_attribute)
    p_float_list.setParseAction(_parse_float_list)

    p_any_list = p_float_list | p_int_list | p_string_list | p_bool_list
    """



class BoolParserBase(object):
    def __init__(self):
        super(BoolParserBase, self).__init__()
        self.term_parser = self.build_term_parser()
        self.tokenizer   = self.build_tokenizer()
        self._build_expression_tree = self.term_parser._build_expression_tree

    def build_term_parser(self):
        "Default: raise NotImplementedException"
        raise NotImplementedException, "build_term_parser()"
        return InfixTermParser()

    def build_tokenizer(self):
        "Default: copy tokenizer from self.term_parser"
        return self.term_parser.tokenizer

    def _parse_bool_operator(self, s,p,t):
        return t

    cmp_operators = '= != <> > < <= >='

    p_bool_and = CaselessKeyword(u'and')
    p_bool_or  = CaselessKeyword(u'or')
    p_bool_not = CaselessKeyword(u'not')

    @cached
    def p_bool_operator(self):
        p_bool_operator = oneOf( u'= <>')
        p_bool_operator.setName('bool_op')
        return p_bool_operator

    @cached
    def p_cmp_operator(self):
        p_cmp_operator = oneOf(self.cmp_operators)
        p_cmp_operator.setName('cmp_op')
        return p_cmp_operator

    @cached
    def p_cmp_in(self):
        p_cmp_in = CaselessKeyword(u'in') | CaselessKeyword(u'notin')
        return p_cmp_in


class InfixBoolExpressionParser(BoolParserBase):
    # exp = a op b
    def build_term_parser(self):
        "Default: InfixTermParser()"
        return InfixTermParser()

    @cached
    def p_bool_cmp(self):
        p_bool_operator = self.p_bool_operator()
        p_bool          = self.tokenizer.p_bool()
        p_identifier    = self.tokenizer.p_identifier()

        p_bool_cmp  = p_bool + OneOrMore( p_bool_operator + p_identifier )
        p_bool_cmp |= (p_bool | p_identifier) + Optional( p_bool_operator + p_bool )
        return p_bool_cmp

    @cached
    def p_str_cmp(self):
        p_identifier   = self.tokenizer.p_identifier()
        p_string       = self.tokenizer.p_string()
        p_cmp_operator = self.p_cmp_operator()

        p_str_cmp   = p_identifier + OneOrMore( p_cmp_operator + p_string )
        p_str_cmp  |= p_string     + OneOrMore( p_cmp_operator + p_identifier )
        return p_str_cmp

    @cached
    def p_list_cmp(self):
        p_arithmetic_exp      = self.term_parser.p_arithmetic_exp()
        p_arithmetic_interval = self.term_parser.p_arithmetic_interval(p_arithmetic_exp)

        return p_arithmetic_exp + self.p_cmp_in() + p_arithmetic_interval # p_arithmetic_tuple

    @cached
    def p_factor_cmp(self):
        p_arithmetic_exp = self.term_parser.p_arithmetic_exp()
        return p_arithmetic_exp + Literal('|') + p_arithmetic_exp

    @cached
    def p_arithmetic_cmp(self):
        p_arithmetic_exp = self.term_parser.p_arithmetic_exp()
        return p_arithmetic_exp + self.p_cmp_operator() + p_arithmetic_exp

    @cached
    def p_cmp_exp(self):
        p_exp = self.p_str_cmp()    | self.p_list_cmp() | self.p_arithmetic_cmp() | \
                self.p_factor_cmp() | self.p_bool_cmp()
        p_exp.setParseAction(self._build_expression_tree)
        return p_exp

    # bool_exp = a or b and c and (d or e) ...
    def _p_op_exp(self, p_op, p_exp):
        p_op.setParseAction(self._parse_bool_operator)
        p_op_exp = p_exp + ZeroOrMore( p_op + p_exp )
        p_op_exp.setParseAction(self._build_expression_tree)
        return p_op_exp
        
    @cached
    def p_bool_exp(self):
        p_atom_exp = Forward()

        p_and_exp = self._p_op_exp(self.p_bool_and, p_atom_exp)
        p_and_exp.setParseAction(self._build_expression_tree)

        p_or_exp  = self._p_op_exp(self.p_bool_or,  p_and_exp )
        p_or_exp.setParseAction(self._build_expression_tree)

        p_not_exp = self.p_bool_not + p_atom_exp
        p_not_exp.setParseAction(self._build_expression_tree)

        p_atom_exp <<= p_not_exp | (Suppress('(') + p_or_exp + Suppress(')')) | self.p_cmp_exp()
        return p_or_exp

# repair CASE statement in InfixTermParser
InfixTermParser.p_bool_expression <<= InfixBoolExpressionParser().p_bool_exp()


class ListParser(object):
    def __init__(self, p_item):
        self.p_item = p_item

    def _parse_list(self, s,p,t):
        return [ (u'list',)  + tuple(t) ]

    @cached
    def p_list(self):
        p_list = delimitedList(self.p_item)
        p_list.setParseAction(self._parse_list)
        return p_list


# optimize parser
CompleteBoolExpression = InfixBoolExpressionParser().p_bool_exp()
CompleteTerm           = InfixTermParser().p_arithmetic_exp()
CompleteTermList       = ListParser(CompleteTerm).p_list()

CompleteBoolExpression.streamline()
CompleteTerm.streamline()
CompleteTermList.streamline()


class ConverterRegistry(object):
    """Objects of this class are used to reference the different converters.

    Subclasses must define an attribute _METHOD_NAME that names the
    conversion method that converters must provide
    """
    def __init__(self):
        self._converters  = {}

    def register_converter(self, converter_type, converter):
        "Register a converter for an converter type."
        if not hasattr(converter, self._METHOD_NAME):
            raise TypeError, "Converters must have a '%s' method." % self._METHOD_NAME
        self._converters[converter_type] = converter

    __setitem__ = register_converter

    def unregister_converter(self, converter_type):
        "Remove the registration for an converter type."
        del self._converters[converter_type]

    __delitem__ = unregister_converter

    def fortype(self, converter_type):
        "Return the converter for the given converter type."
        return self._converters.get(converter_type)

    def __getitem__(self, converter_type):
        return self._converters[converter_type]

    def known_types(self):
        "Return the currently registered converter types."
        return self._converters.keys()

    def convert(self, value, conversion_type):
        converter = self._converters[conversion_type]
        convert = getattr(converter, self._METHOD_NAME)
        return convert(value)


# main module functions:

class TermParsing(ConverterRegistry):
    _METHOD_NAME = 'parse'
    def parse(self, term, input_type):
        "Convert a parse tree into a term of the given input type."
        converter = self._converters[input_type]
        return converter.parse(term)


def build_parser(parser):
    parseString = parser.parseString
    class Parser(object):
        def parse(self, term):
            if not isinstance(term, unicode):
                term = unicode(term, 'ascii')
            return parseString(term)[0]
    return Parser()
            

term_parsers = TermParsing()

term_parsers.register_converter('infix_bool',      build_parser(CompleteBoolExpression))
term_parsers.register_converter('infix_term',      build_parser(CompleteTerm))
term_parsers.register_converter('infix_term_list', build_parser(CompleteTermList))


try:
    import sys
    from optimize import bind_all
    bind_all(sys.modules[__name__])
    import pyparsing
    bind_all(pyparsing)
    del sys, bind_all
except:
    pass


if __name__ == '__main__':
    import doctest
    doctest.testmod()
