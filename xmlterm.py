#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Implementation of SAX parser for infix terms.
"""

__all__ = ('BoolExpressionSaxParser', 'TermSaxParser', 'dom_to_tree')

try:
    from psyco.classes import *
except ImportError:
    pass

from itertools import *
from xml.sax.xmlreader import XMLReader, AttributesNSImpl
from xml.sax.handler import feature_namespaces

from mathdom import MATHML_NAMESPACE_URI
from termparser import parse_bool_expression, parse_term

def mkstr(value):
    if isinstance(value, (str, unicode)):
        return value
    else:
        return unicode(str(value), 'ascii')


_ELEMENT_CONSTANT_MAP = {
    'true'  : 'true',
    'false' : 'false',
    'pi'    : 'pi',
    'i'     : 'imaginaryi',
    'e'     : 'exponentiale'
    }

_FUNCTION_MAP = {
    '+' : u'plus',
    '-' : u'minus',
    '*' : u'times',
    '/' : u'divide',
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

class SaxTerm(XMLReader):
    NO_ATTR = AttributesNSImpl({}, {})
    map_operator = _FUNCTION_MAP.get
    map_constant = _ELEMENT_CONSTANT_MAP.get

    def __init__(self, sax_parser=None):
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

    def tree_to_sax(self, tree):
        parser = self.parser
        parser.startDocument()
        parser.startPrefixMapping(None, MATHML_NAMESPACE_URI)
        self._recursive_tree_to_sax(tree)
        parser.endPrefixMapping(None)
        parser.endDocument()

    def _attribute(self, name, value):
        attr = (None, name)
        return AttributesNSImpl( {attr : value}, {attr : name} )

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
                self._write_element((tree[1] == u'true') and u'true' or u'false')
            else:
                self._write_element(u'cn', mkstr(tree[1]),
                                    self._attribute(u'type', operator[6:]))
        elif operator == 'case':
            self._send_case(tree)
        else:
            self._send_function(operator, tree)

    def _send_case(self, tree):
        parser = self.parser
        el_open  = parser.startElementNS
        el_close = parser.endElementNS
        tree_to_sax = self._recursive_tree_to_sax

        piecewise_tag = (MATHML_NAMESPACE_URI, u'piecewise')

        el_open(piecewise_tag, u'piecewise', self.NO_ATTR)

        piece_tag = (MATHML_NAMESPACE_URI, u'piece')
        el_open(piece_tag, u'piece', self.NO_ATTR)
        tree_to_sax(tree[2])
        tree_to_sax(tree[1])
        el_close(piece_tag, u'piece')

        if len(tree) > 3:
            otherwise_tag = (MATHML_NAMESPACE_URI, u'otherwise')
            el_open(otherwise_tag, u'otherwise', self.NO_ATTR)
            tree_to_sax(tree[3])
            el_close(otherwise_tag, u'otherwise')

        el_close(piecewise_tag, u'piecewise')

    def _send_function(self, fname, tree):
        parser = self.parser
        apply_tag = (MATHML_NAMESPACE_URI, u'apply')

        parser.startElementNS(apply_tag, u'apply', self.NO_ATTR)
        self._write_element(fname)

        tree_to_sax = self._recursive_tree_to_sax
        for elem in islice(tree, 1, None):
            tree_to_sax(elem)

        parser.endElementNS(apply_tag, u'apply')

    def _write_element(self, name, content=None, attr=NO_ATTR):
        parser = self.parser
        tag = (MATHML_NAMESPACE_URI, name)

        parser.startElementNS(tag, name, attr)
        if content:
            parser.characters(content)
        parser.endElementNS(tag, name)


def dom_to_tree(doc):
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
        for piece in piecewise.childNodes:
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
            return [ u'name', constant ]
        elif mtype == u'ci':
            return [ u'name', element.firstChild.data ]
        elif mtype == u'cn':
            value = element.firstChild.data
            value_type = element.getAttribute('type')
            if value_type:
                return [ u'const:%s' % value_type, value ]
            else:
                return value
        elif mtype == u'apply':
            operator = element.firstChild
            if operator.childNodes:
                raise NotImplementedError, u"function composition is not supported"
            name = operator.localName

            operands = filter(None, imap(_recursive_dom_to_tree, islice(element.childNodes,1,None)))
            operands.insert(0, map_operator(name, name))
            return operands
        elif mtype == u'piecewise':
            return _recursive_piecewise(element)
        else:
            raise NotImplementedError, u"%s elements are not supported" % mtype

    tree = _recursive_dom_to_tree(doc.documentElement)
    if not isinstance(tree, list):
        return [ tree ]
    else:
        return tree


# main module functions:

class BoolExpressionSaxParser(SaxTerm):
    def parse(self, expression):
        if hasattr(expression, 'getCharacterStream'): # InputSource?
            stream = expression.getCharacterStream()
            if not stream:
                expression = expression.getByteStream()
        if hasattr(expression, 'read'): # StringIO?
            expression = expression.read()
        self.tree_to_sax( parse_bool_expression(expression) )

class TermSaxParser(SaxTerm):
    def parse(self, term):
        if hasattr(expression, 'getCharacterStream'): # InputSource?
            stream = expression.getCharacterStream()
            if not stream:
                expression = expression.getByteStream()
        if hasattr(term, 'read'): # StringIO?
            term = term.read()
        self.tree_to_sax( parse_term(term) )

def expression_to_sax(expression, parser):
    tree_to_sax(parse_bool_expression(expression), parser)

def term_to_sax(term, parser):
    tree_to_sax(parse_term(term), parser)

def tree_to_sax(tree, parser):
    saxer = SaxTerm(parser)
    saxer.tree_to_sax(tree)


if __name__ == '__main__':
    term = ".1*pi+2*3-5.6-6*-1/sin(-45*a.b) * CASE WHEN 3|12 THEN 1+3 ELSE e^(4*1) END + 1"
    bool_term = "%(term)s = 1 or %(term)s > 5 and true" % {'term':term}

    print "ORIGINAL:"
    print bool_term

    from mathdom import MathDOM
    doc = MathDOM.fromMathmlSax(bool_term, BoolExpressionSaxParser())
    print
    print "MATHML:"
    doc.toMathml(indent=True)

    try:
        from termparser import infixof
        print
        print "AST:"
        print dom_to_tree(doc)

        print
        print "INFIX:"
        print infixof( dom_to_tree(doc) )
    except ImportError:
        pass
