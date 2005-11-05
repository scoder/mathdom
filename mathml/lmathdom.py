#!/usr/bin/python

__all__ = [ 'MathDOM' ]

import sys
from StringIO  import StringIO

from lxml.etree import (parse, ElementBase, Element, SubElement, ElementTree,
                        register_namespace_classes, XSLT, XMLSchema, RelaxNG,
                        XPathElementEvaluator, SaxTreeBuilder)

from mathml           import MATHML_NAMESPACE_URI, UNARY_FUNCTIONS
from mathml.xmlterm   import SaxTerm, dom_to_tree, serialize_dom
from mathml.datatypes import Decimal, Complex, Rational, ENotation

TYPE_MAP = {
    'real'       : Decimal,
    'complex'    : Complex,
    'rational'   : Rational,
    'e-notation' : ENotation
    }

RNG_SCHEMA_FILE = 'mathml2.rng.gz'

STYLESHEET_MAPPING = {
    'mathmlc2p.xsl' : ('mathml',   'pmathml'),
    'ctop.xsl'      : ('mathml',   'pmathml2'),
    'pMML2SVG.xsl'  : ('pmathml',  'svg')
    }

STYLESHEET_TRANSFORMERS = {}

# try to read XSL stylesheets
STYLESHEETS = {}
xslt_filename = None
from os import path
for xsl_file, (input_type, output_type) in STYLESHEET_MAPPING.iteritems():
    try:
        xslt_filename = path.abspath( path.join(path.dirname(__file__), 'utils', xsl_file) )
        STYLESHEETS[output_type] = (input_type, XSLT( parse(xslt_filename) ))
    except IOError: # file not found => not available
        pass
    except Exception, e:
        print "Error loading stylesheet %s:" % xsl_file, e
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

del STYLESHEETS, l, xslt, xslts, xslt_filename, xsl_file, input_type, output_type, path # clean up


# try to read XML Schema for MathML validation (doesn't currently work because of libxml2)
MML_SCHEMA = None
## schema_filename = None
## try:
##     from os import path
##     schema_filename = path.abspath( path.join(path.dirname(__file__), 'schema', 'mathml2-content.xsd') )
##     del path
##     MML_SCHEMA = XMLSchema( parse(schema_filename) )
## except IOError:
##     pass
## except Exception, e:
## #    print e
##     pass
## del schema_filename

# try to read RelaxNG schema for MathML validation
MML_RNG = None
schema_filename = None
try:
    from os import path
    schema_filename = path.abspath( path.join(path.dirname(__file__), 'schema', RNG_SCHEMA_FILE) )
    del path
    MML_RNG = RelaxNG( parse(schema_filename) )
except IOError:
    pass
except Exception, e:
    print "Error reading RelaxNG schema for MathML:", e
    pass
del schema_filename


_MATH_NS_DICT = {u'math' : MATHML_NAMESPACE_URI}
_NAMESPACE    = u"{%s}" % MATHML_NAMESPACE_URI

def _tag_name(local_name):
    return u"{%s}%s" % (MATHML_NAMESPACE_URI, local_name)

def _parent(node):
    return node.xpath(u'ancestor::math:*[1]', _MATH_NS_DICT)[0]

def SiblingElement(_element, _tag, *args, **kwargs):
    return SubElement(_parent(_element), _tag, *args, **kwargs)


class Qualifier(object):
    def __init__(self, name, default_node=None):
        self.name = _NAMESPACE + name
        self.__xpath = u'../math:*[local-name() = %s]' % name
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


class MathElement(ElementBase):
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

        evaluator = XPathElementEvaluator(self, other_namespaces)
        evaluator.registerNamespace(u'math', MATHML_NAMESPACE_URI)
        return super(ElementBase, self).xpath(expression, other_namespaces)

    def _xpath(self, xpath):
        try:
            evaluate = self.__xpath_evaluator
        except AttributeError:
            evaluate = self.__xpath_evaluator = XPathElementEvaluator(self, _MATH_NS_DICT).evaluate
        return evaluate(xpath)

    def mathtype(self):
        return self.localName

    def has_type(self, name):
        return self.localName == name

    def iteridentifiers(self):
        return iter(self._xpath(u'.//math:ci'))

    def iteridentifiernames(self):
        return (e.name() for e in self._xpath(u'.//math:ci'))

    def iterconstants(self):
        return iter(self._xpath(u'.//math:true|.//math:false|.//math:exponentiale|.//math:imaginaryi|.//math:pi'))

    def iterconstantnames(self):
        return (e.localName for e in self.iterconstants())

    def iternumbers(self):
        return iter(self._xpath(u'.//math:cn'))

    def iternumbervalues(self):
        return (n.value() for n in self._xpath(u'.//math:cn'))

    def iteroperators(self):
        return (e[0] for e in self._xpath(u'.//math:apply') if len(e))


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
    IMPLEMENTS = u'math'

