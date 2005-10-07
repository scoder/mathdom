import sys
sys.path.insert(0, '..')

import unittest
from itertools import starmap

from mathml.termparser   import term_parsers
from mathml.termbuilder  import tree_converters
from mathml.utils.pyterm import PyTermBuilder
from mathml.mathdom import MathDOM
from mathml.xmlterm import SaxTerm, serialize_dom


build_pyterm = PyTermBuilder().build

def pyeval(term_type, *terms):
    parse = term_parsers[term_type].parse
    pyterms = [ build_pyterm(parse(term)) for term in terms ]
    return map(eval, pyterms)

ARITHMETIC_TERMS = {
    '1+4*5+-7' : 1+4*5+-7,
    '(1+4)*(-5)+7' : (1+4)*(-5)+7,
    '-7-7*-7/-3' : -7-7*-7/-3,
    '(.2+1i)/(3.-1i)' : (.2+1j)/(3.-1j),
    '-2^3' : -2**3,
    '-2E4^3.4E-5' : -2E4**3.4E-5,
    '-.02E-4-13.4E-15*(-(-.02E-4+13.4E-15))' : -.02E-4-13.4E-15*(-(-.02E-4+13.4E-15)),
#    ' 15*-(-1-15)'   :  15*-(1+1), # FAILS in Parser
    '-(2+3)^2' : -(2+3)**2,
    '-2^-3' : -2**-3,
    '-(3+2)^2-5^-2' : -(3+2)**2-5**-2,
    '-(4+2)^2+7^+2' : -(4+2)**2+7**+2,
    '(2+5)^2-7^+2'  : (2+5)**2-7**+2,
    '(2+-3)*-2/-2^-2' : (2+-3)*-2/-2**-2,
    '-(-1+-50)/-3*-5^(-2*-3)' : -(-1+-50)/-3*-5**(-2*-3),
    '16/4/2'      : 16/4/2,
    '16/4/2*2'    : 16/4/2*2,
    '16/4/(2*2)'  : 16/4/(2*2),
    '16/(2*4)/2'  : 16/(2*4)/2,
    '16/2*4/2'    : 16/2*4/2,
    }

BOOLEAN_TERMS = {
    'true or false'  : True,
    'true and false' : False,
    '1+1 < 2+2'  : True,
    '1 in (3,4)' : False,
    '3 in [3,4)' : True,
    '3 in [2*1+1,3^1+2-1)' : True,
    }


TERMS = {
    'infix_term' : ARITHMETIC_TERMS,
    'infix_bool' : BOOLEAN_TERMS
    }


def ast_test(term, term_type):
    parser = term_parsers[term_type]
    converter = tree_converters['infix']

    ast = parser.parse(term)
    infix = converter.build(ast)

    return pyeval(term_type, term, infix)


def dom_test(term, term_type):
    doc = MathDOM.fromString(term, term_type)
    infix = serialize_dom(doc, 'infix')

    return pyeval(term_type, term, infix)


###

def build_test_class(test_method, term_type):
    class_name = "%s_%s" % (test_method.func_name, term_type)

    def build_test_method(term, result):
        def test(self):
            results = test_method(term, term_type)
            #print result
            if result is None:
                self.assertEqual(*results)
            else:
                for r in results:
                    self.assertEqual(r, result)
        test.__doc__ = "%s: %s" % (class_name.replace('_', ' '), term)
        return test

    terms = TERMS[term_type]
    tests = dict(
        ('test%03d' % i, build_test_method(term, result))
        for i, (term, result) in enumerate(sorted(terms.iteritems()))
        )

    return type(class_name, (unittest.TestCase,), tests)


if __name__ == '__main__':
    test_classes = starmap(build_test_class,
                           ( (m, t) for m in (ast_test, dom_test) for t in TERMS.iterkeys())
                           )

    test_suite = unittest.makeSuite(test_classes.next())
    for testclass in test_classes:
        test_suite2 = unittest.makeSuite(testclass)
        test_suite.addTest(test_suite2)

    unittest.TextTestRunner(verbosity=2).run(test_suite)
