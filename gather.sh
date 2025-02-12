#!/bin/bash

[ -f claude.txt ] && rm claude.txt
for f in `find . -name "*.py" -not -path "*migrations*" -not -name "__init__.py"`;
do
	echo "# $f" >> claude.txt
	cat $f >> claude.txt
done
