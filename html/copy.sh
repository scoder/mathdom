#!/bin/sh

SFLOGO="     <a href='http://www.sourceforge.net/'                            ><img src='http://sourceforge.net/sflogo.php?group_id=149323\&amp;type=1' alt='SourceForge Logo'             style='border: 0px solid ; margin: 2px ; height: 31px ; width: 88px ;' /></a>"
SUPPORTLOGO="<a href='http://sourceforge.net/donate/index.php?group_id=149323'><img src='project-support.png'                                           alt='Support This Project'         style='border: 0px solid ; margin: 2px ; height: 32px ; width: 88px ;' /></a>"
XHTMLLOGO="  <a href='http://validator.w3.org/check?uri=referer'              ><img src='http://www.w3.org/Icons/valid-xhtml10'                         alt='Valid XHTML 1.0 Transitional' style='border: 0px solid ; margin: 2px ; height: 31px ; width: 88px ;' /></a>"

VERSION=`ls ../releases/mathdom* | sed -ne "s/.*mathdom-\([0-9.]\+\)[.]tar.*/\1/p" | sort -r | head -1`

echo "Current version: $VERSION"

sed -e "s|\(<!--CURRENT-->\)[^<]*\(<!--/CURRENT-->\)|\1 $VERSION \2| ; \
        s|mathdom-[0-9.]*tar.gz|mathdom-$VERSION.tar.gz| ; \
        s|<!--XHTMLLOGO-->|${XHTMLLOGO//  / }|
        s|<!--SFLOGO-->|${SFLOGO//  / }|
        s|<!--SUPPORTLOGO-->|${SUPPORTLOGO//  / }|
        " > index.html < MathDOM.html
ls -l index.html

rsync -ruvtL index.html *.png *.css scoder@shell.sourceforge.net:/home/groups/m/ma/mathdom/htdocs/
