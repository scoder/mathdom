#!/usr/bin/python

__all__ = [ 'MathDOM', 'Apply', 'Constant', 'Identifier', 'Name',
            'Qualifier', 'Element', 'SubElement', 'SiblingElement' ]

__doc__ = """
ElementTree/lxml based implementation of MathDOM.

This module depends on the C extension lxml, which in turn requires
libxml2 and libxslt.  Use this if you want a simple API, MathML
validation and XSLT support.

The main class is MathDOM.  It supports parsing and serializing MathML
and several other term representations.

Apart from the regular ElementTree/lxml API, the special functions
Apply, Identifier and Constant create new 'math:apply', 'math:ci' and
'math:cn' tags under a given parent like this:

>>> from mathml.lmathdom import MathDOM, Apply, Identifier, Constant
>>> doc = MathDOM.fromString('a+3*(4+5)', 'infix_term')
>>> for apply_tag in doc.xpath('//math:apply[math:plus]'): # add 1 to every sum
...     c = Constant(apply_tag, 1, 'integer')
>>> doc.serialize('infix')
u'a + 3 * ( 4 + 5 + 1 ) + 1'

"""

import sys
from StringIO import StringIO

from lxml import etree as _etree
from lxml.etree import SubElement, ElementTree
from lxml.sax import ElementTreeContentHandler

from mathml           import MATHML_NAMESPACE_URI, UNARY_FUNCTIONS
from mathml.xmlterm   import SaxTerm, dom_to_tree, serialize_dom
from mathml.datatypes import Decimal, Complex, Rational, ENotation

from mathml.utils     import STYLESHEETS as UTILS_STYLESHEETS
from mathml.schema    import SCHEMAS

TYPE_MAP = {
    'real'       : Decimal,
    'complex'    : Complex,
    'rational'   : Rational,
    'e-notation' : ENotation
    }

STYLESHEET_MAPPING = {
    'mathmlc2p' : ('mathml',   'pmathml'),
    'ctop'      : ('mathml',   'pmathml2'),
    'pMML2SVG'  : ('pmathml',  'svg')
    }

STYLESHEET_TRANSFORMERS = {}

# prepare XSL stylesheets
STYLESHEETS = {}
from os import path
for xsl_name, (input_type, output_type) in STYLESHEET_MAPPING.iteritems():
    try:
        STYLESHEETS[output_type] = (input_type, UTILS_STYLESHEETS[xsl_name])
    except KeyError: # not available
        pass
    except Exception, e:
        print "Error loading stylesheet %s:" % xsl_name, e
        pass

xslt = None
l = len(STYLESHEETS) + 1
while l > len(STYLESHEETS):
    l = len(STYLESHEETS)
    for output_type, (input_type, xslt) in STYLESHEETS.items():
        if input_type != 'mathml' and input_type not in STYLESHEETS:
            del STYLESHEETS[output_type]

xslts = None
for output_type, (input_type, xslt) in STYLESHEETS.items():
    STYLESHEET_TRANSFORMERS[output_type] = xslts = []
    input_type = None
    while input_type != 'mathml':
        try:
            input_type, xslt = STYLESHEETS[output_type]
        except KeyError:
            raise ValueError, "Unsupported output format %s, please install appropriate stylesheets" % output_type
        xslts.insert(0, xslt)
        output_type = input_type

del STYLESHEETS, l, xslt, xslts, xsl_name, input_type, output_type, path # clean up

# ignore XML Schema for MathML validation (doesn't currently work because of libxml2)
MML_SCHEMA = None

# try to read RelaxNG schema for MathML validation
MML_RNG = SCHEMAS.get('mathml2')


_MATH_NS_DICT = {'math' : MATHML_NAMESPACE_URI}
_NAMESPACE    = "{%s}" % MATHML_NAMESPACE_URI
_ANCESTOR_XPATH = _etree.XPath('ancestor::math:*[1]', namespaces=_MATH_NS_DICT)

_parser = _etree.XMLParser(remove_blank_text=True)

def _tag_name(local_name):
    return u"{%s}%s" % (MATHML_NAMESPACE_URI, local_name)

