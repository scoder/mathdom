from distutils.core import setup
setup(
    name='mathdom',
    version='0.3.0',
    package_dir={'mathml': 'src'},
    packages=['mathml'],

    description='MathDOM - Content MathML in Python',
    long_description="""MathDOM - Content MathML in Python

MathDOM is a set of Python 2.4 modules (using PyXML and pyparsing)
that import mathematical terms as a Content MathML DOM. It
currently parses MathML and literal infix terms into a DOM
document and writes out MathML and literal infix/prefix/postfix
terms. The DOM elements are enhanced by domain specific methods
that make using the DOM a little easier.

You can call it the shortest way between different term
representations and a Content MathML DOM. Ever noticed the
annoying differences between terms in different programming
languages? Build your application around the DOM and stop caring
about the term representation that users prefer or that your
machine can execute. If you need a different representation, add a
converter, but don't change the model. Literal terms are connected
through an intermediate AST step that makes writing converters for
Python/SQL/yourfavorite easier.
""",

    author='Stefan Behnel',
    author_email='scoder@users.sourceforge.net',
    url='http://mathdom.sourceforge.net/',

    classifiers = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python',
    'Topic :: Text Processing :: Markup :: XML',
    'Topic :: Scientific/Engineering :: Mathematics',
    ]
    )
