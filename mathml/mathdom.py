#!/usr/bin/python

__all__ = [ 'MathDOM' ]

import sys, new
from itertools import chain

from xml.dom import Node, getDOMImplementation
from xml.dom.Element import Element
from xml.dom.ext import Print, PrettyPrint
from xml.dom.ext.reader.Sax2 import Reader


from mathml           import MATHML_NAMESPACE_URI
from mathml.xmlterm   import SaxTerm, dom_to_tree, serialize_dom
from mathml.datatypes import Decimal, Complex, Rational, ENotation

TYPE_MAP = {
    'real'       : Decimal,
    'complex'    : Complex,
    'rational'   : Rational,
    'e-notation' : ENotation
    }


UNARY_ARITHMETIC_FUNCTIONS = u"""
factorial minus abs conjugate arg real imaginary floor ceiling
"""

UNARY_LOGICAL_FUNCTIONS    = u"""
not
"""

UNARY_ELEMENTARY_CLASSICAL_FUNCTIONS = u"""
sin cos tan sec csc cot sinh cosh tanh sech csch coth
arcsin arccos arctan arccosh arccot arccoth arccsc arccsch
arcsec arcsech arcsinh arctanh exp ln log
"""

BINARY_ARITHMETIC_FUNCTIONS = u"""
quotient divide minus power rem
"""

NARY_ARITHMETIC_FUNCTIONS = u"""
plus times max min gcd lcm
"""

NARY_STATISTICAL_FUNCTIONS = u"""
mean sdev variance median mode
"""

NARY_LOGICAL_FUNCTIONS = u"""
and or xor
"""

NARY_FUNCTIONAL_FUNCTION = u"""
compose
"""

BINARY_SET_CONTAINMENT = u"""
in notin
"""

CONSTANTS = u"""
pi ExponentialE ee ImaginaryI ii gamma infin infty true false NotANumber NaN
"""

##

UNARY_FUNCTIONS  = UNARY_ELEMENTARY_CLASSICAL_FUNCTIONS + \
                   UNARY_ARITHMETIC_FUNCTIONS + \
                   UNARY_LOGICAL_FUNCTIONS

BINARY_FUNCTIONS = BINARY_ARITHMETIC_FUNCTIONS + \
                   BINARY_SET_CONTAINMENT

NARY_FUNCTIONS   = NARY_ARITHMETIC_FUNCTIONS + \
                   NARY_STATISTICAL_FUNCTIONS + \
                   NARY_LOGICAL_FUNCTIONS + \
                   NARY_FUNCTIONAL_FUNCTION

##


METHODS_BY_ELEMENT_NAME = {}
def method_elements(element_names=u"", defined_in=u""):
    if defined_in:
        global_sources = globals()
        elements = frozenset(chain(
            element_names.split(),
            (name for s in defined_in.split() for name in global_sources[s].split())
            ))
    else:
        elements = frozenset(element_names.split())

    def register_function(function):
        new_function = (function.func_name, function)
        for element_name in elements:
            try:
                METHODS_BY_ELEMENT_NAME[element_name].append(new_function)
            except KeyError:
                METHODS_BY_ELEMENT_NAME[element_name] = [new_function]

    return register_function

# the same for all elements:
def register_method(function):
    new_function = (function.func_name, function)
    try:
        METHODS_BY_ELEMENT_NAME[None].append(new_function)
    except KeyError:
        METHODS_BY_ELEMENT_NAME[None] = [new_function]


