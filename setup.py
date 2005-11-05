from distutils.core import setup
import sys, os

VERSION  = '0.6.3.1'
PACKAGE_NAME = 'mathdom'
PACKAGES = ['mathml', 'mathml.utils']
PACKAGE_DATA = {}

# CONFIG DEFAULTS

FORCED_PACKAGE_NAME=None
INCLUDE_LXML_SOURCE=False
REQUIRE_PACKAGES_FOR_BUILD=False

# CONFIGURE PACKAGE

root_dir = os.path.dirname(__file__)
src_dir  = os.path.join(root_dir, 'mathml')

try:
    os.stat(os.path.join(src_dir, 'lmathdom.py'))
    HAS_LMATHDOM = True
except OSError:
    HAS_LMATHDOM = False

try:
    os.stat(os.path.join(src_dir, 'mathdom.py'))
    HAS_MATHDOM = True
except OSError:
    HAS_MATHDOM = False

# CMD LINE OVERRIDE

options = sys.argv[1:]
for option in options:
    remove_option = True
    if option.startswith('--name='):
        FORCED_PACKAGE_NAME=option[7:]
    elif option == '--contrib-lxml':
        INCLUDE_LXML_SOURCE = True
    elif option == '--no-contrib-lxml':
        INCLUDE_LXML_SOURCE = False
    elif option == '--require-imports':
        REQUIRE_PACKAGES_FOR_BUILD = True
    elif option == '--no-require-imports':
        REQUIRE_PACKAGES_FOR_BUILD = False
    elif option == '--pyxml':
        HAS_LMATHDOM = False
    elif option == '--lxml':
        HAS_MATHDOM = False
    else:
        remove_option = False
    if remove_option:
        sys.argv.remove(option)

# HELP MESSAGE

if '--help' in options or '--help-mathdom' in options:
    print """MathDOM package install options:
    --help-mathdom       : show this usage information and exit
    --name=XXX           : force package name to XXX
    --contrib-lxml       : include lxml sources in 'contrib/lxml/'  (%s)
    --no-contrib-lxml    : do not include lxml sources
    --require-imports    : check if required packages are installed (%s)
    --no-require-imports : do not check installation
    --pyxml              : build *only* 'mathdom-pyxml' package
    --lxml               : build *only* 'mathdom-lxml'  package

    Current build config : lxml (%s), pyxml (%s), forced name (%s)
    """ % (INCLUDE_LXML_SOURCE, REQUIRE_PACKAGES_FOR_BUILD,
           HAS_LMATHDOM, HAS_MATHDOM, FORCED_PACKAGE_NAME)
    try:
        sys.argv.remove('--help-mathdom')
        sys.exit(0)
    except ValueError:
        pass

# CHECK FOR AVAILABLE PACKAGES

if REQUIRE_PACKAGES_FOR_BUILD:
    if HAS_LMATHDOM:
        try:
            from lxml.etree import SaxTreeBuilder
        except:
            print "lxml not installed or not patched."
            HAS_LMATHDOM = False

    if HAS_MATHDOM:
        try:
            from xml import xpath
        except:
            print "PyXML not installed."
            HAS_MATHDOM = False

if INCLUDE_LXML_SOURCE:
    INCLUDE_LXML_SOURCE = False
    if HAS_LMATHDOM:
        try:
            os.stat(os.path.join(root_dir, 'contrib/lxml'))
            INCLUDE_LXML_SOURCE = True
        except OSError:
            print "lxml source not installed in contrib directory."

# CHECK WHICH PACKAGE TO BUILD

if HAS_MATHDOM and HAS_LMATHDOM:
    pass
elif HAS_MATHDOM:
    PACKAGE_NAME += "-pyxml"
elif HAS_LMATHDOM:
    PACKAGE_NAME += "-lxml"
else:
    raise RuntimeError, "Package must contain mathml.mathdom and/or mathml.lmathdom module!"

