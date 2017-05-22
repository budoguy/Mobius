#!/bin/sh
echo "Channel,Position,Distance,Loss"
for d in data/distances/*
do
    distance=$(basename $d)
    for f in $d/??.csv
    do
        name=$(basename -s .csv "$f")
        ./analyze.py "$f" -c none |
        grep -n "Loss" |
        while IFS=" :"; read -r linenum junk1 loss
        do
            (( num=$linenum/8 ))
            IFS=","; echo "$name,$num,$distance,$loss"
        done
    done
done

echo
echo "Channel,Position,Distance,SD"
for d in data/distances/*
do
    distance=$(basename $d)
    for f in $d/??.csv
    do
        name=$(basename -s .csv "$f")
        ./analyze.py "$f" -c none |
        grep -n "RSSI stddev" |
        while IFS=" :"; read -r linenum junk1 junk2 stddev junk3
        do
            (( num=($linenum-1)/8 ))
            IFS=","; echo "$name,$num,$distance,$stddev"
        done
    done
done

echo
echo "Channel,Position,Distance,RSSI"
for d in data/distances/*
do
    distance=$(basename $d)
    for f in $d/??.csv
    do
        name=$(basename -s .csv "$f")
        ./analyze.py "$f" -c none |
        grep -n "RSSI avg" |
        while IFS=" :"; read -r linenum junk1 junk2 rssi junk3
        do
            (( num=$linenum/8 ))
            IFS=","; echo "$name,$num,$distance,$rssi"
        done
    done
done