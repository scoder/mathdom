from distutils.core import setup
setup(
    name='mathml',
    version='0.1',
    package_dir={'mathml': ''},
    packages=['mathml'],
    py_modules=['mathml.mathdom', 'mathml.termparser', 'mathml.xmlterm']
    )
