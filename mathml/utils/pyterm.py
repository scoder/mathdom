from mathml.termbuilder import tree_converters, InfixTermBuilder
from mathml.termparser  import (term_parsers, cached, TermTokenizer,
                                InfixTermParser, InfixBoolExpressionParser, ListParser,
                                CaselessKeyword)

__all__ = [ 'PyTermBuilder', 'PyTermParser', 'PyBoolExpressionParser', 'ParseException' ]

# BUILDER

class PyTermBuilder(InfixTermBuilder):
    _INTERVAL_NOTATION = {
        u'closed'      : u'xrange(int(%s),   int(%s)+1)'.replace(u' ', u''),
        u'closed-open' : u'xrange(int(%s),   int(%s)  )'.replace(u' ', u''),
        u'open-closed' : u'xrange(int(%s)+1, int(%s)+1)'.replace(u' ', u''),
        u'open'        : u'xrange(int(%s)+1, int(%s)  )'.replace(u' ', u'')
        }

    _OPERATOR_MAP = {
        '^'       : '**',
        '='       : '==',
        'acos'    : 'math.acos',
        'asin'    : 'math.asin',
        'atan'    : 'math.atan',
        'atan2'   : 'math.atan2',
        'ceil'    : 'math.ceil',
        'cos'     : 'math.cos',
        'cosh'    : 'math.cosh',
        'degrees' : 'math.degrees',
        'exp'     : 'math.exp',
        'floor'   : 'math.floor',
        'log'     : 'math.log',
        'log10'   : 'math.log10',
        'pow'     : 'math.pow',
        'radians' : 'math.radians',
        'sin'     : 'math.sin',
        'sinh'    : 'math.sinh',
        'sqrt'    : 'math.sqrt',
        'tan'     : 'math.tan',
        'tanh'    : 'math.tanh'
        }

    _NAME_MAP = {
        u'e'     : u'math.e',
        u'pi'    : u'math.pi',
        u'true'  : u'True',
        u'false' : u'False'
        }

    def _handle_const_bool(self, operator, operands, affin):
        return [ operands[0] and 'True' or 'False' ]

    def _handle_const_complex(self, operator, operands, affin):
        value = operands[0]
        if value.imag == 0:
            return value.real_str
        real_str = value.real_str
        if real_str == "0":
            real_str = ''
        return [ u'(%s%s%sj)' % (real_str, (value.imag >= 0) and '+' or '', value.imag_str) ]

    def _handle_case(self, operator, operands, affin_status):
        assert operator == 'case'
        result = [ operands[0], 'and', operands[1] ]
        if len(operands) > 2:
            result.append('or')
            result.append(operands[2])
        return result

    def _handle_interval(self, operator, operands, affin):
        assert operator[:9] == u'interval:'
        return [ self._INTERVAL_NOTATION[ operator[9:] ] % tuple(operands) ]


tree_converters.register_converter('python',   PyTermBuilder())

# PARSER

from pyparsing import *

class PyTermTokenizer(TermTokenizer):
    _CONSTANT_MAP = {
        u'math.e'  : u'e',
        u'math.pi' : u'pi'
        }

    @cached
    def p_bool(self):
        p_bool = Keyword(u'True') | Keyword(u'False')
        p_bool.setName('bool')
        p_bool.setParseAction(self._parse_bool)
        return p_bool

class PyTermParser(InfixTermParser):
    OPERATOR_ORDER = InfixTermParser.OPERATOR_ORDER.replace(' ^ ', ' ** ')

    def build_tokenizer(self):
        return PyTermTokenizer()

    @cached
    def _zero(self):
        return self.tokenizer._parse_int(None, None, ["0"])[0]

    def _parse_operator(self, s,p,t):
        if t[0] == '**':
            return [ '^' ]
        else:
            return t

    def p_operator(self, operator):
        p_op = super(PyTermParser, self).p_operator(operator)
        if operator == '*':
            p_op = p_op + NotAny('*')
        return p_op

    def _parse_interval(self, s,p,t):
        if len(t) == 1:
            start, stop = self._zero(), t[0]
        else:
            start, stop = t
        return [ (u'interval:closed-open', start, stop) ]

    def p_case(self, *args):
        return NoMatch()

    def p_arithmetic_interval(self, p_arithmetic_exp):
        p_interval = Suppress(Literal('xrange') | Literal('range')) + Suppress('(') \
                     + p_arithmetic_exp + Optional(Suppress(',') + p_arithmetic_exp) \
                     + Suppress(')')
        p_interval.setParseAction(self._parse_interval)
        return p_interval

class PyBoolExpressionParser(InfixBoolExpressionParser):
    def build_term_parser(self):
        return PyTermParser()

    @cached
    def p_cmp_in(self):
        not_in = Combine(CaselessKeyword(u'not') + CaselessKeyword(u'in'), adjacent=False)
        p_cmp_in = CaselessKeyword(u'in') | not_in
        p_cmp_in.setParseAction(self._parse_cmp_operator)
        return p_cmp_in


py_term = PyTermParser().p_arithmetic_exp()
term_parsers.register_converter('python_bool',      PyBoolExpressionParser().p_bool_exp())
term_parsers.register_converter('python_term',      py_term)
term_parsers.register_converter('python_term_list', ListParser(py_term).p_list())
del py_term