def SiblingElement(_element, _tag, *args, **kwargs):
    return SubElement(_element.getparent(), _tag, *args, **kwargs)

Element = _parser.makeelement


class Qualifier(object):
    def __init__(self, name, default_node=None):
        self.name = _NAMESPACE + name
        self.__xpath = '../math:' + name
        self.__default_node = default_node

    def __find_qualifier(self, node, default=None):
        try:
            _xpath_eval = node._xpath
        except AttributeError:
            _xpath_eval = None

        if _xpath_eval:
            qualifier_nodes = _xpath_eval(self.__xpath)
        else:
            qualifier_nodes = node.xpath(self.__xpath, _MATH_NS_DICT)

        if qualifier_nodes:
            return qualifier_nodes[0]
        else:
            return default

    def __get__(self, node, owner):
        if node is None:
            return self
        qualifier_node = self.__find_qualifier(node, self.__default_node)
        return qualifier_node[0]

    def __set__(self, node, value):
        qualifier_node = self.__find_qualifier(node)
        if qualifier_node is None:
            qualifier_node = SiblingElement(node, self.name)

        if isinstance(value, (str, unicode)):
            qualifier_node.clear()
            qualifier_node.text = value
        else:
            qualifier_node.text = None
            qualifier_node.append(value)


class MathElement(_etree.ElementBase):
    @property
    def localName(self):
        tagname = self.tag
        if tagname[:1] == '{':
            return tagname.split('}', 1)[-1]
        else:
            return tagname

    @property
    def childNodes(self):
        return self.getchildren()

    @property
    def firstChild(self):
        return self[0]

    def xpath(self, expression, other_namespaces=None):
        if not other_namespaces or other_namespaces == _MATH_NS_DICT:
            return self._xpath(expression)

        evaluator = _etree.XPathElementEvaluator(
            self, namespaces=other_namespaces)
        evaluator.registerNamespace('math', MATHML_NAMESPACE_URI)
        return super(MathElement, self).xpath(
            expression, namespaces=other_namespaces)

    def _xpath(self, xpath):
        try:
            evaluate = self.__xpath_evaluator
        except AttributeError:
            evaluate = self.__xpath_evaluator = \
                _etree.XPathElementEvaluator(
                self, namespaces=_MATH_NS_DICT).evaluate
        return evaluate(xpath)

    def mathtype(self):
        return self.localName

    def has_type(self, name):
        return self.localName == name

    def iteridentifiers(self):
        return iter(self._xpath('.//math:ci'))

    def iteridentifiernames(self):
        return (e.name() for e in self._xpath('.//math:ci'))

    def iterconstants(self):
        return iter(self._xpath('.//math:true|.//math:false|.//math:exponentiale|.//math:imaginaryi|.//math:pi'))

    def iterconstantnames(self):
        return (e.localName for e in self.iterconstants())

    def iternumbers(self):
        return iter(self._xpath('.//math:cn'))

    def iternumbervalues(self):
        return (n.value() for n in self._xpath('.//math:cn'))

    def iteroperators(self):
        return (e[0] for e in self._xpath('.//math:apply') if len(e))


class SerializableMathElement(MathElement):
    def to_tree(self):
        return dom_to_tree(self)

    def serialize(self, *args, **kwargs):
        return serialize_dom(self, *args, **kwargs)

    if 'pmathml' in STYLESHEET_TRANSFORMERS:
        def to_pmathml(self):
            """Returns an ElementTree containing a Presentational
            MathML representation of this document."""
            return self.xsltify('pmathml')
        to_pres = to_pmathml
    elif 'pmathml2' in STYLESHEET_TRANSFORMERS:
        def to_pmathml(self):
            """Returns an ElementTree containing a Presentational
            MathML representation of this document."""
            return self.xsltify('pmathml2')
        to_pres = to_pmathml

    if STYLESHEET_TRANSFORMERS:
        def xsltify(self, _output_format, **kwargs):
            xslts = STYLESHEET_TRANSFORMERS[_output_format]
            root = ElementTree(self)
            for xslt in xslts:
                root = xslt.apply(root, **kwargs)
            return root

