#!/bin/sh
acc=(0 0 0 0)
echo "Order,Nearest,,,Farthest"
for f in data/baselines/????.csv
do
    name=$(basename -s .csv $f)
    ./analyze.py "$f" -c none |
    grep "order" |
    while read -r junk1 junk2 order
    do
        for i in 0 1 2 3
        do
            if [ ${order:i:1} -eq ${name:i:1} ]
            then
                (( acc[i]++ ))
            fi
        done
        IFS=","; echo "$name,${acc[*]}"
    done
done

echo
echo "Order,Position,SD"
for f in data/baselines/????.csv
do
    name=$(basename -s .csv $f)
    ./analyze.py "$f" -c none |
    grep -n "RSSI stddev" |
    while IFS=" :"; read -r linenum junk1 junk2 stddev junk3
    do
        (( num=$linenum/6 ))
        for i in 0 1 2 3
        do
            if [ ${name:i:1} -eq $num ]
            then
                IFS=","; echo "$name,$i,$stddev"
            fi
        done
    done
done

echo
echo "Order,Position,Loss"
for f in data/baselines/????.csv
do
    name=$(basename -s .csv $f)
    ./analyze.py "$f" -c none |
    grep -n "Loss" |
    while IFS=" :"; read -r linenum junk1 loss
    do
        (( num=$linenum/6 ))
        for i in 0 1 2 3
        do
            if [ ${name:i:1} -eq $num ]
            then
                IFS=","; echo "$name,$i,$loss"
            fi
        done
    done
done