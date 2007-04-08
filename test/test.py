import sys
sys.path.insert(0, '..')
#sys.stderr = sys.stdout

import unittest, types
from itertools import count, chain, starmap
from StringIO import StringIO

from mathml.termparser   import term_parsers, ParseException
from mathml.termbuilder  import tree_converters
from mathml.utils.pyterm import PyTermBuilder
from mathml.xmlterm import SaxTerm, serialize_dom


build_pyterm = PyTermBuilder().build

def pyeval(*terms):
    my_globals, my_locals = globals(), {}
    pyterms = [ (build_pyterm(term_parsers[term_type].parse(term)), my_globals, my_locals)
                for term_type, term in terms ]
    return starmap(eval, pyterms)

ARITHMETIC_TERMS = {
    '16'            : 16,
    '(16)'          : 16,
    '16++'          : ParseException,
    'case true then 1 end' : ParseException,
    'case true else 2 end' : ParseException,

    '1+4*5+-7'      : 1+4*5+-7,
    '(1+4)*(-5)+7'  : (1+4)*(-5)+7,
    '-7-7*-7/-3'    : -7-7*-7/-3,
    '(.2+1i)/(3.-1i)' : (.2+1j)/(3.-1j),
    '-2^3'          : -2**3,
    '-2E4^3.4E-5'   : -2E4**3.4E-5,
    '-.02E-4-13.4E-15*(-(-.02E-4+13.4E-15))' : -.02E-4-13.4E-15*(-(-.02E-4+13.4E-15)),
#    ' 15*-(1+1)'    :  15*-(1+1), # FAILS in Parser
    '-(2+3)^2'      : -(2+3)**2,
    '-2^-3'         : -2**-3,
    '-(3+2)^2-5^-2' : -(3+2)**2-5**-2,
    '-(4+2)^2+7^+2' : -(4+2)**2+7**+2,
    '(2+5)^2-7^+2'  : (2+5)**2-7**+2,
    '(2+-3)*-2/-2^-2' : (2+-3)*-2/-2**-2,
    '-(-1+-50)/-3*-5^(-2*-3)' : -(-1+-50)/-3*-5**(-2*-3),
    '16/4/2'        : 16/4/2,
    '16/4/2*2'      : 16/4/2*2,
    '16/4/(2*2)'    : 16/4/(2*2),
    '16/(2*4)/2'    : 16/(2*4)/2,
    '16/2*4/2'      : 16/2*4/2,
    'case true then 1 else 2 end' : 1,
    }

BOOLEAN_TERMS = {
    'true'                 : True,
    'false'                : False,
    'true or false'        : True,
    'true and false'       : False,
    'not true and false'   : False,
    'true and not false'   : True,
    '1+1 < 2+2'            : True,
    '1 in (3,4)'           : False,
    '3 in [3,4)'           : True,
    '3 in [2*1+1,3^1+2-1)' : True,
    }

PY_ARITHMETIC_TERMS = {
    '16++'            : ParseException,
    'case True then 1 else 2 end' : ParseException,

    '16'              : 16,
    '(16)'            : 16,
    '1+4*5+-7'        : 1+4*5+-7,
    '(1+4)*(-5)+7'    : (1+4)*(-5)+7,
    '-7-7*-7/-3'      : -7-7*-7/-3,
    '(.2+1j)/(3.-1j)' : (.2+1j)/(3.-1j),
    '2**3'            : 2**3,
    '1*2**3'          : 1*2**3,
    '-2E4**3.4E-5'    : -2E4**3.4E-5,
    }

PY_BOOLEAN_TERMS = {
    'true and false'          : None, # parsed as identifiers, not bool!
    'True or False'           : True,
    'True and False'          : False,
    '1+1 < 2+2'               : True,
    '1 in range(3,4)'         : False,
    '3 in xrange(3*2+1)'      : True,
    }


