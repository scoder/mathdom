MATHML_NAMESPACE_URI = u"http://www.w3.org/1998/Math/MathML"


UNARY_ARITHMETIC_FUNCTIONS = u"""
factorial minus abs conjugate arg real imaginary floor ceiling
"""

UNARY_LOGICAL_FUNCTIONS    = u"""
not
"""

UNARY_ELEMENTARY_CLASSICAL_FUNCTIONS = u"""
sin cos tan sec csc cot sinh cosh tanh sech csch coth
arcsin arccos arctan arccosh arccot arccoth arccsc arccsch
arcsec arcsech arcsinh arctanh exp ln log
"""

BINARY_ARITHMETIC_FUNCTIONS = u"""
quotient divide minus power rem
"""

NARY_ARITHMETIC_FUNCTIONS = u"""
plus times max min gcd lcm
"""

NARY_STATISTICAL_FUNCTIONS = u"""
mean sdev variance median mode
"""

NARY_LOGICAL_FUNCTIONS = u"""
and or xor
"""

NARY_FUNCTIONAL_FUNCTION = u"""
compose
"""

BINARY_SET_CONTAINMENT = u"""
in notin
"""

BINARY_RELATIONS = u"""
neq equivalent approx factorof
"""

NARY_RELATIONS = u"""
eq leq lt geq gt
"""

CONSTANTS = u"""
pi ExponentialE ee ImaginaryI ii gamma infin infty true false NotANumber NaN
"""

##

UNARY_FUNCTIONS  = UNARY_ELEMENTARY_CLASSICAL_FUNCTIONS + \
                   UNARY_ARITHMETIC_FUNCTIONS + \
                   UNARY_LOGICAL_FUNCTIONS

BINARY_FUNCTIONS = BINARY_ARITHMETIC_FUNCTIONS + \
                   BINARY_SET_CONTAINMENT

NARY_FUNCTIONS   = NARY_ARITHMETIC_FUNCTIONS + \
                   NARY_STATISTICAL_FUNCTIONS + \
                   NARY_LOGICAL_FUNCTIONS + \
                   NARY_FUNCTIONAL_FUNCTION

##

FUNCTIONS = UNARY_FUNCTIONS + BINARY_FUNCTIONS + NARY_FUNCTIONS

RELATIONS = BINARY_RELATIONS + NARY_RELATIONS + BINARY_SET_CONTAINMENT
