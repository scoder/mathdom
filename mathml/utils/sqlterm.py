from mathml.termbuilder import tree_converters, InfixTermBuilder

__all__ = [ 'SqlTermBuilder' ]

# BUILDER

class SqlTermBuilder(InfixTermBuilder):
    _NAME_MAP = {
        u'e'     : u'exp(1.0)',
        u'pi'    : u'pi()',
        u'true'  : u'TRUE',
        u'false' : u'FALSE'
        }

    def _handle_const_bool(self, operator, operands, affin):
        return [ operands[0] and 'TRUE' or 'FALSE' ]

    def _handle_const_complex(self, operator, operands, affin):
        raise NotImplementedError, "Complex numbers cannot be converted to SQL."

    def _handle_interval(self, operator, operands, affin):
        raise NotImplementedError, "Intervals cannot be converted to SQL."


tree_converters.register_converter('sql', SqlTermBuilder())