class MathElement(Element):
    "Fake class containing methods for different MathML Element objects."
    @register_method
    def mathtype(self):
        return self.localName

    @register_method
    def has_type(self, name):
        return self.localName == name

    @register_method
    def iteridentifiers(self):
        return iter(self.getElementsByTagName(u'ci'))

    @register_method
    def iteridentifiernames(self):
        return (e.name() for e in self.getElementsByTagName(u'ci'))

    @register_method
    def iterconstants(self):
        return iter(self.getElementsByTagName(u'name'))

    @register_method
    def iterconstantnames(self):
        return (e.firstChild.data for e in self.getElementsByTagName(u'name'))

    @register_method
    def iternumbers(self):
        return iter(self.getElementsByTagName(u'cn'))

    @register_method
    def iternumbervalues(self):
        return iter(n.value() for n in self.getElementsByTagName(u'cn'))

    @register_method
    def iteroperators(self):
        return iter(e.firstChild for e in self.getElementsByTagName(u'apply'))

    @method_elements(u"apply")
    def operator(self):
        return self.firstChild

    @method_elements(u"apply")
    def operatorname(self):
        return self.firstChild.localName

    @method_elements(u"apply")
    def set_operator(self, new_operator):
        doc = self.ownerDocument
        if isinstance(new_operator, (str, unicode)):
            operator = doc.createElementNS(MATHML_NAMESPACE_URI, new_operator)
        else:
            operator = new_operator
        self.childNodes[:1] = [ operator ]

    @method_elements(u"apply")
    def operands(self):
        return self.childNodes[1:]

    @method_elements(u"apply")
    def operand_count(self):
        return len(self.childNodes) - 1

    @method_elements(u"apply")
    def append_operand(self, operand):
        if not self.childNodes:
            raise TypeError, "You must supply an operator first."
        self.childNodes.append(operand)

    @method_elements(u"apply ci cn")
    def to_tree(self):
        return dom_to_tree(self)

    @method_elements(u"apply ci cn")
    def serialize(self, *args, **kwargs):
        return serialize_dom(self, *args, **kwargs)

    @method_elements(defined_in="UNARY_FUNCTIONS")
    def operand(self):
        return self.firstChild

    @method_elements(u"minus")
    def is_negation(self):
        parent = self.parentNode
        children = parent.childNodes
        return len(children) == 2

    @method_elements(u"interval")
    def closure(self):
        return self.getAttribute(u'closure') or 'closed'


class MathValue(Element):
    "Fake class containing methods for handling constants, identifiers, etc."
    @method_elements(u"ci")
    def value(self):
        return self.firstChild

    @method_elements(u"ci name")
    def name(self):
        if hasattr(self.firstChild, 'data'):
            return self.firstChild.data
        elif hasattr(self.firstChild, 'localName'):
            return self.firstChild.localName
        else:
            return str(self.firstChild)

    @method_elements(u"cn")
    def value(self):
        "Returns the numerical value with the correct type."
        valuetype = self.valuetype()
        if valuetype == u'integer':
            return int(self.firstChild.data)
        elif valuetype == u'real':
            return Decimal(self.firstChild.data)

        try:
            typeclass = TYPE_MAP[valuetype]
            return typeclass(self.childNodes[0].data, self.childNodes[2].data)
        except KeyError:
            raise NotImplementedError, "Invalid data type."

    @method_elements(u"cn")
    def _set_tuple_value(self, typename, value_tuple):
        del self.childNodes[:]
        doc = self.ownerDocument
        appendChild = self.appendChild

        appendChild( doc.createTextNode(value_tuple[0]) )
        appendChild( doc.createElementNS(MATHML_NAMESPACE_URI, u'sep') )
        appendChild( doc.createTextNode(value_tuple[1]) )
        self.setAttribute(u'type', typename)

    @method_elements(u"cn")
    def set_value(self, value, type_name=None):
        if isinstance(value, complex):
            self.set_complex(value)
            return
        elif isinstance(value, Rational):
            self.set_rational(value)
            return
        elif type_name is None:
            try:
                type_name = value.TYPE_NAME
            except AttributeError:
                if isinstance(value, (int, long)):
                    type_name = u'integer'
                elif isinstance(value, float):
                    type_name = u'real'
                else:
                    raise TypeError, "Invalid value type. Please specify type name."
        doc = self.ownerDocument
        self.childNodes[:] = [ doc.createTextNode(unicode(value)) ]

    @method_elements(u"cn")
    def set_complex(self, value):
        try:
            tuple_value = (value.real_str, value.imag_str)
        except AttributeError:
            tuple_value = (unicode(value.real), unicode(value.imag))
        self._set_tuple_value(u'complex', tuple_value)

    @method_elements(u"cn")
    def set_rational(self, *value):
        value = Rational(*value)
        self._set_tuple_value(u'rational', (value.num_str, value.denom_str))

    @method_elements(u"cn")
    def valuetype(self):
        typeattr = self.getAttribute(u'type')
        if typeattr:
            return typeattr
        elif len(self.childNodes) == 1:
            value = self.firstChild.data
            for type_test, name in ((int, u'integer'), (float, u'real')):
                try:
                    type_test(value)
                    return name
                except ValueError:
                    pass
        else:
            return u'real' # MathML default!

    @method_elements(u"cn")
    def __repr__(self):
        name = self.localName
        return u"<%s type='%s'>%r</%s>" % (name, self.getAttribute('type') or 'real', self.value(), name)

    @method_elements(u"ci")
    def __repr__(self):
        name = self.localName
        return u"<%s>%r</%s>" % (name, self.firstChild, name)


