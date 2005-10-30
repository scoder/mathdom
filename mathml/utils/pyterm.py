from mathml.termbuilder import tree_converters, InfixTermBuilder
from mathml.termparser  import (term_parsers, build_parser,
                                InfixTermParser, InfixBoolExpressionParser, ListParser)

# BUILDER

class PyTermBuilder(InfixTermBuilder):
    _INTERVAL_NOTATION = {
        u'closed'      : u'xrange(int(%s),   int(%s)+1)',
        u'closed-open' : u'xrange(int(%s),   int(%s)  )',
        u'open-closed' : u'xrange(int(%s)+1, int(%s)+1)',
        u'open'        : u'xrange(int(%s)+1, int(%s)  )'
        }

    _OPERATOR_MAP = {
        '^' : '**',
        }
    map_operator = _OPERATOR_MAP.get

    _NAME_MAP = {
        u'e'     : u'math.e',
        u'pi'    : u'math.pi',
        u'true'  : u'True',
        u'false' : u'False'
        }
    map_name = _NAME_MAP.get

    def _map_operator(self, operator):
        return self.map_operator(operator, operator)

    def _handle_name(self, operator, operands, affin):
        name = unicode(str(operands[0]), 'ascii')
        return [ self.map_name(name, name) ]

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

    def _handle_interval(self, operator, operands, affin):
        assert operator[:9] == u'interval:'
        return [ self._INTERVAL_NOTATION[ operator[9:] ] % tuple(operands) ]


tree_converters.register_converter('python',   PyTermBuilder())

# PARSER

class PyTermParser(InfixTermParser):
    operator_order = '** % / * - +'
    def _parse_operator(self, s,p,t):
        if t[0] == '**':
            return '^'
        else:
            return t

class PyBoolExpressionParser(InfixBoolExpressionParser):
    def build_term_parser(self):
        return PyTermParser()

CompletePyBoolExpression = PyBoolExpressionParser().p_bool_exp()
CompletePyTerm           = PyTermParser().p_arithmetic_exp()
CompletePyTermList       = ListParser(CompletePyTerm).p_list()

CompletePyBoolExpression.streamline()
CompletePyTerm.streamline()
CompletePyTermList.streamline()

term_parsers.register_converter('python_bool',      build_parser(CompletePyBoolExpression))
term_parsers.register_converter('python_term',      build_parser(CompletePyTerm))
term_parsers.register_converter('python_term_list', build_parser(CompletePyTermList))
