from distutils.core import setup
setup(
    name='mathdom',
    version='0.5.1',
    packages=['mathml', 'mathml.utils'],

    description='MathDOM - Content MathML in Python',
    long_description="""MathDOM - Content MathML in Python

**MathDOM** is a set of Python 2.4 modules (using PyXML_ and
pyparsing_) that import mathematical terms as a `Content MathML`_ DOM. It
currently parses MathML and literal infix terms into a DOM document
and writes out MathML and literal infix/prefix/postfix/Python
terms. The DOM elements are enhanced by domain specific methods that
make using the DOM a little easier.

.. _pyparsing:             http://pyparsing.sourceforge.net
.. _PyXML:                 http://pyxml.sourceforge.net
.. _`Content MathML`:      http://www.w3.org/TR/MathML2/chapter4.html
.. _MathML:                http://www.w3.org/TR/MathML2/

You can call it the shortest way between different term
representations and a Content MathML DOM. Ever noticed the annoying
differences between terms in different programming languages? Build
your application around the DOM and stop caring about the term
representation that users prefer or that your machine can execute. If
you need a different representation, add a converter, but don't change
the model. Literal terms are connected through an intermediate AST
step that makes writing converters for SQL/Java/Lisp/*your-favourite*
easy.
""",

    author='Stefan Behnel',
    author_email='scoder@users.sourceforge.net',
    url='http://mathdom.sourceforge.net/',
    download_url='http://www.sourceforge.net/projects/mathdom',

    classifiers = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python',
    'Topic :: Text Processing :: Markup :: XML',
    'Topic :: Scientific/Engineering :: Mathematics',
    ],

    keywords = "MathML xml DOM math parser"
    )