class math_cn(SerializableMathElement):
    IMPLEMENTS = u'cn'
    def __repr__(self):
        name = self.localName
        return u"<%s type='%s'>%r</%s>" % (name, self.get(u'type', u'real'), self.value(), name)

    def valuetype(self):
        typeattr = self.get(u'type')
        if typeattr:
            return typeattr
        elif self.text and len(self) == 0:
            value = self.text
            for type_test, name in ((int, u'integer'), (float, u'real')):
                try:
                    type_test(value)
                    return name
                except ValueError:
                    pass
        else:
            return u'real' # MathML default!

    def set_rational(self, *value):
        "Set the rational value of this element"
        value = Rational(*value)
        self._set_tuple_value(u'rational', (value.num_str, value.denom_str))

    def set_complex(self, value):
        "Set the complex value of this element"
        try:
            tuple_value = (value.real_str, value.imag_str)
        except AttributeError:
            tuple_value = (unicode(value.real), unicode(value.imag))
        self._set_tuple_value(u'complex', tuple_value)

    def value(self):
        "Returns the numerical value with the correct type."
        valuetype = self.valuetype()
        if valuetype == u'integer':
            return int(self.text)
        elif valuetype == u'real':
            return Decimal(self.text)

        try:
            typeclass = TYPE_MAP[valuetype]
            return typeclass(self.text, self[0].tail)
        except KeyError:
            raise NotImplementedError, "Invalid data type."

    def _set_tuple_value(self, typename, value_tuple):
        self.clear()
        self.text = unicode(value_tuple[0])
        sep = SubElement(self, _tag_name(u'sep'))
        sep.tail  = unicode(value_tuple[1])
        self.set(u'type', typename)

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
                    type_name = u'integer'
                elif isinstance(value, float):
                    type_name = u'real'
                else:
                    raise TypeError, "Invalid value type. Please specify type name."
        self.clear()
        self.text = unicode(value)


class math_ci(SerializableMathElement):
    IMPLEMENTS = u'ci'
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
    IMPLEMENTS = u'apply'
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
    IMPLEMENTS = u'minus'
    def is_negation(self):
        return len(_parent(self)) == 2


class math_interval(MathElement):
    IMPLEMENTS = u'interval'
    def closure(self):
        return self.get(u'closure') or 'closed'


class math_unary_function(MathElement):
    IMPLEMENTS = UNARY_FUNCTIONS
    def operand(self):
        return self.firstChild


class math_log(math_unary_function):
    IMPLEMENTS = u'log'
    default_logbase = Element(u'{%s}cn' % MATHML_NAMESPACE_URI)
    default_logbase.text = u'10'
    logbase = Qualifier(u'logbase', default_logbase)
    del default_logbase


class MathDOM(object):
    def __init__(self, etree=None):
        if etree is None:
            root = Element(u'{%s}math' % MATHML_NAMESPACE_URI)
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
        content_handler = SaxTreeBuilder()
        sax_parser.setContentHandler(content_handler)
        sax_parser.parse( cls.__build_input_file(input) )
        return cls( content_handler.etree )

    @classmethod
    def fromString(cls, input, input_type='mathml'):
        return cls.fromStream(cls.__build_input_file(input), input_type)

    @classmethod
    def fromStream(cls, input, input_type='mathml'):
        if input_type == 'mathml':
            return cls( ElementTree(file=input) )
        else:
            sax_parser = SaxTerm.for_input_type(input_type)
            return cls.fromSax(input, sax_parser())

    def toMathml(self, out=None, indent=False):
        if out is None:
            out = sys.stdout
        tree = self._etree
        try:
            if tree.getroot().mathtype() != u'math':
                math_root = Element(u'{%s}math' % MATHML_NAMESPACE_URI)
                math_root[:] = [tree.getroot()]
                tree = ElementTree(math_root)
        except AttributeError:
            pass
        #if indent: ??
        self._etree.write(out, 'UTF-8')

    if 'pmathml' in STYLESHEET_TRANSFORMERS or 'pmathml2' in STYLESHEET_TRANSFORMERS:
        def to_pmathml(self, *args, **kwargs):
            """Returns an ElementTree containing a Presentational
            MathML representation of this document."""
            root = self._etree.getroot()
            return root.to_pmathml(*args, **kwargs)
        to_pres = to_pmathml

    if STYLESHEET_TRANSFORMERS:
        def xsltify(self, _output_format, **kwargs):
            root = self._etree.getroot()
            return root.xsltify(_output_format, **kwargs)

    if MML_SCHEMA:
        def validate(self):
            return MML_SCHEMA.validate(self._etree)
    elif MML_RNG:
        def validate(self):
            return MML_RNG.validate(self._etree)

    def to_tree(self):
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
                etree.write(out, 'UTF-8')
                return out.getvalue()
        return serialize_dom(self._etree, output_format, converter)

    def xpath(self, expression, other_namespaces=None):
        if other_namespaces:
            other_namespaces = other_namespaces.copy()
            other_namespaces.update(_MATH_NS_DICT)
        else:
            other_namespaces = _MATH_NS_DICT
        return self._etree.xpath(expression, other_namespaces)

    def __getattr__(self, name):
        return getattr(self._etree, name)

    # new DOM methods:

    def createApply(self, name, *args):
        apply_tag = Element(u'{%s}apply' % MATHML_NAMESPACE_URI)
        function_tag = SubElement(apply_tag, u'{%s}%s' % (MATHML_NAMESPACE_URI, name))
        if args:
            function_tag[:] = args
        return apply_tag

    createFunction = createApply

    def createConstant(self, value):
        cn_tag = Element(u'{%s}cn' % MATHML_NAMESPACE_URI)
        cn_tag.set_value(value)
        return cn_tag


# register namespace implementation

classes = [ (cls.IMPLEMENTS.split(), cls) for cls in vars().values()
            if isinstance(cls, type) and issubclass(cls, MathElement) and hasattr(cls, 'IMPLEMENTS') ]

class_sort = [ (len(item[0]), i, item) for i, item in enumerate(classes) ]
class_sort.sort(reverse=True) # move more generic implementations to the front

class_dict = {}
for item in class_sort:
    tags, cls = item[2]
    class_dict.update((tag, cls) for tag in tags)

class_dict[None] = MathElement
register_namespace_classes(MATHML_NAMESPACE_URI, class_dict)
