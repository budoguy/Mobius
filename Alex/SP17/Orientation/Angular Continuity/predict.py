#!/usr/bin/env python3

# import argparse
import os
import csv
import statistics as st
import numpy as np
import numpy.linalg as la

# arg_parser = argparse.ArgumentParser()
# arg_parser.add_argument("--angle", "-a",
#     help="angle to test",
#     type=float)
# arg_parser.add_argument("--distance", "-d",
#     help="distance to test",
#     type=int)
# args = arg_parser.parse_args()


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


training_datapoints = {}

for subdir in os.scandir("./Multiple distances"):
    if not subdir.is_dir():
        continue
    distance = int(subdir.name[0:2])
    angle = float(subdir.name[7:-4])
    with open(os.path.join(subdir.path, "raw.csv")) as f:
        if not angle in training_datapoints:
            training_datapoints[angle] = {}
        training_datapoints[angle][distance] = parse_csv(f)

measured_datapoints = {}

for subdir in os.scandir("./One distance"):
    if not subdir.is_dir():
        continue
    angle = float(subdir.name[:-4])
    with open(os.path.join(subdir.path, "raw.csv")) as f:
        measured_datapoints[angle] = parse_csv(f)


channels = [37, 38, 39]
angles = sorted(list(training_datapoints.keys()))
distances = sorted(list(training_datapoints[0.0].keys()))

model = \
    dict([(angle,
        dict([(dist,
            tuple(st.mean([dp["rssi"] for dp in
                training_datapoints[angle][dist] if dp["channel"] == ch])
            for ch in channels))
        for dist in distances]))
    for angle in angles])

measured = \
    dict([(angle,
        tuple(st.mean([dp["rssi"] for dp in
            measured_datapoints[angle] if dp["channel"] == ch])
        for ch in channels))
    for angle in angles])

print("Distance predictions:")
for angle in measured:
    norms = dict([(dist,
        la.norm(np.subtract(measured[angle], model[angle][dist]), ord=2))
        for dist in distances])
    predicted_distance = min(norms, key=norms.get)
    print("{:3} deg: {} cm".format(int(angle), predicted_distance))

print()
print("Orientation predictions:")
for actual_angle in angles:
    norms = dict([(angle,
        la.norm(np.subtract(measured[actual_angle], model[angle][20]), ord=4))
        for angle in angles])
    predicted_angle = min(norms, key=norms.get)
    predictions = [int(i) for i in sorted(norms, key=norms.get)]
    print("Actual: {:3} deg, Predicted: {}".format(int(actual_angle), predictions))
    # print("Actual: {:3} deg, Predicted: {:3} deg".format(int(actual_angle), int(predicted_angle)))
