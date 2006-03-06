import os, re
from os import path
from lxml.etree import tostring, parse, RelaxNG, XMLSchema, XSLT, ElementTree, XML

__all__ = ['SCHEMAS']

__RE_SCHEMA_FILE = re.compile('.*\.(rng|xsd)(\.gz)?$', re.I)

schema_dir = path.dirname(__file__)
schema_files = [ filename for filename in os.listdir(schema_dir)
                 if __RE_SCHEMA_FILE.match(filename) ]


class RelocatableRelaxNG(object):
    _relocate_xslt = XSLT(XML('''\
    <xsl:stylesheet version="1.0"
         xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
         xmlns:rng="http://relaxng.org/ns/structure/1.0"
         xmlns="http://relaxng.org/ns/structure/1.0">
      <xsl:template match="/rng:*">
        <xsl:copy>
          <xsl:copy-of select="@*"/>
          <rng:start><rng:ref rng:name="{$newref}"/></rng:start>
          <xsl:apply-templates/>
        </xsl:copy>
      </xsl:template>
      <xsl:strip-space elements="*"/>
      <xsl:template match="rng:start"/>
      <xsl:template match="*">
        <xsl:copy><xsl:copy-of select="@*"/><xsl:apply-templates/></xsl:copy>
      </xsl:template>
    </xsl:stylesheet>
    '''))

    def __init__(self, tree, start=None):
        self._tree  = tree
        self._start = start

    def validate(self, xml_tree):
        if self._start is None:
            rng_tree = self._tree
        else:
            rng_tree = self._relocate_xslt(self._tree,
                                           newref="'%s'" % self._start)
            # ugly hack to get around namespace (?) issues
            rng_tree = parse(StringIO(str(rng_tree)))
        rng = RelaxNG(rng_tree)
        self.validate = rng.validate # replace the object method by the real thing
        return rng.validate(xml_tree)

    def copy(self, start=None):
        return self.__class__(self._tree, start)

    def relocate(self, start):
        self._start = start
        try: del self.validate
        except AttributeError: pass


class SchemaDict(dict):
    def __init__(self):
        dict.__init__(self)
        self.BROKEN = {}
        for filename in schema_files:
            file_path = path.join(schema_dir, filename)
            name, ext = path.splitext(filename)
            ext = ext.lower()
            while ext == '.gz':
                name, ext = path.splitext(name)
                ext = ext.lower()
            try:
                tree = parse(file_path)
                if 'xsd' in ext:
                    self[name] = XMLSchema(tree)
                else:
                    self[name] = RelocatableRelaxNG(tree)
            except Exception, e:
                self.BROKEN[name] = e

SCHEMAS = SchemaDict()
