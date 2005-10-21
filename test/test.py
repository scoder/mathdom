import sys
sys.path.insert(0, '..')

import unittest
from itertools import count, chain, starmap

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


from mathml import FUNCTIONS, RELATIONS
ALL_OPERATORS = frozenset(chain(FUNCTIONS.split(), RELATIONS.split()))


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

def build_test_class(term_type, mathdom):
    class_name = term_type
    impl_name  = mathdom.__module__.rsplit('.', 1)[-1]

    def docstr(test_name, term):
        return "%-8s - %-9s - %s: %s" % (impl_name, test_name, class_name.replace('_', ' '), term)

    def build_term_test_method(test_method, term, result):
        def test(self):
            result_iter = test_method(term, term_type, mathdom)
            #print result
            if result is None:
                self.assertEqual(*tuple(result_iter)[:2])
            else:
                for r in result_iter:
                    self.assertEqual(r, result)
        test.__doc__ = docstr(test_method.func_name, term)
        return test

    def build_dom_test_method(term):
        def test(self):
            doc = mathdom.fromString(term, term_type)
            root = doc.xpath("/*")[0]
            self.assertEquals(root.mathtype(), u'math')
            element = root.firstChild
            if element:
                try:
                    value = float(term)
                    self.assertEquals(element.value(), value)
                except ValueError:
                    self.assertEquals(element.mathtype(), 'apply')
                    self.assert_(element.firstChild.mathtype() in ALL_OPERATORS,
                                 element.firstChild.mathtype())
        test.__doc__ = docstr("dom_work", term)
        return test

    def build_output_test(term, method_name):
        if not hasattr(mathdom, method_name):
            return None
        def test(self):
            doc = mathdom.fromString(term, term_type)
            result = getattr(doc, method_name)()
            self.assert_(result, result)
        test.__doc__ = docstr(method_name, term)
        return test

    def build_validate_test(term):
        if not hasattr(mathdom, 'validate'):
            return None
        def test(self):
            doc = mathdom.fromString(term, term_type)
            self.assert_(doc.validate())
        test.__doc__ = docstr("validate", term)
        return test

    terms = TERMS[term_type]
    test_name = ("test_%05d" % i for i in count()).next

    tests = dict(
        (test_name(), build_term_test_method(test_method, term, result))
        for m, test_method in enumerate((ast_test, dom_test))
        for i, (term, result) in enumerate(sorted(terms.iteritems()))
        )

    tests.update(
        (test_name(), test_builder(term))
        for test_builder in (build_dom_test_method, build_validate_test)
        for i, term in enumerate(sorted(terms.iterkeys()))
        )

    tests.update(
        (test_name(), build_output_test(term, method_name))
        for m, method_name in enumerate(['to_pres', 'to_tree', 'serialize'])
        for i, term in enumerate(sorted(terms.iterkeys()))
        )

    return type(class_name, (unittest.TestCase,), tests)


if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    mathdom_impls = []
    try:
        from mathml.mathdom  import MathDOM as pyMathDOM
        mathdom_impls.append(pyMathDOM)
    except ImportError:
        pass
    try:
        from mathml.lmathdom import MathDOM as lxMathDOM
        mathdom_impls.append(lxMathDOM)
    except ImportError:
        pass

    test_classes = starmap(build_test_class,
                           ( (t, mathdom)
                             for mathdom in mathdom_impls
                             for t in TERMS.iterkeys()
                             )
                           )

    test_suite = unittest.TestSuite()
    test_suite.addTests(map(unittest.makeSuite, test_classes))

    unittest.TextTestRunner(verbosity=2).run(test_suite)
