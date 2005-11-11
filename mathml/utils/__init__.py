import os
from os import path
from lxml.etree import parse, XSLT

__all__ = ['STYLESHEETS']

xslt_dir = path.dirname(__file__)
xslt_files = [ filename for filename in os.listdir(xslt_dir)
               if filename.endswith('.xsl') or filename.endswith('.xslt') ]

class StylesheetDict(dict):
    def __init__(self):
        dict.__init__(self)
        self.BROKEN = {}
        for filename in xslt_files:
            name = path.splitext(filename)[0]
            try:
                self[name] = XSLT(parse(path.join(xslt_dir, filename)))
            except Exception, e:
                self.BROKEN[name] = e

STYLESHEETS = StylesheetDict()
