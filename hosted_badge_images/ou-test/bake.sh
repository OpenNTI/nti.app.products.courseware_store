#!/bin/sh
for f in *.json 
do
	png=${f%.*}.png
	if [ -f "$png" ]
	then
		echo "Baking $png"
		nti_bake_badge -p $f $png
	fi
done
