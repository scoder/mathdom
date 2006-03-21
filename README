MathDOM - handling terms through a MathML DOM in Python
-------------------------------------------------------

I'd be really glad to hear if this is useful. And maybe you have an idea how
to make it better. :) Just send me an email:
Stefan Behnel <scoder@users.sourceforge.net>

See LICENSE file for licensing.

You can find the latest version at
http://mathdom.sourceforge.net


What is MathDOM?
----------------

Terms, there and back again.

The package comprises parsers for a subset of Content MathML 2.0 and infix
terms (using pyparsing [1]). It provides access to the term tree through a DOM
(based on PyXML/4DOM [2]) or, preferably, the ElementTree API on top of lxml
[3] and allows serialization to Content MathML and literal terms in infix,
prefix and postfix notation. It supports subclassable input/output filters,
e.g. for Python terms.

If you want to test it, run 'examples/infix.py'.


A quick example:
----------------

>>> from mathml.lmathdom import MathDOM                     # use lxml implementation
>>> doc = MathDOM.fromString("+2^x+4*-5i/6", "infix_term")  # parse infix term
>>> [ n.value() for n in doc.xpath(u'//math:cn[@type="integer"]') ] # find integers
[2, 4, 6]
>>> for apply_tag in doc.xpath(u'//math:apply[math:plus]'): # replace '+' with '-'
...     apply_tag.set_operator(u'minus')
>>> from mathml.utils import pyterm                         # register Python term builder
>>> doc.serialize("python")                                 # serialize to Python term
u'2 ** x - 4 * (-5j) / 6'

Simple, isn't it ?


Current status:
---------------

MathDOM 0.7 is now in a stable state. There have not been any bug reports for
quite a while.  Future enhancements may regard the compatibility of the two
implementations (PyXML and lxml).  They will likely come closer based on the
ElementTree API.


Regarding lxml:
---------------

The lxml based implementation shares most of the code with the PyXML one, but
replaces the DOM implementation with a patched version of lxml [3], an XML API
similar to ElementTree [4], implemented on top of libxml2 [5]. That makes it
much faster than the pure Python implementation (just try test/test.py for a
comparison) and it supports more XML features, like XSLT and XInclude.

MathDOM 0.7 should work out-of-the-box with lxml 0.9 and better.  Get it from
http://codespeak.net/lxml/


PyXML vs. lxml:
---------------

MathDOM's mathml package includes two main modules: mathdom and lmathdom.  The
first depends on PyXML and the second on lxml.  It is one of the goals of
MathDOM to keep both APIs as close as possible, but since lxml's ElementTree
API is very different in spirit from PyXML's DOM, there will always be
differences.  If you want your code to be portable between both (e.g. to use
the mathdom module as a fallback in Jython), please try to avoid the XML
specific APIs as much as possible and prefer the methods that are defined by
the MathDOM implementation.  Both implementations share a subset of the
ElementTree API.  If you need a specific feature that both lxml and PyXML
support, but that is accessed differently in both MathDOM APIs, feel free to
discuss this on the MathDOM mailing list as a request for API enhancement.


The files:
----------

* Installation:

setup.py                - distutils, try "python setup.py install"


* Examples are in "examples/":

examples/infix.py       - example: read a term, write out MathML, infix,
                          prefix, postfix representations
                          -> START HERE if you want to figure out how
                          things work.

examples/dom.py         - example: read a term, do some DOM stuff

examples/ldom.py        - example: read a term, do some lxml/xpath stuff


* The actual package source is in "mathml/":

mathml/mathdom.py       - the DOM implemention

mathml/lmathdom.py      - the lxml implemention (supports XSLT, RelaxNG, etc.)

mathml/xmlterm.py       - SAX generator for the termparser AST

mathml/termparser.py    - parser for literal infix terms

mathml/termbuilder.py   - serializer for literal terms,
                          framework for output converters


* Extensions are in "mathml/utils/":

mathml/utils/pyterm.py  - a Python term serializer and parser

mathml/utils/sqlterm.py - a preliminary SQL term serializer

mathml/utils/mathmlc2p.xsl
mathml/utils/ctop.xsl   - XSLT converters: Content MathML -> Presentation MathML

mathml/utils/sax_pmathml.py
                        - PyMathML [6] integration through the SAX interface


* PyMathML [6] is in "mathml/pmathml/"

  For convenience, PyMathML [6] is included in MathDOM. PyMathML is a
  renderer for Presentational MathML, written by Gustavo Carneiro and
  distributed under the terms of the LGPL (if you can't accept that,
  don't use it!). For questions regarding PyMathML, please contact the
  PyMathML project at SourceForge. I do not maintain that package!
  If you want to use PyMathML with MathDOM, take a look at
  mathml/utils/sax_pmathml.py


References
----------

[1] pyparsing:   http://pyparsing.sf.net/
[2] PyXML:       http://pyxml.sf.net/
[3] lxml:        http://codespeak.net/lxml/
[4] ElementTree: http://effbot.org/zone/element-index.htm
[5] libxml2:     http://xmlsoft.org/
[6] PyMathML:    http://pymathml.sf.net/


Have fun!
