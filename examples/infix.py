try:
    import psyco
    psyco.full()
except ImportError:
    pass

import sys
from itertools import imap

# Maybe we are still before installation?
sys.path.append('..')

from mathml.mathdom     import MathDOM
from mathml.termbuilder import tree_converters
from mathml.termparser  import *
from mathml.xmlterm     import *


def handle_term(term):
    print "ORIGINAL:"
    print term
    print

    doc = None
    for term_type in term_parsers.known_types():
        print "Trying to parse '%s' ..." % term_type,
        try:
            doc = MathDOM.fromString(term, term_type)
            print "done."
            break
        except ParseException, e:
            print "Parsing as %s failed: %s" % (term_type, unicode(e).encode('UTF-8'))

    if doc is None:
        print "The term is not parsable."
        sys.exit(0)


    print "MATHML:"
    doc.toMathml(indent=False)
    print "\n"

    root = doc.documentElement
    print "NUMBERS USED :", ', '.join(frozenset(imap(str, root.iternumbervalues())))
    print "NAMES USED   :", ', '.join(frozenset(e.name() for e in root.iteridentifiers()))
    print

    print "AST:"
    tree = dom_to_tree(doc)
    print tree
    print

    for output_type in tree_converters.known_types():
        converter = tree_converters[output_type]
        print "%s:" % output_type.upper().ljust(8), converter.build(tree)
        print

    if 'python' not in tree_converters.known_types():
        print "Importing pyterm converter ..."
        from mathml.utils import pyterm

        print "Building python term ..."
        print
        converter = tree_converters['python']
        print "PYTHON  :" , converter.build(tree)
        print


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '-':
        handle_term( sys.stdin.read() )
    else:
        while True:
            print "Please enter an infix term or leave empty to proceed with an example term. 'exit' exits"
            try:
                term = raw_input('# ')
            except EOFError:
                sys.exit(0)

            if term.strip() in ('exit', 'quit'):
                sys.exit(0)

            if not term:
                term = ".1*pi+2E-4*(1+3i)-5.6-6*-1/sin(-45.5E6*a.b) * CASE WHEN 3|12 THEN 1+3 ELSE e^(4*1) END + 1"
                term = "%(term)s = 1 or %(term)s > 5 and true" % {'term':term}

            handle_term(term)
