#!/usr/bin/env python3

import argparse
import os
import re
import csv
import statistics as st
import matplotlib.pyplot as plt

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("chart",
    help="chart file to output")
args = arg_parser.parse_args()

def __freq_to_channel_num(freq):
    ''' Map frequency (24xx MHz) to advertising channel number. '''
    if freq == 2:
        return 37
    elif freq == 26:
        return 38
    elif freq == 80:
        return 39
    else:
        return -1

def __get_ids(arr):
    ''' Get a list of tag IDs that were detected. '''
    def helper(arr):
        if "tag_id" in arr:
            return set([arr["tag_id"]])
        ids = set()
        for i in arr:
            if hasattr(i, '__iter__'):
                ids |= helper(i)
            else:
                ids |= helper(arr[i])
        return ids
    return sorted(list(helper(arr)))

def parse_csv(f):
    ''' Parse the CSV-formatted file or serial port output. '''
    datapoints = []
    reader = csv.reader(f)
    timestamp_offset = None
    for row in reader:
        dp = {}
        dp["tag_id"] = int(row[0])
        dp["sequence_num"] = int(row[1])
        if timestamp_offset == None:
            timestamp_offset = int(row[2])
        dp["timestamp"] = int(row[2]) - timestamp_offset
        dp["rssi"] = int(row[3])
        dp["channel"] = __freq_to_channel_num(int(row[4]))
        datapoints.append(dp)
    return datapoints


datapoints = {}

for subdir in os.scandir():
    if not subdir.is_dir():
        continue
    distance = int(subdir.name[0:2])
    angle = float(subdir.name[7:-4])
    with open(os.path.join(subdir.path, "raw.csv")) as f:
        if not angle in datapoints:
            datapoints[angle] = {}
        datapoints[angle][distance] = parse_csv(f)

# Connect the two sides of the plot
datapoints[360.0] = datapoints[0.0]

channels = [37, 38, 39]
angles = sorted(list(datapoints.keys()))
distances = sorted(list(datapoints[0.0].keys()))
ids = __get_ids(datapoints)

avgs = [[[[st.mean([dp["rssi"] for dp in datapoints[angle][dist]
                if dp["channel"] == ch and dp["tag_id"] == id])
            for angle in angles]
        for ch in channels]
    for dist in distances]
for id in ids]

plt.subplots_adjust(left=0.1, right=0.95, top=0.93, bottom=0.1)
for id in avgs:
    for dist in id:
        for ch in dist:
            plt.plot(angles, ch)
plt.title("Signal Strength by Channel and Distance")
plt.xlabel("Angle (degrees)")
plt.ylabel("RSSI (dBm)")
plt.margins(y=0.1)
# plt.legend(["Tag {}, {} cm, ch {}".format(i, d, c) for i in ids for d in distances for c in channels],
#     loc="center left", bbox_to_anchor=(1, 0.5), fontsize=8)
plt.autoscale(tight=True)
for angle in [0, 90, 180, 270, 360]:
    plt.axvline(x=angle, color='grey')
plt.savefig(args.chart)
# plt.show()
