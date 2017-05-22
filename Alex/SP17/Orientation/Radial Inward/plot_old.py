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
    angle = float(subdir.name[:-4])
    with open(os.path.join(subdir.path, "raw.csv")) as f:
        datapoints[angle] = parse_csv(f)

# Connect the two sides of the plot
datapoints[360.0] = datapoints[0.0]

ids = __get_ids(datapoints)


channel_avgs = []
for angle in datapoints:
    channel_avgs.append((angle, dict([(ch, round(st.mean([dp["rssi"] for dp in datapoints[angle] if dp["channel"] == ch]), 3)) for ch in [37, 38, 39]])))
channel_avgs = sorted(channel_avgs, key=lambda x: x[0])


tag_avgs = []
for angle in datapoints:
    tag_avgs.append((angle, dict([(tag, round(st.mean([dp["rssi"] for dp in datapoints[angle] if dp["tag_id"] == tag]), 3)) for tag in ids])))
tag_avgs = sorted(tag_avgs, key=lambda x: x[0])


fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(10, 10))
plt.subplots_adjust(wspace=0.2, hspace=0.3, left=0.08, right=0.87, top=0.95, bottom=0.07)

ax = axes[0]
for ch in [37, 38, 39]:
    ax.plot(
        [i[0] for i in channel_avgs],
        [i[1][ch] for i in channel_avgs]
    )
ax.set_title("Average Signal Strength by Channel")
ax.set_xlabel("Receiver Angle (degrees)")
ax.set_ylabel("Average RSSI (dBm)")
ax.margins(y=0.1)
ax.legend([37, 38, 39], loc="center left", bbox_to_anchor=(1, 0.5))
ax.autoscale(tight=True)
for angle in [0, 90, 180, 270, 360]:
    ax.axvline(x=angle, color='grey')

ax = axes[1]
for i in ids:
    ax.plot(
        [j[0] for j in tag_avgs],
        [j[1][i] for j in tag_avgs]
    )
ax.set_title("Average Signal Strength by Tag")
ax.set_xlabel("Receiver Angle (degrees)")
ax.set_ylabel("Average RSSI (dBm)")
ax.margins(y=0.1)
ax.legend(ids, loc="center left", bbox_to_anchor=(1, 0.5))
ax.autoscale(tight=True)
for angle in [0, 90, 180, 270, 360]:
    ax.axvline(x=angle, color='grey')

plt.savefig(args.chart)
