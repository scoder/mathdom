#!/bin/sh

VERSION=`ls ../releases/mathdom* | sed -ne "s/.*mathdom-\([0-9.]\+\)[.]tar.*/\1/p" | sort -r | head -1`

echo "Current version: $VERSION"

sed -e "s|\(<!--CURRENT-->\)[^<]*\(<!--/CURRENT-->\)|\1$VERSION\2|" > index.html < MathDOM.html
ls -l index.html

rsync -ruvtl index.html *.png scoder@shell.sourceforge.net:/home/groups/m/ma/mathdom/htdocs/
