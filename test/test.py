import sys, re
sys.path.insert(0, 'src')
sys.path.insert(0, '../src')

import unittest
from termparser   import parse_term, parse_bool_expression
from termbuilder  import tree_converters
from utils.pyterm import PyTermBuilder
from mathdom import MathDOM
from xmlterm import TermSaxParser, BoolExpressionSaxParser, serialize_dom


build_pyterm = PyTermBuilder().build

def pyeval_term(*terms):
    pyterms = [ build_pyterm(parse_term(term)) for term in terms ]
    return map(eval, pyterms)
def pyeval_bool(*terms):
    pyterms = [ build_pyterm(parse_bool_expression(term)) for term in terms ]
    return map(eval, pyterms)

TERMS = {
    '1+4*5+-7' : 1+4*5+-7,
    '(1+4)*(-5)+7' : (1+4)*(-5)+7,
    '-7-7*-7/-3' : -7-7*-7/-3,
    '(.2+1i)/(3.-1i)' : (.2+1j)/(3.-1j),
    '-2^3' : -2**3,
    '-2E4^3.4E-5' : -2E4**3.4E-5,
    '-.02E-4-13.4E-15*(-(-.02E-4+13.4E-15))' : -.02E-4-13.4E-15*(-(-.02E-4+13.4E-15)),
#    '-.02E-4-13.4E-15*-(-.02E-4+13.4E-15)', # FAILS in Parser
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

def ast_test_term(term):
    converter = tree_converters['infix']
    ast = parse_term(term)
    infix = converter.build(ast)

    return pyeval_term(term, infix)


def dom_test_term(term):
    doc = MathDOM.fromMathmlSax(term, TermSaxParser())
    infix = serialize_dom(doc, 'infix')

    return pyeval_term(term, infix)


def ast_test_bool(expression):
    converter = tree_converters['infix']
    ast = parse_bool_expression(expression)
    infix = converter.build(ast)

    return pyeval_bool(expression, infix)


def dom_test_bool(expression):
    doc = MathDOM.fromMathmlSax(expression, BoolExpressionSaxParser())
    infix = serialize_dom(doc, 'infix')

    return pyeval_bool(expression, infix)


###

def build_test_class(class_name, test_method, terms=TERMS):
    def build_test_method(term, result):
        def test(self):
            results = test_method(term)
            #print result
            if result is None:
                self.assertEqual(*results)
            else:
                for r in results:
                    self.assertEqual(r, result)
        test.__doc__ = "%s: %s" % (class_name, term)
        return test

    tests = dict(
        ('test%03d' % i, build_test_method(term, result))
        for i, (term, result) in enumerate(sorted(terms.iteritems()))
        )

    return type(class_name, (unittest.TestCase,), tests)


TestInfixTermAST = build_test_class('TestInfixTermAST', ast_test_term, TERMS)
TestInfixTermDOM = build_test_class('TestInfixTermDOM', dom_test_term, TERMS)
TestInfixExprAST = build_test_class('TestInfixExprAST', ast_test_bool, BOOLEAN_TERMS)
TestInfixExprDOM = build_test_class('TestInfixExprDOM', dom_test_bool, BOOLEAN_TERMS)


if __name__ == '__main__':
    test_suite = unittest.makeSuite(TestInfixTermAST)
    for testclass in (TestInfixTermDOM, TestInfixExprAST, TestInfixExprDOM):
        test_suite2 = unittest.makeSuite(testclass)
        test_suite.addTest(test_suite2)

    unittest.TextTestRunner(verbosity=2).run(test_suite)
