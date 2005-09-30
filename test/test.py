import sys
sys.path.append('src')
sys.path.append('../src')

import unittest
from termparser import parse_term, tree_converters
from mathdom import MathDOM
from xmlterm import TermSaxParser, serialize_dom

def pyeval(term):
    return eval(term.replace('^', '**').replace('i', 'j'))


class TestInfixTerms(unittest.TestCase):
    TERMS = [
        '1+4*5+-7',
        '(1+4)*(-5)+7',
        '-7-7*-7/-3',
        '(.2+1i)/(3.-1i)',
        '-2^2',
        '-(2+2)^2'
        ]

    def testASTEval(self):
        converter = tree_converters['infix']
        for term in self.TERMS:
            ast = parse_term(term)
            infix = converter.build(ast)

            self.assertEqual(pyeval(term), pyeval(infix), "'%s' != '%s'" % (term, infix))

    def testDOMEval(self):
        for term in self.TERMS:
            doc = MathDOM.fromMathmlSax(term, TermSaxParser())
            infix = serialize_dom(doc, 'infix')

            self.assertEqual(pyeval(term), pyeval(infix), "'%s' != '%s'" % (term, infix))


if __name__ == '__main__':
    unittest.main()
