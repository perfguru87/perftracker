#!/bin/sh
VER=`grep "__pt_version__ = " perftracker/__init__.py | cut -d "'" -f 2`

echo "\n###### run the following commands manually ######\n"
echo "vim perftracker/__init__.py  # update version"
echo "git commit -m \"bump version to $VER\" perftracker/__init__.py && git tag \"v$VER\" && git push origin --tags"
echp "git push"
echo