# add qualifiers as attributes to standard DOM classes
DEFAULT_DICT = {}
def setupDefaults():
    dom_impl = getDOMImplementation()
    doc = dom_impl.createDocument(MATHML_NAMESPACE_URI, u"apply", None)

    logbase = doc.createElementNS(MATHML_NAMESPACE_URI, u'cn')
    logbase.appendChild( doc.createTextNode(u'10') )
    DEFAULT_DICT['logbase'] = logbase

setupDefaults()

class Qualifier(object):
    def __init__(self, name, valid_elements):
        self.name = name
        if isinstance(valid_elements, (str, unicode)):
            valid_elements = valid_elements.split()
        self.valid_elements = frozenset(valid_elements)
        self.__ACCESS_ERROR = "This element does not support the qualifier %s" % name

    def __find_qualifier(self, node):
        parent = node.parentNode
        if parent:
            ELEMENT_NODE = node.ELEMENT_NODE
            name = self.name
            for child in parent.childNodes:
                if child.nodeType == ELEMENT_NODE and child.localName == name:
                    return child
        return None

    def __get__(self, node, owner):
        if node is None:
            return self
        if node.localName not in self.valid_elements:
            raise NotImplementedError, self.__ACCESS_ERROR

        qualifier_node = self.__find_qualifier(node)
        if qualifier_node:
            return qualifier_node.firstChild
        else:
            return DEFAULT_DICT[self.name].cloneNode(True)

    def __set__(self, node, value):
        if node.localName not in self.valid_elements:
            raise NotImplementedError, self.__ACCESS_ERROR

        qualifier_node = self.__find_qualifier(node)
        if qualifier_node:
            for child in reversed(tuple(qualifier_node.children)):
                qualifier_node.removeChild(child)
        else:
            qualifier_node = node.ownerDocument.createElement(self.name)
            parent = node.parentNode
            parent.appendChild(qualifier_node)
        qualifier_node.appendChild(value)

Element.logbase = Qualifier('logbase', u'log')


class MathDOM(object):
    def __init__(self, document):
        self.__augmentElements(document)
        self._document = document

    def __augmentElements(self, node):
        "Weave methods into DOM Element objects."
        if node.nodeType == node.ELEMENT_NODE:
            element_methods = METHODS_BY_ELEMENT_NAME.get(node.localName, ())
            common_methods  = METHODS_BY_ELEMENT_NAME.get(None, ())
            node_class = node.__class__
            for method_name, method in chain(element_methods, common_methods):
                new_method = new.instancemethod(method, node, node_class)
                setattr(node, method_name, new_method)

        for child in tuple(node.childNodes):
            if child.nodeType == Node.TEXT_NODE:
                if not child.data.strip():
                    node.removeChild(child)
                    continue
            else:
                self.__augmentElements(child)

    @staticmethod
    def __build_sax_reader(input_type):
        if input_type == 'mathml':
            return Reader()
        else:
            sax_class = SaxTerm.for_input_type(input_type)
            return Reader(parser=sax_class())

    @classmethod
    def fromSax(cls, input, sax_parser):
        dom_builder = Reader(parser=sax_parser)
        return cls( dom_builder.fromString(input) )

    @classmethod
    def fromString(cls, input, input_type='mathml'):
        dom_builder = cls.__build_sax_reader(input_type)
        return cls( dom_builder.fromString(input) )

    @classmethod
    def fromStream(cls, input, input_type='mathml'):
        dom_builder = cls.__build_sax_reader(input_type)
        return cls( dom_builder.fromStream(input) )

    def __getattr__(self, name):
        return getattr(self._document, name)

    def __repr__(self):
        return repr(self._document)

    def toMathml(self, out=None, indent=False):
        if out is None:
            out = sys.stdout
        if indent:
            PrettyPrint(self._document, out)
        else:
            Print(self._document, out)

    # new DOM methods:

    def createApply(self, name, *args):
        create_element = self._document.createElementNS
        apply_tag = create_element(MATHML_NAMESPACE_URI, u'apply')
        function_tag = create_element(MATHML_NAMESPACE_URI, name)
        apply_tag.appendChild(function_tag)
        augmentElements(apply_tag)
        if args:
            function_tag.childNodes[:] = args
        return apply_tag

    def createFunction(self, name, *args):
        create_element = self._document.createElementNS
        apply_tag = create_element(MATHML_NAMESPACE_URI, u'apply')
        function_tag = create_element(MATHML_NAMESPACE_URI, name)
        apply_tag.appendChild(function_tag)
        augmentElements(apply_tag)
        if args:
            function_tag.childNodes[:] = args
        return apply_tag

    def createConstant(self, value):
        create_element = self._document.createElementNS
        cn_tag = create_element(MATHML_NAMESPACE_URI, u'cn')
        cn_tag.set_value(value)
        return cn_tag
