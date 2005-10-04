import sys
sys.path.append('src')
sys.path.append('../src')

import unittest
from termparser import parse_term, tree_converters
from mathdom import MathDOM
from xmlterm import TermSaxParser, serialize_dom

def pyeval(*terms):
    return [ eval(term.replace('^', '**').replace('i', 'j'))
             for term in terms ]

TERMS = [
    '1+4*5+-7',
    '(1+4)*(-5)+7',
    '-7-7*-7/-3',
    '(.2+1i)/(3.-1i)',
    '-2^3',
    '-2E4^3.4E-5',
    '-.02E-4-13.4E-15*(-(-.02E-4+13.4E-15))',
#    '-.02E-4-13.4E-15*-(-.02E-4+13.4E-15)', # FAILS in Parser
    '-(2+3)^2',
    '-2^-3',
    '-(3+2)^2-5^-2',
    '-(4+2)^2+7^+2',
    '(2+5)^2-7^+2',
    '(2+-3)*-2/-2^-2',
    '-(-1+-50)/-3*-5^(-2*-3)',
    ]

def ast_test_term(term):
    converter = tree_converters['infix']
    ast = parse_term(term)
    infix = converter.build(ast)

    return pyeval(term, infix)


def dom_test_term(term):
    doc = MathDOM.fromMathmlSax(term, TermSaxParser())
    infix = serialize_dom(doc, 'infix')

    return pyeval(term, infix)


###

def build_test_class(class_name, test_method, terms=TERMS):
    def build_test_method(term):
        def test(self):
            self.assertEqual(*test_method(term))
        test.__doc__ = "%s: %s" % (class_name, term)
        return test

    tests = dict(
        ('test%03d' % i, build_test_method(term))
        for i, term in enumerate(terms)
        )

    return type(class_name, (unittest.TestCase,), tests)


TestInfixTermAST = build_test_class('TestInfixTermAST', ast_test_term)
TestInfixTermDOM = build_test_class('TestInfixTermDOM', dom_test_term)


if __name__ == '__main__':
    test_suite = unittest.makeSuite(TestInfixTermAST)
    test_suite2 = unittest.makeSuite(TestInfixTermDOM)
    test_suite.addTest(test_suite2)

    unittest.TextTestRunner(verbosity=2).run(test_suite)
