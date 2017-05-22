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
# arg_parser.add_argument("infile",
#     help="file to predict")
# arg_parser.add_argument("id",
#     help="ID of the tag to predict",
#     type=int)
# arg_parser.add_argument("--radius", "-r",
#     help="radial distance from the beacon to the receiver (centimeters)",
#     type=int)
# arg_parser.add_argument("--azimuth", "-a",
#     help="azimuth of the beacon relative to the receiver (degrees)",
#     type=int)
# arg_parser.add_argument("--orientation", "-o",
#     help="orientation of the beacon relative to the receiver (degrees)",
#     type=float)
# arg_parser.add_argument("chart",
#     help="chart file to output")
# args = arg_parser.parse_args()

# if not ((args.radius == None and
#          args.azimuth != None and
#          args.orientation != None) or
#         (args.radius != None and
#          args.azimuth == None and
#          args.orientation != None) or
#         (args.radius != None and
#          args.azimuth != None and
#          args.orientation == None)):
#     print("Error: you must provide exactly two measurements")
#     sys.exit(1)

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



# for r in radii:
#     for a in angles:
#         for o in angles:
#             print(m.get(r, a, o))




# measured_data = {}

# infile = args.infile
# if os.path.isdir(infile):
#     infile += "/raw.csv"
# with open(infile) as f:
#     measured_data = parse_csv(f)

# measured = Model.make_vector(measured_data, args.id)

# if args.radius == None:
#     print("Predicted radius:")
#     norms = dict([
#         (r, norm(measured, m.get(r, args.azimuth, args.orientation), 2))
#         for r in radii])
#     prediction = min(norms, key=norms.get)
#     print("{} cm".format(prediction))
# elif args.orientation == None:
#     print("Predicted tag orientation:")
#     norms = dict([
#         (orient, norm(measured, m.get(args.radius, args.azimuth, orient), 4))
#         for orient in angles])
#     prediction = min(norms, key=norms.get)
#     print("{} deg".format(prediction))
# else:
#     print("Predicted azimuth:")
#     norms = dict([
#         (az, norm(measured, m.get(args.radius, az, args.orientation), 2))
#         for az in angles])
#     prediction = min(norms, key=norms.get)
#     print("{} deg".format(prediction))




# # Print out table of model vectors for LaTeX
# for r in sorted(radii):
#     for o in sorted(angles):
#         for a in sorted(angles):
#             v = m.get(r, a, o)
#             print("{} & {} & {} & {:.3} & {:.3} & {:.3} \\\\".format(
#                 r, int(o), int(a), float(v[0]), float(v[1]), float(v[2])))




m2 = Model()

ids = []

for subdir in os.scandir("../Radial Straight"):
    if not subdir.is_dir():
        continue
    receiver_orientation = float(subdir.name[0:-4])
    with open(os.path.join(subdir.path, "raw.csv")) as f:
        dps = parse_csv(f)
        ids = Model._Model__get_ids(dps)
        m2.add_data(dps, 50, receiver_orientation)


num_correct = 0
total = 0
error = []
predictions = dict([(r, 0) for r in range(0, -50, -10)])
for receiver_orientation in angles:
    true_r = 50
    o = Model._Model__rel_angle(270, receiver_orientation)
    for id in ids:
        a = Model._Model__rel_angle(
            Model._Model__abs_azimuth(id),
            receiver_orientation
        )
        norms = dict([(r,
            norm(m2.get(true_r, a, o), m.get(r, a, o, only_r=False)))
            for r in radii])
        prediction = min(norms, key=norms.get)
        e = prediction - true_r
        predictions[e] += 1
        error.append(e)
        if prediction == true_r:
            num_correct += 1
        total += 1
