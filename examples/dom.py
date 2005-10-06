import sys
from itertools import imap

try:
    from xml import xpath
    HAS_XPATH = True
except ImportError:
    HAS_XPATH = False

try:
    raise ImportError
    from mathml.mathdom     import MathDOM
    from mathml.termbuilder import tree_converters
    from mathml.termparser  import *
    from mathml.xmlterm     import *
except ImportError:
    # Maybe we are still before installation?
    sys.path.append('src')
    sys.path.append('../src')

    from mathdom     import MathDOM
    from termbuilder import tree_converters
    from termparser  import *
    from xmlterm     import *

print "Please enter an infix term or leave empty to proceed with an example term."
try:
    term = raw_input('# ')
except EOFError:
    sys.exit(0)

if not term:
    term = ".1*pi+2E-4*(1+3i)-5.6-6*-1/sin(-45.5E6*a.b) * CASE WHEN 3|12 THEN 1+3 ELSE e^(4*1) END + 1"
    term = "%(term)s = 1 or %(term)s > 5 and true" % {'term':term}


print "ORIGINAL:"
print term
print

doc = None
for parser in (BoolExpressionSaxParser, TermSaxParser, TermListSaxParser):
    try:
        doc = MathDOM.fromMathmlSax(term, parser())
    except ParseException, e:
        print "Parsing with %s failed: %s" % (parser.__name__, unicode(e).encode('UTF-8'))

if doc is None:
    print "The term is not parsable."
    sys.exit(0)

infix_converter = tree_converters['infix']

def write_infix():
    tree = dom_to_tree(doc)
    print "SERIALIZED:", infix_converter.build(tree)

print "MathML parsing done."
write_infix()

print
print "Exchanging '+' and '-' ..."
for apply_tag in doc.getElementsByTagName(u'apply'):
    operator = apply_tag.operatorname()
    if operator == u'plus':
        apply_tag.set_operator(u'minus')
    elif operator == u'minus' and apply_tag.operand_count() > 1:
        apply_tag.set_operator(u'plus')
write_infix()

if HAS_XPATH:
    print
    print "Searching for negative numbers using XPath expression '//cn[number() < 0]' ..."
    for cn_tag in xpath.Evaluate('//cn[number() < 0]', doc.documentElement):
        value = cn_tag.value()
        print "%s [%s]" % (value, type(value))
else:
    print "XPath not installed. Skipping test."

print 'Done.'
