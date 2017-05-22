#!/bin/sh
echo "Scan Interval,Position,Loss"
for f in data/scan\ intervals/test_??.csv data/scan\ intervals/test_???.csv
do
    name=$(basename -s .csv "$f")
    name=${name:5}
    ./analyze.py "$f" -c none |
    grep -n "Loss" |
    while IFS=" :"; read -r linenum junk1 loss
    do
        (( num=$linenum/6 ))
        IFS=","; echo "$name,$num,$loss"
    done
done