class math_math(SerializableMathElement):
    IMPLEMENTS = 'math'

class math_cn(SerializableMathElement):
    IMPLEMENTS = 'cn'
    VALID_TYPES = ("real", "integer", "rational")
    def __repr__(self):
        name = self.localName
        return u"<%s type='%s'>%r</%s>" % (name, self.get('type', 'real'), self.value(), name)

    def valuetype(self):
        typeattr = self.get('type')
        if typeattr:
            return typeattr
        elif self.text and len(self) == 0:
            value = self.text
            for type_test, name in ((int, 'integer'), (float, 'real')):
                try:
                    type_test(value)
                    return name
                except ValueError:
                    pass
        else:
            return 'real' # MathML default!

    def set_rational(self, *value):
        "Set the rational value of this element"
        value = Rational(*value)
        self._set_tuple_value('rational', (value.num_str, value.denom_str))

    def set_complex(self, value):
        "Set the complex value of this element"
        try:
            tuple_value = (value.real_str, value.imag_str)
        except AttributeError:
            tuple_value = (unicode(value.real), unicode(value.imag))
        self._set_tuple_value('complex', tuple_value)

    def value(self):
        "Returns the numerical value with the correct type."
        valuetype = self.valuetype()
        if valuetype == 'integer':
            return int(self.text)
        elif valuetype == 'real':
            return Decimal(self.text)

        try:
            typeclass = TYPE_MAP[valuetype]
            return typeclass(self.text, self[0].tail)
        except KeyError:
            raise NotImplementedError, "Invalid data type."

    def _set_tuple_value(self, type_name, value_tuple):
        self.clear()
        self.text = unicode(value_tuple[0])
        sep = SubElement(self, _tag_name('sep'))
        sep.tail  = unicode(value_tuple[1])
        self.set('type', type_name)

    def set_value(self, value, type_name=None):
        """Set the value of this element. May have to specify a MathML
        type name for clarity."""
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
                    type_name = 'integer'
                elif isinstance(value, float):
                    type_name = 'real'
                else:
                    raise TypeError, "Invalid value type. Please specify type name."
        elif type_name not in self.VALID_TYPES:
            raise ValueError, "Unsupported type name."
        self.clear()
        self.set('type', type_name)
        self.text = unicode(value)


class math_ci(SerializableMathElement):
    IMPLEMENTS = 'ci'
    def __repr__(self):
        name = self.localName
        return u"<%s>%r</%s>" % (name, self[0], name)

    def value(self):
        return self[0]

    def name(self):
        name = self.text
        if name:
            return name
        name = self.localName
        if name:
            return name
        return str(self[0])


class math_apply(SerializableMathElement):
    IMPLEMENTS = 'apply'
    def operator(self):
        return self[0]

    def operatorname(self):
        return self[0].localName

    def set_operator(self, new_operator):
        operands = self[1:]
        self.clear()
        if isinstance(new_operator, (str, unicode)):
            SubElement(self, _tag_name(new_operator))
        elif isinstance(new_operator, MathElement):
            operands.insert(0, new_operator)
        else:
            raise ValueError, "Operator value has invalid type, use strings or math elements."
        for operand in operands:
            self.append(operand)

    def operands(self):
        return self[1:]

    def operand_count(self):
        return len(self) - 1

    def append_operand(self, operand):
        if not len(self):
            raise TypeError, "You must supply an operator first."
        self.append(operand)


class math_minus(MathElement):
    IMPLEMENTS = 'minus'
    def is_negation(self):
        return len(self.getparent()) == 2


class math_interval(MathElement):
    IMPLEMENTS = 'interval'
    def closure(self):
        return self.get('closure') or 'closed'


class math_unary_function(MathElement):
    IMPLEMENTS = UNARY_FUNCTIONS
    def operand(self):
        return self.firstChild


class math_log(math_unary_function):
    IMPLEMENTS = 'log'
    # logbase setup later


