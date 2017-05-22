#!/usr/bin/env python3

import sys
import argparse
import os
import csv
import statistics as st
import numpy as np
import numpy.linalg as la
import matplotlib.pyplot as plt

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("chart",
    help="chart file to output")
args = arg_parser.parse_args()

class Model:
    def __init__(self):
        self.__model = {}

    @classmethod
    def __get_ids(cls, arr):
        def helper(arr):
            if "tag_id" in arr:
                return set([arr["tag_id"]])
            ids = set()
            for i in arr:
                if hasattr(i, "__iter__"):
                    ids |= helper(i)
                else:
                    ids |= helper(arr[i])
            return ids
        return sorted(list(helper(arr)))

    @classmethod
    def __abs_azimuth(cls, id):
        return {
            1: 270.0,
            2: 225.0,
            3: 180.0,
            4: 135.0,
            5: 90.0,
            6: 45.0,
            7: 0.0,
            8: 315.0,
        }[id]

    @classmethod
    def __rel_angle(cls, abs_tag_angle, abs_receiver_angle):
        return (abs_tag_angle - abs_receiver_angle) % 360.0

    @classmethod
    def make_vector(cls, datapoints, id):
        return tuple(st.mean([dp["rssi"] for dp in datapoints
                if dp["channel"] == ch and dp["tag_id"] == id])
            for ch in [37, 38, 39])

    def add_data(self, data, radius, receiver_orientation):
        rel_orientation = self.__rel_angle(270, receiver_orientation)
        if not radius in self.__model:
            self.__model[radius] = {}
        for id in self.__get_ids(data):
            azimuth = self.__rel_angle(
                self.__abs_azimuth(id),
                receiver_orientation
            )
            if not azimuth in self.__model[radius]:
                self.__model[radius][azimuth] = {}
            self.__model[radius][azimuth][rel_orientation] = \
                self.make_vector(data, id)

    def get(self, radius, azimuth, rel_orientation, only_r=False, only_a=False, only_o=False):
        if only_r:
            return [sum(y) / len(y) for y in zip(
                *[self.__model[radius][a][o] for a in self.__model[radius] for o in self.__model[radius][a]])]
        elif only_a:
            return [sum(y) / len(y) for y in zip(
                *[self.__model[r][azimuth][o] for r in self.__model for o in self.__model[r][azimuth]])]
        elif only_o:
            return [sum(y) / len(y) for y in zip(
                *[self.__model[r][a][rel_orientation] for r in self.__model for a in self.__model[r]])]
        else:
            return self.__model[radius][azimuth][rel_orientation]


def freq_to_channel_num(freq):
    return {
        2: 37,
        26: 38,
        80: 39,
    }[freq]

def norm(v1, v2, norm=2):
    return la.norm(np.subtract(v1, v2), ord=norm)

def parse_csv(f):
    datapoints = []
    reader = csv.reader(f)
    timestamp_offset = None
    for row in reader:
        dp = {}
        dp["tag_id"] = int(row[0])
        dp["rssi"] = int(row[3])
        dp["channel"] = freq_to_channel_num(int(row[4]))
        datapoints.append(dp)
    return datapoints

m = Model()
angles = set()
radii = set()

for subdir in os.scandir():
    if not subdir.is_dir():
        continue
    radius = int(subdir.name[0:2])
    receiver_orientation = float(subdir.name[7:-4])
    radii.add(radius)
    angles.add(receiver_orientation)
    with open(os.path.join(subdir.path, "raw.csv")) as f:
        m.add_data(parse_csv(f), radius, receiver_orientation)

radii = sorted(list(radii))
angles = sorted(list(angles))
channels = [37, 38, 39]

avgs = [m.get(r, None, None, only_r=True) for r in radii]
# avgs = [m.get(None, a, None, only_a=True) for a in angles]
# avgs = [m.get(None, None, o, only_o=True) for o in angles]

plt.subplots_adjust(left=0.1, right=0.85, top=0.93, bottom=0.1)
for ch in range(3):
    plt.plot(radii, [i[ch] for i in avgs])
    # plt.plot(angles, [i[ch] for i in avgs])
plt.title("Signal Strength by Radius")
# plt.title("Signal Strength by Azimuth")
# plt.title("Signal Strength by Orientation")
plt.xlabel("Radius (cm)")
# plt.xlabel("Azimuth (deg)")
# plt.xlabel("Orientation (deg)")
plt.ylabel("RSSI (dBm)")
plt.margins(y=0.1)
plt.legend(channels, loc="center left", bbox_to_anchor=(1, 0.5))
plt.autoscale(tight=True)
plt.savefig(args.chart)
# plt.show()
