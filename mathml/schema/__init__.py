import os, re
from os import path
from lxml.etree import tostring, parse, XMLSchema, RelocatableRelaxNG, XSLT, ElementTree, XML

__all__ = ['SCHEMAS']

__RE_SCHEMA_FILE = re.compile('.*\.(rng|xsd)(\.gz)?$', re.I)

schema_dir = path.dirname(__file__)
schema_files = [ filename for filename in os.listdir(schema_dir)
                 if __RE_SCHEMA_FILE.match(filename) ]

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
