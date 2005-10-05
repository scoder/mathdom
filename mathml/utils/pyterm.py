from termbuilder import InfixTermBuilder

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
        u'e'     : u'math.E',
        u'pi'    : u'math.PI',
        u'true'  : u'True',
        u'false' : u'False'
        }
    map_name = _NAME_MAP.get

    def _map_operator(self, operator):
        return self.map_operator(operator, operator)

    def _handle_name(self, operator, operands, affin):
        name = unicode(str(operands[0]), 'ascii')
        return [ map_name(name, name) ]

    def _handle_const_bool(self, operator, operands, affin):
        return [ operands[0] and 'True' or 'False' ]

    def _handle_const_complex(self, operator, operands, affin):
        value = operands[0]
        return [ u'(%s%s%sj)' % (value.real_str, (value.imag >= 0) and '+' or '', value.imag_str) ]

    def _handle_interval(self, operator, operands, affin):
        assert operator[:9] == u'interval:'
        return [ self._INTERVAL_NOTATION[ operator[9:] ] % tuple(operands) ]


## May add a PyTermParser in future releases ...