print("Radius: {:.4}%, error: {:.4} cm, stdev: {:.4} cm".format(float(100*num_correct/total), float(st.mean(error)), float(st.stdev(error))))
# print((predictions[-10] + predictions[0])/total)
# plt.bar(
#     [i - 2.5 for i in predictions.keys()],
#     [i/total*100 for i in predictions.values()],
#     width=5)
# plt.title("Radius Prediction Accuracy")
# plt.xlabel("Error (cm)")
# plt.ylabel("Frequency (%)")
# # plt.show()
# plt.savefig(args.chart)

num_correct = 0
total = 0
error = []
predictions = dict([(float(a), 0) for a in range(-180, 180, 45)])
for receiver_orientation in angles:
    r = 50
    o = Model._Model__rel_angle(270, receiver_orientation)
    for id in ids:
        true_a = Model._Model__rel_angle(
            Model._Model__abs_azimuth(id),
            receiver_orientation
        )
        norms = dict([(a,
            norm(m2.get(r, true_a, o), m.get(r, a, o, only_a=False)))
            for a in angles])
        prediction = min(norms, key=norms.get)
        e = (prediction - true_a) % 360
        if e >= 180:
            e -= 360
        predictions[e] += 1
        error.append(e)
        if prediction == true_a:
            num_correct += 1
        total += 1
print("Azimuth: {:.4}%, error: {:.4} deg, stdev: {:.4} deg".format(float(100*num_correct/total), float(st.mean(error)), float(st.stdev(error))))
# print((predictions[-45.0] + predictions[0.0] + predictions[45.0])/total)
# plt.bar(
#     [i - 10 for i in predictions.keys()],
#     [i/total*100 for i in predictions.values()],
#     width=20)
# plt.title("Azimuth Prediction Accuracy")
# plt.xlabel("Error (deg)")
# plt.ylabel("Frequency (%)")
# # plt.show()
# plt.savefig(args.chart)


num_correct = 0
total = 0
error = []
predictions = dict([(float(a), 0) for a in range(-180, 180, 45)])
for receiver_orientation in angles:
    r = 50
    true_o = Model._Model__rel_angle(270, receiver_orientation)
    for id in ids:
        a = Model._Model__rel_angle(
            Model._Model__abs_azimuth(id),
            receiver_orientation
        )
        norms = dict([(o,
            norm(m2.get(r, a, true_o), m.get(r, a, o, only_o=False)))
            for o in angles])
        prediction = min(norms, key=norms.get)
        e = (prediction - true_o) % 360
        if e >= 180:
            e -= 360
        predictions[e] += 1
        error.append(e)
        if prediction == true_o:
            num_correct += 1
        total += 1
print("Orientation: {:.4}%, error: {:.4} deg, stdev: {:.4} deg".format(float(100*num_correct/total), float(st.mean(error)), float(st.stdev(error))))
# print((predictions[-45.0] + predictions[0.0] + predictions[45.0])/total)
# plt.bar(
#     [i - 10 for i in predictions.keys()],
#     [i/total*100 for i in predictions.values()],
#     width=20)
# plt.title("Orientation Prediction Accuracy")
# plt.xlabel("Error (deg)")
# plt.ylabel("Frequency (%)")
# # plt.show()
# plt.savefig(args.chart)



# predictions = dict([(a, 0) for a in angles])
# receiver_orientation = 90.0
# true_r = 50
# o = Model._Model__rel_angle(270, receiver_orientation)
# for id in ids:
#     true_a = Model._Model__rel_angle(
#         Model._Model__abs_azimuth(id),
#         receiver_orientation
#     )
#     norms = dict([(r,
#         norm(m2.get(true_r, true_a, o), m.get(r, a, o, only_r=False)))
#         for r in radii for a in angles])
#     prediction = min(norms, key=norms.get)
#     predictions[true_a] = prediction
# predictions[360.0] = predictions[0]
# plt.polar([np.radians(a) for a in angles+[360.0]],
#           [predictions[i] for i in sorted(predictions.keys())])
# plt.title("Radius Prediction Accuracy")
# plt.xlabel("Azimuth (deg)")
# plt.ylabel("Radius (cm)")
# # plt.show()
# plt.savefig(args.chart)