class MathDOM(object):
    def __init__(self, etree=None):
        self._parser = parser = _etree.XMLParser(remove_blank_text=True)
        _register_mathml_classes(parser)
        self._Element = parser.makeelement

        if etree is None:
            root = self._Element('{%s}math' % MATHML_NAMESPACE_URI)
            etree = ElementTree(root)
        self._etree = etree

    @staticmethod
    def __build_input_file(source):
        if hasattr(source, 'read'):
            return source
        else:
            return StringIO(source)

    @classmethod
    def fromSax(cls, input, sax_parser):
        "Build a MathDOM from input using sax_parser."
        content_handler = ElementTreeContentHandler(makeelement=Element)
        sax_parser.setContentHandler(content_handler)
        sax_parser.parse( cls.__build_input_file(input) )
        return cls( content_handler.etree )

    @classmethod
    def fromString(cls, input, input_type='mathml'):
        "Build a MathDOM from input using the string term parser for input_type."
        return cls.fromStream(cls.__build_input_file(input), input_type)

    @classmethod
    def fromStream(cls, input, input_type='mathml'):
        """Build a MathDOM from the file-like object input using the
        stringterm parser for input_type."""
        if input_type == 'mathml':
            return cls( ElementTree(file=input, parser=self._parser) )
        else:
            sax_parser = SaxTerm.for_input_type(input_type)
            return cls.fromSax(input, sax_parser())

    def toMathml(self, out=None, indent=False):
        """Convert this MathDOM into MathML and write it to file (or
        file-like object) out. Note that the indent parameter is
        currently ignored due to limitations of lxml."""
        if out is None:
            out = sys.stdout
        tree = self._etree
        try:
            if tree.getroot().mathtype() != 'math':
                math_root = self._Element('{%s}math' % MATHML_NAMESPACE_URI)
                math_root[:] = [tree.getroot()]
                tree = ElementTree(math_root)
        except AttributeError:
            pass
        #if indent: ??
        self._etree.write(out, encoding='UTF-8')

    if 'pmathml' in STYLESHEET_TRANSFORMERS or 'pmathml2' in STYLESHEET_TRANSFORMERS:
        def to_pmathml(self, *args, **kwargs):
            """Returns an ElementTree containing a Presentational
            MathML representation of this document."""
            root = self._etree.getroot()
            return root.to_pmathml(*args, **kwargs)
        to_pres = to_pmathml

    if STYLESHEET_TRANSFORMERS:
        def xsltify(self, _output_format, **kwargs):
            "Run an XSLT on the root node."
            root = self._etree.getroot()
            return root.xsltify(_output_format, **kwargs)

    if MML_SCHEMA:
        def validate(self):
            "Validate the MathDOM against the MathML 2.0 XML Schema."
            return MML_SCHEMA.validate(self._etree)
    elif MML_RNG:
        def validate(self):
            "Validate the MathDOM against the MathML 2.0 RelaxNG schema."
            return MML_RNG.validate(self._etree)

    def to_tree(self):
        "Build and return the AST representation."
        return dom_to_tree(self._etree)

    def serialize(self, output_format=None, converter=None, **kwargs):
        """Serialize to 'mathml' (default), 'pmathml' or any other
        supported term format."""
        if converter is None:
            if output_format is None:
                output_format = 'mathml'
            if output_format == 'mathml':
                out = StringIO()
                self.toMathml(out, False)
                return out.getvalue()
            elif output_format in STYLESHEET_TRANSFORMERS:
                etree = self.xsltify(output_format, **kwargs)
                out = StringIO()
                etree.write(out, encoding='UTF-8')
                return out.getvalue()
        return serialize_dom(self._etree, output_format, converter)

    def xpath(self, expression, other_namespaces=None):
        """Evaluate an XPath expression against the MathDOM.  The
        'math' prefix will automatically be available for the MathML
        namespace.  If other namespaces are needed, the can be
        specified as a {prefix : namespaceURI} dictionary.
        """
        if other_namespaces:
            other_namespaces = other_namespaces.copy()
            other_namespaces.update(_MATH_NS_DICT)
        else:
            other_namespaces = _MATH_NS_DICT
        return self._etree.xpath(expression, namespaces=other_namespaces)

    def xslt(self, stylesheet):
        "Run an XSLT stylesheet against the MathDOM."
        return self._etree.xslt(stylesheet)

    def __getattr__(self, name):
        return getattr(self._etree, name)

    # new DOM methods:

    def createApply(self, name, *args):
        """Create a new apply tag given the name of a function or
        operator and (optionally) its paremeter elements as further
        arguments."""
        apply_tag = self._Element('{%s}apply' % MATHML_NAMESPACE_URI)
        function_tag = SubElement(apply_tag,
                                  '{%s}%s' % (MATHML_NAMESPACE_URI, name))
        if args:
            if len(args) == 1 and isinstance(args[0], (list, tuple)):
                args = args[0]
            for child in args:
                apply_tag.append(child)
        return apply_tag

    createFunction = createApply

    def createConstant(self, value):
        "Create a new constant with the given value."
        cn_tag = self._Element('{%s}cn' % MATHML_NAMESPACE_URI)
        cn_tag.set_value(value)
        return cn_tag

    def createIdentifier(self, name):
        "Create a new identifier that represents the given name."
        ci_tag = self._Element('{%s}ci' % MATHML_NAMESPACE_URI)
        ci_tag.text = name
        return ci_tag


