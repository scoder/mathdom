import unittest

try:
    from mathml import mathdom
except ImportError:
    mathdom = None

try:
    from mathml import lmathdom
except ImportError:
    lmathdom = None


def mathdom_test(function, module):
    if module is None:
        return None
    else:
        def new_function(self):
            function(self, module, module.MathDOM())
        new_function.__name__ = function.__name__
        new_function.__doc__  = function.__doc__
        new_function.__dict__ = function.__dict__
        return new_function

def for_mathdom(function):
    return mathdom_test(function, mathdom)

def for_lmathdom(function):
    return mathdom_test(function, lmathdom)


class MathdomTestCase(unittest.TestCase):
    @for_mathdom
    def test_math(self, mathdom, doc):
        self.assertEquals( doc.firstChild.localName,
                           'math' )
    @for_lmathdom
    def test_lmath(self, lmathdom, doc):
        self.assertEquals( doc.getroot().localName,
                           'math' )

    @for_mathdom
    def test_create_constant(self, mathdom, doc):
        c = doc.createConstant(3)
        self.assertEquals(c.serialize('infix'),
                          '3')
    @for_lmathdom
    def test_lcreate_constant(self, lmathdom, doc):
        c = doc.createConstant(3)
        self.assertEquals(c.serialize('infix'),
                          '3')


    @for_mathdom
    def test_constant(self, mathdom, doc):
        c = mathdom.Constant(doc, 3)
        self.assertEquals(doc.serialize('infix'),
                          '3')
    @for_lmathdom
    def test_lconstant(self, lmathdom, doc):
        c = lmathdom.Constant(doc, 3)
        self.assertEquals(doc.serialize('infix'),
                          '3')


    @for_mathdom
    def test_create_identifier(self, mathdom, doc):
        i = doc.createIdentifier('bla')
        self.assertEquals(i.serialize('infix'),
                          'bla')
    @for_lmathdom
    def test_lcreate_identifier(self, lmathdom, doc):
        i = doc.createIdentifier('bla')
        self.assertEquals(i.serialize('infix'),
                          'bla')


    @for_mathdom
    def test_identifier(self, mathdom, doc):
        i = mathdom.Identifier(doc, 'bla')
        self.assertEquals(doc.serialize('infix'),
                          'bla')
    @for_lmathdom
    def test_lconstant(self, lmathdom, doc):
        i = lmathdom.Identifier(doc, 'bla')
        self.assertEquals(doc.serialize('infix'),
                          'bla')


    @for_mathdom
    def test_create_apply(self, mathdom, doc):
        c = map(doc.createConstant, (1,2,3))
        a = doc.createApply('plus', c)
        self.assertEquals(a.serialize('infix'),
                          '1 + 2 + 3')
    @for_lmathdom
    def test_lcreate_apply(self, lmathdom, doc):
        c = map(doc.createConstant, (1,2,3))
        a = doc.createApply('plus', c)
        self.assertEquals(a.serialize('infix'),
                          '1 + 2 + 3')


    @for_mathdom
    def test_apply(self, mathdom, doc):
        c = map(doc.createConstant, (1,2,3))
        a = mathdom.Apply(doc, 'plus', c)
        self.assertEquals(doc.serialize('infix'),
                          '1 + 2 + 3')
    @for_lmathdom
    def test_lapply(self, lmathdom, doc):
        c = map(doc.createConstant, (1,2,3))
        a = lmathdom.Apply(doc, 'plus', c)
        self.assertEquals(doc.serialize('infix'),
                          '1 + 2 + 3')


if __name__ == '__main__':
    unittest.main()