if HAS_LMATHDOM:
    PACKAGE_DATA.update({
        'mathml'       : ['schema/mathml2.rng.gz'],
        'mathml.utils' : ['mathmlc2p.xsl', 'ctop.xsl']
        })
    PACKAGES.append('mathml.pmathml')

# BUILD MANIFEST.in

manifest = open(os.path.join(root_dir, 'MANIFEST.in'), 'w')
manifest.write("""
include setup.py MANIFEST.in README LICENSE ChangeLog
recursive-include test *.py
include mathml/*.py mathml/utils/*.py
include examples/infix.py
""")
if HAS_LMATHDOM:
    manifest.write("""
    include lxml*.patch examples/ldom.py mathml/schema/mathml2.rng.gz mathml/utils/mathmlc2p.xsl mathml/utils/ctop.xsl
    include mathml/pmathml/*.py mathml/pmathml/backend/*.py
    """.replace('    ', ''))
else:
    manifest.write("""
    exclude mathml/lmathdom.py mathml/utils/sax_pmathml.py
    recursive-exclude mathml/pmathml *
    """.replace('    ', ''))
if HAS_MATHDOM:
    manifest.write("""
    include examples/dom.py
    """.replace('    ', ''))
else:
    manifest.write("""
    exclude mathml/mathdom.py
    """.replace('    ', ''))
if INCLUDE_LXML_SOURCE:
    manifest.write("""
    recursive-include contrib/lxml MANIFEST.in *.txt *.py *.pxd *.pyx *.xml *.mgp
    """.replace('    ', ''))
manifest.close()

# RUN SETUP

setup(
    name=FORCED_PACKAGE_NAME or PACKAGE_NAME,
    version=VERSION,
    packages=PACKAGES,
    package_data=PACKAGE_DATA,

    description='MathDOM - Content MathML in Python',
    long_description="""MathDOM - Content MathML in Python

**MathDOM** is a set of Python 2.4 modules (using PyXML_ or lxml_, and
pyparsing_) that import mathematical terms as a `Content MathML`_
DOM. It currently parses MathML and literal infix terms into a DOM
document and writes out MathML and literal infix/prefix/postfix/Python
terms. The DOM elements are enhanced by domain specific methods that
make using the DOM a little easier. Implementations based on PyXML and
lxml/libxml2 are available.

.. _lxml:                  http://codespeak.net/lxml/
.. _pyparsing:             http://pyparsing.sourceforge.net/
.. _PyXML:                 http://pyxml.sourceforge.net/
.. _`Content MathML`:      http://www.w3.org/TR/MathML2/chapter4.html
.. _MathML:                http://www.w3.org/TR/MathML2/
.. _PyMathML:              http://pymathml.sourceforge.net/

You can call it the shortest way between different term
representations and a Content MathML DOM. Ever noticed the annoying
differences between terms in different programming languages? Build
your application around the DOM and stop caring about the term
representation that users prefer or that your machine can execute. If
you need a different representation, add a converter, but don't change
the model of your application. Literal terms are connected through an
intermediate AST step that makes writing converters for
SQL/Java/Lisp/*your-favourite* easy.

New in version 0.6.3.1:

- Fixes for a number of bugs in mathdom and lmathdom modules

New in version 0.6.2:

- Generalized parser framework
- Python term parser

New in version 0.6.1:

- integration of the PyMathML_ renderer (untested!)
- more generic integration of XSLT scripts

New in version 0.6:

- RelaxNG validation
- Presentation MathML export (based on XSLT)
- stricter spec conformance (encloses MathML output in <math> tag

The first two require lxml, PyXML does not support them.
""",

    author='Stefan Behnel',
    author_email='scoder@users.sourceforge.net',
    url='http://mathdom.sourceforge.net/',
    download_url='http://www.sourceforge.net/projects/mathdom',

    classifiers = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python',
    'Topic :: Text Processing :: Markup :: XML',
    'Topic :: Scientific/Engineering :: Mathematics',
    ],

    keywords = "MathML xml DOM math parser validator"
    )
