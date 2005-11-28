#!/usr/bin/python
# -*- coding: utf-8 -*-

__doc__ = """
Implementation of a SAX parser for the AST defined in the
mathml.termparser module.

Usage examples:
(remember to run 'from mathml import mathdom, xmlterm, termparser' first!)

* Building a MathDOM document from a boolean expression in infix notation:

>>> from mathdom import MathDOM
>>> from xmlterm import SaxTerm
>>> term = 'pi*(1+.3i) + 1'
>>> bool_term = '%(term)s = 1 or %(term)s > 5 and true' % {'term':term}
>>> doc = MathDOM.fromSax(bool_term, SaxTerm.for_input_type('infix_bool')())
>>> # or use this shortcut:
>>> doc = MathDOM.fromString(bool_term, 'infix_bool')
>>> doc.toMathml(indent=True)
<?xml version='1.0' encoding='UTF-8'?>
<apply xmlns='http://www.w3.org/1998/Math/MathML'>
  <or/>
  <apply>
    <eq/>
    <apply>
      <plus/>
      <apply>
        <times/>
        <pi/>
        <cn type='complex'>1<sep/>0.3</cn>
      </apply>
      <cn type='integer'>1</cn>
    </apply>
    <cn type='integer'>1</cn>
  </apply>
  <apply>
    <and/>
    <apply>
      <gt/>
      <apply>
        <plus/>
        <apply>
          <times/>
          <pi/>
          <cn type='complex'>1<sep/>0.3</cn>
        </apply>
        <cn type='integer'>1</cn>
      </apply>
      <cn type='integer'>5</cn>
    </apply>
    <true/>
  </apply>
</apply>


* Generating an AST from the DOM and converting it to infix notation:

>>> from xmlterm import dom_to_tree
>>> from termbuilder import tree_converters
>>> ast = dom_to_tree(doc)
>>> ast
[u'or', ['=', ['+', ['*', [u'name', u'pi'], [u'const:complex', Complex(1+0.3j)]], [u'const:integer', 1]], [u'const:integer', 1]], [u'and', ['>', ['+', ['*', [u'name', u'pi'], [u'const:complex', Complex(1+0.3j)]], [u'const:integer', 1]], [u'const:integer', 5]], [u'const:bool', True]]]
>>> converter = tree_converters['infix']
>>> converter.build(ast)
u'pi * (1+0.3i) + 1 = 1 or pi * (1+0.3i) + 1 > 5 and true'
"""

__all__ = ('dom_to_tree', 'serialize_dom', 'SaxTerm')

try:
    from psyco.classes import *
except ImportError:
    pass

from itertools import *
from xml.sax.xmlreader import XMLReader, AttributesNSImpl
from xml.sax.handler import feature_namespaces

from mathml             import MATHML_NAMESPACE_URI
from mathml.termparser  import term_parsers
from mathml.termbuilder import tree_converters


def mkstr(value):
    if isinstance(value, (str, unicode)):
        return value
    else:
        return unicode(str(value), 'ascii')


_ELEMENT_CONSTANT_MAP = {
    u'true'  : u'true',
    u'false' : u'false',
    u'pi'    : u'pi',
    u'i'     : u'imaginaryi',
    u'e'     : u'exponentiale'
    }

_FUNCTION_MAP = {
    '+' : u'plus',
    '-' : u'minus',
    '*' : u'times',
    '/' : u'divide',
    '%' : u'rem',
    '^' : u'power',
    '|' : u'factorof',
    '=' : u'eq',
    '<>': u'neq',
    '!=': u'neq',
    '>' : u'gt',
    '>=': u'geq',
    '<=': u'leq',
    '<' : u'lt',
    }


# main module functions:

# OUTPUT:

def serialize_dom(doc_or_element, output_format=None, converter=None):
    """Serialize a MathDOM document into a term.

    You can specify either a converter or an output format. If neither
    of the two is given, it defaults to the 'infix' converter.
    """
    if output_format is None:
        output_format = 'infix'
    if converter is None:
        converter = tree_converters.fortype(output_format)
        if converter is None:
            raise ValueError, "Unsupported output format '%s'" % output_format
    tree = dom_to_tree(doc_or_element)
    return converter.build(tree)