TERMS = {
    'infix_term'  : ARITHMETIC_TERMS,
    'infix_bool'  : BOOLEAN_TERMS,
    'python_term' : PY_ARITHMETIC_TERMS,
    'python_bool' : PY_BOOLEAN_TERMS
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

    return chain(pyeval( (term_type, term), (term_type.replace('python', 'infix'), infix) ),
                 [eval(pyterm)])


def dom_test(term, term_type, mathdom):
    doc = mathdom.fromString(term, term_type)
    infix  = serialize_dom(doc, 'infix')
    pyterm = serialize_dom(doc, 'python')

    return chain(pyeval( (term_type, term), (term_type.replace('python', 'infix'), infix) ),
                 [eval(pyterm)])

###

def build_test_class(term_type, terms, mathdom):
    impl_name  = mathdom.__module__.rsplit('.', 1)[-1]
    class_name = impl_name + '_' + term_type

    def docstr(test_name, term):
        return "%-8s - %-9s - %s: %s" % (impl_name, test_name, class_name.replace('_', ' '), term)

    def build_term_test_method(test_method, term, result):
        if isinstance(result, types.ClassType) and issubclass(result, Exception):
            def test(self):
                self.assertRaises(result, test_method, term, term_type, mathdom)
        else:
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
            if hasattr(element, 'value'):
                value = eval(term)
                self.assertEquals(element.value(), value)
            elif element.mathtype() == 'apply':
                self.assert_(element.firstChild.mathtype() in ALL_OPERATORS,
                             element.firstChild.mathtype())
            else:
                self.assert_(element.mathtype() in ('piecewise', 'true', 'false', 'imaginaryi', 'exponentiale'))
        test.__doc__ = docstr("dom_work", term)
        return test

    def build_output_test(term, output_type):
        def test(self):
            doc = mathdom.fromString(term, term_type)
            result = doc.serialize(output_type)
            if hasattr(result, 'write'):
                xml_out = StringIO()
                result.write(xml_out, 'UTF-8')
                result = xml_out.getvalue()
            self.assert_(result, type(result))
        test.__doc__ = docstr(output_type, term)
        return test

    def build_validate_test(term):
        if not hasattr(mathdom, 'validate'):
            return None
        def test(self):
            doc = mathdom.fromString(term, term_type)
            self.assert_(doc.validate())
        test.__doc__ = docstr("validate", term)
        return test

    def build_xslt_serialize_test(term):
        if not hasattr(mathdom, 'xsltify'):
            return None
        from lxml import etree
        stylesheet = etree.XSLT(etree.ElementTree(etree.XML('''
        <xsl:stylesheet version="1.0"
             xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
             xmlns:math="http://www.w3.org/1998/Math/MathML">
          <xsl:output method="text" encoding="UTF-8"/>
          <xsl:template match="math:math">
            <xsl:value-of select="math:serialize(., \'python\')" />
          </xsl:template>
        </xsl:stylesheet>
        ''')))
        def test(self):
            doc = etree.ElementTree(mathdom.fromString(term, term_type).getroot())
            pyterm = str( stylesheet(doc) )
            self.assertEquals(pyeval( (term_type, term) ).next(), eval(pyterm))
        test.__doc__ = docstr("xslt_ext", term)
        return test

    def build_parser_test(term):
        def test(self):
            self.assertRaises(ParseException, mathdom.fromString, term, term_type)
        test.__doc__ = docstr('errors', term)
        return test

    next_test_name = ("test_%05d" % i for i in count()).next

    invalid_terms = sorted( term for (term, result) in terms.iteritems()
                            if isinstance(result, (types.ClassType, type)) )

    tests =  dict(
        (next_test_name(), build_parser_test(term))
         for term in invalid_terms
         )

    valid_terms = sorted( (term, result) for (term, result) in terms.iteritems()
                          if not isinstance(result, (types.ClassType, type)) )

    tests.update(
        (next_test_name(), build_term_test_method(test_method, term, result))
        for test_method in (ast_test, dom_test)
        for term, result in valid_terms
        )

    tests.update(
        (next_test_name(), test_builder(term))
        for test_builder in (build_dom_test_method, build_validate_test, build_xslt_serialize_test)
        for term, result in valid_terms
        )

    output_types = {
        'mathdom'  : ['mathml'],
        'lmathdom' : ['pmathml', 'pmathml2', 'mathml']
        }[impl_name]

    tests.update(
        (next_test_name(), build_output_test(term, output_type))
        for output_type in output_types
        for term, result in valid_terms
        )

    return type(class_name, (unittest.TestCase,), tests)


if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    args = sys.argv[1:]

    mathdom_impls = []
    try:
        if not args or 'mathdom' in args:
            from mathml.mathdom  import MathDOM as pyMathDOM
            mathdom_impls.append(pyMathDOM)
    except ImportError:
        pass
    try:
        if not args or 'lmathdom' in args:
            from mathml.lmathdom import MathDOM as lxMathDOM
            mathdom_impls.append(lxMathDOM)
    except ImportError:
        pass

    test_classes = starmap(build_test_class,
                           ( (term_type, terms, mathdom)
                             for mathdom in mathdom_impls
                             for term_type, terms in TERMS.iteritems()
                             )
                           )

    test_suite = unittest.TestSuite()
    test_suite.addTests(map(unittest.makeSuite, test_classes))

    unittest.TextTestRunner(verbosity=2).run(test_suite)
