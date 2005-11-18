__doc__ = """
MathML numeric type implementations based on the Decimal type.

Complex, Rational, ENotation
"""

from decimal import Decimal


class Complex(complex):
    """Data type for complex numbers.

    Examples are (1+5i), (0.1-2i), (-i), ...
    """
    TYPE_NAME = u'complex'

    __ZERO = Decimal(0)
    def __new__(cls, real, imag=None):
        if imag is None:
            if isinstance(real, cls):
                return real
            elif isinstance(real, complex):
                return cls(real.real, real.imag)
            else:
                imag = cls.__ZERO
                instance = complex.__new__(cls, real)
        elif isinstance(real, (str, unicode)) and isinstance(imag, (str, unicode)):
            instance = complex.__new__(cls, cls.__build_complex_str(real, imag))
        else:
            instance = complex.__new__(cls, real, imag)

        instance.__tuple = (instance.__real, instance.__imag) = (unicode(real), unicode(imag))
        return instance

    def __complex__(self):
        return self

    def __iter__(self):
        "Fake iterator to support tuple conversion."
        return iter(self.__tuple)

    @property
    def real_str(self):
        return self.__real

    @property
    def imag_str(self):
        return self.__imag

    @classmethod
    def __build_complex_str(cls, real, imag):
        return "%s%s%sj" % (real, (float(imag) >= 0) and '+' or '', imag)

    def __repr__(self):
        return "Complex(%s%s%sj)" % (self.__real, (self.imag >= 0) and '+' or '', self.__imag)

    def __str__(self):
        return "(%s%s%sj)" % (self.__real, (self.imag >= 0) and '+' or '', self.__imag)


class Rational(Decimal):
    """Data type for rational numbers.

    Examples are 1/20, 3/45, ...
    """
    TYPE_NAME = u'rational'

    def __new__(cls, num, denom=None):
        if denom is None:
            if isinstance(num, cls):
                return num
            else:
                denom = 1
        num, denom = int(num), int(denom)
        instance = Decimal.__new__(cls, Decimal(num) / denom)
        instance.__num, instance.__denom = (num, denom)
        instance.__tuple = (unicode(num), unicode(denom))
        return instance

    def __iter__(self):
        "Fake iterator to support tuple conversion."
        return iter(self.__tuple)

    @property
    def num(self):
        return self.__num

    @property
    def denom(self):
        return self.__denom

    @property
    def num_str(self):
        return unicode(self.__num)

    @property
    def denom_str(self):
        return unicode(self.__denom)

    def __repr__(self):
        return "Rational(%s/%s)" % (self.num, self.denom)


class ENotation(Decimal):
    """Data type of numbers in E-Notation.

    An example is 1E20 for 1*10^20.
    """
    TYPE_NAME = u'e-notation'

    def __new__(cls, num, exponent=None):
        if exponent is None:
            if isinstance(num, cls):
                return num
            else:
                exponent = 1
        else:
            exponent = int(exponent)

        if exponent > 0:
            value = Decimal(num) * (10 ** exponent)
        else:
            value = Decimal(num) / (10 ** abs(exponent))

        instance = Decimal.__new__(cls, value)
        instance.__num, instance.__exponent = num, exponent
        instance.__tuple = (unicode(num), unicode(exponent))
        return instance

    def __iter__(self):
        "Fake iterator to support tuple conversion."
        return iter(self.__tuple)

    @property
    def num(self):
        return self.__num

    @property
    def exponent(self):
        return self.__exponent

    @property
    def num_str(self):
        return unicode(self.__num)

    @property
    def exponent_str(self):
        return unicode(self.__exponent)

    def __repr__(self):
        return "%sE%+04d" % (self.num, self.exponent)

    def __str__(self):
        return "%sE%+d" % (self.num, self.exponent)
