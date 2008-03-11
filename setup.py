try:
    from setuptools import setup
    from setuptools.extension import Extension
except ImportError:
    from distutils.core import setup
    from distutils.extension import Extension
import sys, os

VERSION  = '0.8'
PACKAGE_NAME = 'mathdom'
PACKAGES = ['mathml', 'mathml.utils', 'mathml.schema']
PACKAGE_DATA = {}
PACKAGE_DIRS = {}
EXTENSIONS   = []

# CONFIG DEFAULTS

FORCED_PACKAGE_NAME=None
REQUIRE_PACKAGES_FOR_BUILD=False

# CONFIGURE PACKAGE

root_dir = os.path.dirname(__file__)
src_dir  = os.path.join(root_dir, 'mathml')

try:
    os.stat(os.path.join(src_dir, 'lmathdom.py'))
    HAS_LMATHDOM = True
except OSError:
    HAS_LMATHDOM  = False

try:
    os.stat(os.path.join(src_dir, 'mathdom.py'))
    HAS_MATHDOM = True
except OSError:
    HAS_MATHDOM = False

try:
    os.stat(os.path.join(root_dir, 'contrib', 'lxml', 'src', 'lxml', 'etree.c'))
    HAS_LXML_C = True
except OSError:
    HAS_LXML_C = False

# CMD LINE OVERRIDE

options = sys.argv[1:]
distutils_options = []
for option in options:
    if option.startswith('--name='):
        FORCED_PACKAGE_NAME=option[7:]
    elif option == '--require-imports':
        REQUIRE_PACKAGES_FOR_BUILD = True
    elif option == '--no-require-imports':
        REQUIRE_PACKAGES_FOR_BUILD = False
    elif option == '--pyxml':
        HAS_LMATHDOM = False
    elif option == '--lxml':
        HAS_MATHDOM = False
    else:
        distutils_options.append(option)

sys.argv[1:] = distutils_options

# HELP MESSAGE

if '--help' in options or '--help-mathdom' in options:
    print """MathDOM package install options:
    --help-mathdom       : show this usage information and exit
    --name=XXX           : force package name to XXX
    --require-imports    : build depending on installed PyXML/lxml  (%s)
    --no-require-imports : do not check installation
    --pyxml              : build *only* 'mathdom-pyxml' package
    --lxml               : build *only* 'mathdom-lxml'  package

    Current build config : lxml (%s), pyxml (%s), forced name (%s)
    """ % (REQUIRE_PACKAGES_FOR_BUILD,
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
exclude html/*
include html/*.png html/*.css html/MathDOM.html
recursive-include test *.py
include mathml/*.py mathml/utils/*.py mathml/schema/*.py
include examples/infix.py
""")
if HAS_LMATHDOM:
    manifest.write("""
    include examples/ldom.py mathml/schema/mathml2.rng.gz mathml/utils/mathmlc2p.xsl mathml/utils/ctop.xsl
    include mathml/pmathml/*.py mathml/pmathml/backend/*.py
    recursive-exclude mathml/pmathml .cvsignore
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
manifest.close()

# RUN SETUP

setup(
    name=FORCED_PACKAGE_NAME or PACKAGE_NAME,
    version=VERSION,
    packages=PACKAGES,
    package_data=PACKAGE_DATA,
    package_dir=PACKAGE_DIRS,
    ext_modules=EXTENSIONS,

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
your application around MathDOM and stop caring about the term
representation that users prefer or that your machine can execute. If
you need a different representation, add a converter, but don't change
the model of your application. Literal terms are connected through an
intermediate AST step that makes writing converters for
SQL/Java/Lisp/*your-favourite* easy.

New in version 0.8:

- works with (and requires) lxml 2.0 or later

New in version 0.7.2:

- works with (and requires) lxml 1.3 or later

New in version 0.7.1:

- bug fix for operator qualifiers

New in version 0.7:

- works with lxml 0.9 out-of-the-box

New in version 0.6.7:

- added missing '%' operator (modulo)
- adapted to updated lxml API

New in version 0.6.6:

- closer APIs of mathdom and lmathdom
- convenience functions to portably create apply, ci and cn elements

New in version 0.6.5:

- XSLT extension function to include literal terms in output
- bug fix in Python term serializer

New in version 0.6.4:

- Updated setup.py script to use setuptools if available
- Support for splitting package into two PyXML and lxml dependent packages
- Now builds patched lxml during install

New in version 0.6.3.1:

- Fixes a number of bugs in mathdom and lmathdom modules

New in version 0.6.2:

- Generalized parser framework
- Python term parser

New in version 0.6.1:

- integration of the PyMathML_ renderer (untested!)
- more generic integration of XSLT scripts

New in version 0.6:

- RelaxNG validation (lxml)
- Presentation MathML export (based on XSLT/lxml)
- stricter spec conformance (encloses MathML output in <math> tag
""",

    author='Stefan Behnel',
    author_email='scoder@users.sourceforge.net',
    url='http://mathdom.sourceforge.net/',
    download_url='http://prdownloads.sourceforge.net/mathdom/mathdom-%s.tar.gz?download' % VERSION,

    classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python',
    'Topic :: Text Processing :: Markup :: XML',
    'Topic :: Scientific/Engineering :: Mathematics',
    'Topic :: Software Development :: Libraries :: Python Modules'
    ],

    keywords = "MathML xml DOM math parser validator"
)
