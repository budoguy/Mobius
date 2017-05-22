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

def __tag_id_to_angle_offset(id):
    ''' Convert the tag number to the angle offset from 0 degrees '''
    if id == 7:
        return 0.0
    elif id == 6:
        return 45.0
    elif id == 5:
        return 90.0
    elif id == 4:
        return 135.0
    elif id == 3:
        return 180.0
    elif id == 2:
        return 225.0
    elif id == 1:
        return 270.0
    elif id == 8:
        return 315.0
    else:
        raise ValueError("id must be an integer between 1 and 8")


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
channels = [37, 38, 39]
angles = sorted(list(datapoints.keys()))

channel_avgs = []
for angle in datapoints:
    channel_avgs.append(
        (angle, dict([
            (ch,
                st.mean([dp["rssi"] for tag in ids for dp in
                    datapoints[(__tag_id_to_angle_offset(tag) - angle) % 360.0]
                    if dp["channel"] == ch and dp["tag_id"] == tag]))
            for ch in channels])))
channel_avgs = sorted(channel_avgs, key=lambda x: x[0])

# channel_avgs = []
# for angle in datapoints:
#     channel_avgs.append(
#         (angle, dict([
#             (ch,
#                 st.mean([dp["rssi"] for dp in
#                     datapoints[angle] if dp["channel"] == ch]))
#             for ch in [37, 38, 39]])))
# channel_avgs = sorted(channel_avgs, key=lambda x: x[0])

# channel_avgs = [[st.mean([dp["rssi"]
#         for dp in datapoints[angle] if dp["channel"] == ch])
#     for angle in angles]
# for ch in channels]



# fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(10, 5))
# plt.subplots_adjust(wspace=0.2, hspace=0.3, left=0.08, right=0.87, top=0.92, bottom=0.12)


# tag_avgs = []
# for angle in datapoints:
#     tag_avgs.append(
#         (angle, dict([
#             (tag,
#                 st.mean([dp["rssi"] for dp in
#                     datapoints[angle]
#                     if dp["tag_id"] == tag]))
#             for tag in ids])))
# tag_avgs = sorted(tag_avgs, key=lambda x: x[0])


# ax = axes[0]
# for i in ids:
#     ax.plot(
#         [j[0] for j in tag_avgs],
#         [j[1][i] for j in tag_avgs]
#     )
# ax.set_title("Average Signal Strength by Tag")
# ax.set_xlabel("Receiver Angle (degrees)")
# ax.set_ylabel("Average RSSI (dBm)")
# ax.margins(y=0.1)
# ax.legend(ids, loc="center left", bbox_to_anchor=(1, 0.5))
# ax.autoscale(tight=True)
# for angle in [0, 90, 180, 270, 360]:
#     ax.axvline(x=angle, color='grey')




# tag_avgs = []
# for angle in datapoints:
#     tag_avgs.append(
#         (angle, dict([
#             (tag,
#                 st.mean([dp["rssi"] for dp in
#                     datapoints[(__tag_id_to_angle_offset(tag) - angle) % 360.0]
#                     if dp["tag_id"] == tag]))
#             for tag in ids])))
# tag_avgs = sorted(tag_avgs, key=lambda x: x[0])



plt.subplots_adjust(left=0.1, right=0.85, top=0.93, bottom=0.1)
for ch in channels:
    plt.plot(
        [i[0] for i in channel_avgs],
        [i[1][ch] for i in channel_avgs]
    )
# for j in ids:
#     plt.plot(
#         [i[0] for i in tag_avgs],
#         [i[1][j] for i in tag_avgs]
#     )
plt.title("Signal Strength by Azimuth")
plt.xlabel("Azimuth (degrees)")
plt.ylabel("RSSI (dBm)")
plt.margins(y=0.1)
plt.legend(channels, loc="center left", bbox_to_anchor=(1, 0.5))
plt.autoscale(tight=True)
for angle in [0, 90, 180, 270, 360]:
    plt.axvline(x=angle, color='grey')

plt.savefig(args.chart)
# plt.show()