def Constant(parent, value, type_name=None):
    """Create a new cn tag under the parent element that represents
    the given constant."""
    if isinstance(parent, MathDOM):
        parent = parent.getroot()
    cn_tag = SubElement(parent, '{%s}cn' % MATHML_NAMESPACE_URI)
    cn_tag.set_value(value, type_name)
    return cn_tag

def Identifier(parent, name):
    """Create a new ci tag under the parent element that represents
    the given name."""
    if isinstance(parent, MathDOM):
        parent = parent.getroot()
    ci_tag = SubElement(parent, '{%s}ci' % MATHML_NAMESPACE_URI)
    ci_tag.text = name
    return ci_tag

Name = Identifier

def Apply(parent, name, *args):
    """Create a new apply tag under the parent element, given the name
    of a function or operator and (optionally) its parameter elements
    as further arguments."""
    if isinstance(parent, MathDOM):
        parent = parent.getroot()
    apply_tag    = SubElement(parent,
                              '{%s}apply' % MATHML_NAMESPACE_URI)
    function_tag = SubElement(apply_tag,
                              '{%s}%s' % (MATHML_NAMESPACE_URI, name))
    if args:
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            args = args[0]
        for child in args:
            apply_tag.append(child)
    return apply_tag


# serializer function for lxml.XSLT

def xslt_serialize(_, nodes, output_type):
    return ''.join( node.serialize(output_type) for node in nodes )

_etree.FunctionNamespace(MATHML_NAMESPACE_URI)['serialize'] = xslt_serialize


# global setup, register namespace implementation

def _setup_logbase():
    # set up "math_log.logbase"
    _default_logbase = Element('{%s}cn' % MATHML_NAMESPACE_URI)
    _default_logbase.text = '10'
    math_log.logbase = Qualifier('logbase', _default_logbase)

def _prepare_mathml_classes():
    classes = [ (cls.IMPLEMENTS.split(), cls)
                for cls in _all_names
                if isinstance(cls, type)
                and issubclass(cls, MathElement)
                and hasattr(cls, 'IMPLEMENTS') ]

    # move more generic implementations to the front
    # to overwrite them by more special classes
    class_sort = [ (len(item[0]), i, item)
                   for i, item in enumerate(classes) ]
    class_sort.sort(reverse=True)

    class_dict = {}
    for item in class_sort:
        tags, cls = item[2]
        class_dict.update((tag, cls) for tag in tags)
    class_dict[None] = MathElement

    return class_dict

_setup_logbase()
del _setup_logbase

_all_names = vars().values()
_all_mathml_classes = _prepare_mathml_classes()
del _all_names, _prepare_mathml_classes

def _register_mathml_classes(parser):
    lookup = _etree.ElementNamespaceClassLookup()
    parser.set_element_class_lookup(lookup)

    lxml_math_namespace = lookup.get_namespace(MATHML_NAMESPACE_URI)
    lxml_math_namespace.update(_all_mathml_classes)

_register_mathml_classes(_parser)
