#!/bin/sh
dir=`dirname ${BASH_SOURCE[0]}`
find $dir -name \*.py | xargs pycodestyle --max-line-length=140 --ignore=E221
