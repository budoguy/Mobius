#!/bin/sh
echo "Channel,Position,Loss"
for f in data/scan\ intervals\ single\ channel/??.csv data/scan\ intervals\ single\ channel/all.csv
do
    name=$(basename -s .csv "$f")
    ./analyze.py "$f" -c none |
    grep -n "Loss" |
    while IFS=" :"; read -r linenum junk1 loss
    do
        (( num=$linenum/8 ))
        IFS=","; echo "$name,$num,$loss"
    done
done