def dom_to_tree(doc_or_element):
    "Convert a MathDOM document or element into its AST representation."
    map_operator = dict((v,n) for (n,v) in _FUNCTION_MAP.iteritems()).get
    map_constant = dict((v,n) for (n,v) in _ELEMENT_CONSTANT_MAP.iteritems()).get
    def _recursive_piecewise(piecewise):
        "piecewise -> [ case, p1cond, p1value, [ case, p2cond, p2val, [ ... , otherwise ]]]"
        def _piece_to_case(piece):
            children = piece.childNodes
            if len(children) != 2:
                raise NotImplementedError, u"piece element has %d children, 2 allowed" % len(children)
            value, condition = map(_recursive_dom_to_tree, children)
            return [ u'case', condition, value ]

        otherwise = None
        case = []
        last_case = case
        for piece in piecewise:
            name = piece.localName
            if name == u'piece':
                new_case = _piece_to_case(piece)
                last_case.append(new_case)
                last_case = new_case
            elif name == u'otherwise':
                otherwise = _recursive_dom_to_tree(piece.firstChild)
            else:
                raise NotImplementedError, u"Unknown element in piecewise: %s" % name
        if otherwise:
            if last_case:
                last_case.append(otherwise)
            else:
                return otherwise
        return case[0]

    def _recursive_dom_to_tree(element):
        mtype = element.mathtype()

        constant = map_constant(mtype)
        if constant:
            if constant in (u'true', u'false'):
                return [ u'const:bool', constant == u'true' ]
            else:
                return [ u'name', constant ]
        elif mtype == u'ci':
            return [ u'name', element.name() ]
        elif mtype == u'cn':
            return [ u'const:%s' % element.valuetype().replace('-', ''), element.value() ]
        elif mtype == u'apply':
            operator = element.operator()
            if operator.childNodes:
                raise NotImplementedError, u"function composition is not supported"
            name = operator.mathtype()

            operands = map(_recursive_dom_to_tree, element.operands())
            operands.insert(0, map_operator(name, name))
            return operands
        elif mtype == u'piecewise':
            return _recursive_piecewise(element)
        elif mtype == u'list':
            list_items = map(_recursive_dom_to_tree, element)
            list_items.insert(0, mtype)
            return list_items
        elif mtype == u'interval':
            list_items = map(_recursive_dom_to_tree, element)
            list_items.insert(0, '%s:%s' % (mtype, element.closure()))
            return list_items
        else:
            raise NotImplementedError, u"%s elements are not supported" % mtype

    try:
        root = doc_or_element.documentElement
    except AttributeError:
        try:
            root = doc_or_element.getroot()
        except AttributeError:
            root = doc_or_element

    if root.mathtype() == u'math':
        root = root.firstChild
    tree = _recursive_dom_to_tree(root)
    if not isinstance(tree, list):
        return [ tree ]
    else:
        return tree


# INPUT:

