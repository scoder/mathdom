import sys
sys.path.insert(0, '..')

import unittest
from itertools import chain, starmap

from mathml.termparser   import term_parsers
from mathml.termbuilder  import tree_converters
from mathml.utils.pyterm import PyTermBuilder
from mathml.xmlterm import SaxTerm, serialize_dom


build_pyterm = PyTermBuilder().build

def pyeval(term_type, *terms):
    parse = term_parsers[term_type].parse
    my_globals, my_locals = globals(), {}
    pyterms = [ (build_pyterm(parse(term)), my_globals, my_locals) for term in terms ]
    return starmap(eval, pyterms)

ARITHMETIC_TERMS = {
    '1+4*5+-7' : 1+4*5+-7,
    '(1+4)*(-5)+7' : (1+4)*(-5)+7,
    '-7-7*-7/-3' : -7-7*-7/-3,
    '(.2+1i)/(3.-1i)' : (.2+1j)/(3.-1j),
    '-2^3' : -2**3,
    '-2E4^3.4E-5' : -2E4**3.4E-5,
    '-.02E-4-13.4E-15*(-(-.02E-4+13.4E-15))' : -.02E-4-13.4E-15*(-(-.02E-4+13.4E-15)),
#    ' 15*-(1+1)'   :  15*-(1+1), # FAILS in Parser
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
    'not true and false' : False,
    'true and not false' : True,
    '1+1 < 2+2'  : True,
    '1 in (3,4)' : False,
    '3 in [3,4)' : True,
    '3 in [2*1+1,3^1+2-1)' : True,
    }


TERMS = {
    'infix_term' : ARITHMETIC_TERMS,
    'infix_bool' : BOOLEAN_TERMS
    }


def ast_test(term, term_type, _):
    parser = term_parsers[term_type]
    infix_converter  = tree_converters['infix']
    python_converter = tree_converters['python']

    ast = parser.parse(term)
    infix  = infix_converter.build(ast)
    pyterm = python_converter.build(ast)

    return chain(pyeval(term_type, term, infix), [eval(pyterm)])


def dom_test(term, term_type, mathdom):
    doc = mathdom.fromString(term, term_type)
    infix  = serialize_dom(doc, 'infix')
    pyterm = serialize_dom(doc, 'python')

    return chain(pyeval(term_type, term, infix), [eval(pyterm)])


###

def build_test_class(test_method, term_type, which_MathDOM):
    class_name = "%s_%s" % (test_method.func_name, term_type)
    impl_name  = which_MathDOM.__module__.split('.')[-1]

    def build_test_method(term, result):
        def test(self):
            result_iter = test_method(term, term_type, which_MathDOM)
            #print result
            if result is None:
                self.assertEqual(*tuple(result_iter)[:2])
            else:
                for r in result_iter:
                    self.assertEqual(r, result)
        test.__doc__ = "%-8s - %s: %s" % (impl_name, class_name.replace('_', ' '), term)
        return test

    terms = TERMS[term_type]
    tests = dict(
        ('test%03d' % i, build_test_method(term, result))
        for i, (term, result) in enumerate(sorted(terms.iteritems()))
        )

    return type(class_name, (unittest.TestCase,), tests)


if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    from mathml.mathdom  import MathDOM as dMathDOM
    from mathml.lmathdom import MathDOM as lMathDOM

    test_classes = starmap(build_test_class,
                           ( (m, t, mathdom)
                             for mathdom in (dMathDOM, lMathDOM)
                             for m in (ast_test, dom_test)
                             for t in TERMS.iterkeys()
                             )
                           )

    test_suite = unittest.makeSuite(test_classes.next())
    for testclass in test_classes:
        test_suite2 = unittest.makeSuite(testclass)
        test_suite.addTest(test_suite2)

    unittest.TextTestRunner(verbosity=2).run(test_suite)