class SaxTerm(XMLReader):
    """AST reader that outputs SAX events.

    For converting AST trees, just call tree_to_sax.

    For parsing literal terms, you may either call parse_term directly
    or use the for_input_type class method to retrieve a sax reader
    class.  The latter can be used as input source to any SAX parser.
    """

    __SAX_READERS = {}

    NO_ATTR = AttributesNSImpl({}, {})
    map_operator = _FUNCTION_MAP.get
    map_constant = _ELEMENT_CONSTANT_MAP.get

    def __init__(self, sax_parser=None):
        XMLReader.__init__(self)
        if sax_parser:
            self.setContentHandler(sax_parser)

    def setContentHandler(self, sax_parser):
        XMLReader.setContentHandler(self, sax_parser)
        self.parser = sax_parser

    def setFeature(self, name, value):
        if name == feature_namespaces:
            assert value
        else:
            XMLReader.setFeature(self, name, value)

    @classmethod
    def for_input_type(cls, input_type):
        "Returns a SAX reader class for parsing terms of type input_type."
        try:
            return cls.__SAX_READERS[(cls, input_type)]
        except KeyError:
            pass

        class SaxGenerator(cls):
            def parse(self, term):
                self.parse_term(term, input_type)

        cls.__SAX_READERS[(cls, input_type)] = SaxGenerator
        return SaxGenerator

    def parse_term(self, expression, input_type):
        if hasattr(expression, 'getCharacterStream'): # InputSource?
            stream = expression.getCharacterStream()
            if stream:
                expression = stream
            else:
                expression = expression.getByteStream()
        if hasattr(expression, 'read'): # StringIO?
            expression = expression.read()

        term_parser = term_parsers[input_type]
        self.tree_to_sax( term_parser.parse(expression) )

    def tree_to_sax(self, tree):
        parser = self.parser
        parser.startDocument()
        parser.startPrefixMapping(None, MATHML_NAMESPACE_URI)

        self._open_tag(u'math')
        self._recursive_tree_to_sax(tree)
        self._close_tag(u'math')

        parser.endPrefixMapping(None)
        parser.endDocument()

    def _attributes(self, **attributes):
        values, qnames = {}, {}
        for name, value in attributes.iteritems():
            name = unicode(name)
            ns_name = (None, name)
            qnames[ns_name] = name
            values[ns_name] = value

        return AttributesNSImpl(values, qnames)

    def _recursive_tree_to_sax(self, tree):
        operator = tree[0]
        mapped_operator = self.map_operator(operator)
        if mapped_operator:
            self._send_function(mapped_operator, tree)
        elif operator == u'name':
            name = mkstr(tree[1])
            constant = self.map_constant(name)
            if constant:
                self._write_element(constant)
            else:
                self._write_element(u'ci', name)
        elif operator.startswith(u'const:'):
            if operator == u'const:bool':
                self._write_element(tree[1] and u'true' or u'false')
            elif operator in (u'const:complex', u'const:rational'):
                self._send_bin_constant(operator[6:], tree[1])
            elif operator == u'const:enotation':
                self._send_bin_constant('e-notation', tree[1])
            else:
                self._write_element(u'cn', mkstr(tree[1]),
                                    self._attributes(type=operator[6:]))
        elif operator == u'case':
            self._send_case(tree)
        elif operator[:4] == u'list':
            self._send_list(tree, u'list', self.NO_ATTR)
        elif operator[:9] == u'interval:':
            closure = self._attributes(closure=operator[9:] or 'closed')
            self._send_list(tree, u'interval', closure)
        else:
            self._send_function(operator, tree)

    def _send_bin_constant(self, typename, value):
        try:
            parts = tuple(value)
        except:
            raise NotImplementedError, "Only MathDOM types are constant pairs."

        parts = map(mkstr, parts)

        parser  = self.parser
        self._open_tag(u'cn', self._attributes(type=typename))
        parser.characters(parts[0])
        self._write_element(u'sep')
        parser.characters(parts[1])
        self._close_tag(u'cn')

    def _send_case(self, tree):
        el_open  = self._open_tag
        el_close = self._close_tag
        tree_to_sax = self._recursive_tree_to_sax

        el_open(u'piecewise', self.NO_ATTR)

        el_open(u'piece', self.NO_ATTR)
        tree_to_sax(tree[2])
        tree_to_sax(tree[1])
        self._close_tag(u'piece')

        if len(tree) > 3:
            el_open(u'otherwise', self.NO_ATTR)
            tree_to_sax(tree[3])
            el_close(u'otherwise')

        el_close(u'piecewise')

    def _send_list(self, tree, list_type, attributes):
        tree_to_sax = self._recursive_tree_to_sax

        self._open_tag(list_type, attributes)
        for elem in islice(tree, 1, None):
            tree_to_sax(elem)
        self._close_tag(list_type)

    def _send_function(self, fname, tree):
        self._open_tag(u'apply', self.NO_ATTR)
        self._write_element(fname)

        tree_to_sax = self._recursive_tree_to_sax
        for elem in islice(tree, 1, None):
            tree_to_sax(elem)

        self._close_tag(u'apply')

    def _open_tag(self, name, attr=NO_ATTR):
        self.parser.startElementNS( (MATHML_NAMESPACE_URI, name), name, attr )

    def _close_tag(self, name):
        self.parser.endElementNS( (MATHML_NAMESPACE_URI, name), name )

    def _write_element(self, name, content=None, attr=NO_ATTR):
        parser = self.parser
        tag = (MATHML_NAMESPACE_URI, name)

        parser.startElementNS(tag, name, attr)
        if content:
            parser.characters(content)
        parser.endElementNS(tag, name)


try:
    import sys
    from optimize import bind_all
    bind_all(sys.modules[__name__])
    del sys, bind_all
except:
    pass


if __name__ == '__main__':
    import doctest
    doctest.testmod()
