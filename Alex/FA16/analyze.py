#!/usr/bin/env python3

import argparse
import os
import subprocess
import io
import time
# import serial
import csv
import statistics as st
import itertools

parser = argparse.ArgumentParser()
parser.add_argument("data",
    help="data to analyze")
parser.add_argument("-o", "--out",
    help="path and prefix of files to output (overrides other output options)")
parser.add_argument("-l", "--log",
    help="log file to output")
parser.add_argument("-c", "--chart",
    help="chart file to output")
parser.add_argument("-d", "--uart-dump",
    help="file to dump serial output")
parser.add_argument("-n", "--num",
    help="number of data points to collect",
    type=int)
parser.add_argument("-t", "--time",
    help="number of seconds of data points to collect",
    type=int)
args = parser.parse_args()

if args.out != None:
    args.log = args.out + "_processed.csv"
    args.chart = args.out + ".png"
    args.uart_dump = args.out + ".csv"

if args.num != None and args.time != None:
    print("Do not provide both --num and --time")
    sys.exit(1)

class Packet:
    def __init__(self):
        self.info = None
        self.num = None
        self.timestamp = None
        self.length = None
        self.ble_length = None
        self.ble_access_addr = None
        self.ble_header = None
        self.ble_adv_addr = None
        self.ble_payload = None
        self.ble_crc = None
        self.rssi = None
        self.status = None
        self.ble_seq_num = None

class DataPoint:
    def __init(self):
        self.tag_id = None
        self.sequence_num = None
        self.timestamp = None
        self.rssi = None
        self.receive_interval = None

def getIds(datapoints):
    # Get a list of tag IDs that were detected
    ids = []
    for dp in datapoints:
        if dp.tag_id not in ids:
            ids.append(dp.tag_id)
    return sorted(ids)

def calculateStats(datapoints):
    ids = getIds(datapoints)
    seq_num_received = dict([(tag, [dp.sequence_num for dp in datapoints if dp.tag_id == tag]) for tag in ids])
    num_received = dict([(key, len(seq_num_received[key])) for key in seq_num_received])
    num_expected = dict([(key, 1) for key in seq_num_received])
    for key in seq_num_received:
        lst = seq_num_received[key]
        prev = lst[0]
        for curr in lst[1:]:
            if curr > prev:
                num_expected[key] += curr - prev
            elif curr < prev:
                num_expected[key] += curr - prev + 256
            else:
                num_expected[key] += 1
            prev = curr

    avg_rssi = dict([(tag, st.mean([dp.rssi for dp in datapoints if dp.tag_id == tag])) for tag in ids])
    sd_rssi = dict([(tag, st.stdev([dp.rssi for dp in datapoints if dp.tag_id == tag])) for tag in ids])

    for tag in ids:
        print("Tag {}:".format(tag))
        print("  Packets received: {}".format(num_received[tag]))
        print("  Packets expected: {}".format(num_expected[tag]))
        print("  Loss: {:.3}%".format(float((1-num_received[tag]/num_expected[tag])*100)))
        print("  RSSI avg: {:.3} dBm".format(float(avg_rssi[tag])))
        print("  RSSI stddev: {:.3} dBm".format(float(sd_rssi[tag])))

    order = sorted(avg_rssi, key=avg_rssi.get, reverse=True)
    print("Detected order: {}".format("".join(map(str, order))))

datapoints = []

ext = os.path.splitext(args.data)[1]
if ext == ".psd":
    with open(args.data, "rb") as f:
        while True:
            b = f.read(1)
            # Check for EOF
            if not b:
                break
            # Skip nonstandard packets
            if b != b"\x01":
                f.seek(256, io.SEEK_CUR)
                continue
            
            # Read out the data
            p = Packet()
            p.info = ord(b)
            p.num = int.from_bytes(f.read(4), byteorder="little")
            p.timestamp = int.from_bytes(f.read(8), byteorder="little")
            p.length = int.from_bytes(f.read(2), byteorder="little")
            p.ble_length = ord(f.read(1))
            p.ble_access_addr = [b for b in reversed(f.read(4))]
            p.ble_header = int.from_bytes(f.read(2), byteorder="little")
            p.ble_adv_addr = [b for b in reversed(f.read(6))]
            p.ble_payload = f.read(p.ble_length - 17)
            p.ble_crc = int.from_bytes(f.read(3), byteorder="little")
            p.rssi = ord(f.read(1))
            p.status = ord(f.read(1))
            
            # Convert the data
            # Timestamp conversion from TI document # SWRU187G, page 23
            timeLo = p.timestamp & 0xFFFF
            timeHi = p.timestamp >> 16
            p.timestamp = (timeHi * 5000 + timeLo)//32000
            p.ble_seq_num = p.ble_payload[2]
            p.rssi = p.rssi - 94 # Conversion determined empirically
            
            # Build the data point
            dp = DataPoint()
            dp.tag_id = int(p.ble_adv_addr[-1])
            dp.sequence_num = int(p.ble_seq_num)
            dp.timestamp = int(p.timestamp)
            dp.rssi = int(p.rssi)
            datapoints.append(dp)
            
            # Skip to the next packet
            f.seek(256 - p.length, io.SEEK_CUR)

else:
    with open(args.data, "r") as f:
        if os.path.dirname(args.data) == "/dev":
            subprocess.call(["stty", "-f", args.data, "115200"])
            print("Waiting for port to settle...")
            f.seek(200)
            startTime = time.time()
            while time.time() - startTime <= 3:
                f.readline()
            print("Collecting data...")
        f2 = None
        writer = None
        if args.uart_dump:
            f2 = open(args.uart_dump, "w")
            writer = csv.writer(f2)
        reader = csv.reader(f)
        timestampOffset = None
        startTime = time.time()
        receive_interval = 0
        for row in reader:
            if args.uart_dump:
                writer.writerow(row)
            dp = DataPoint()
            if row[0] != "--":
                dp.tag_id = int(row[0])
                dp.sequence_num = int(row[1])
                if timestampOffset == None:
                    timestampOffset = int(row[2])
                dp.timestamp = int(row[2]) - timestampOffset
                dp.rssi = int(row[3])
                dp.receive_interval = receive_interval
                datapoints.append(dp)
                if args.num != None and reader.line_num >= args.num:
                    break
            else:
                calculateStats([i for i in datapoints if i.receive_interval == receive_interval])
                receive_interval = float(row[2])
                print("Receive interval: {}ms".format(receive_interval))
            if args.time != None and (time.time() - startTime) >= args.time:
                break
        if args.uart_dump:
            f2.close()

ids = getIds(datapoints)

# Generate the output file
if args.log:
    with open(args.log, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp"] + ids)

        for dp in datapoints:
            row = [dp.timestamp] + [None]*len(ids)
            row[1 + ids.index(dp.tag_id)] = dp.rssi
            writer.writerow(row)

print("---------------------------")
print("Overall statistics:")
calculateStats(datapoints)

# Plot the data
if args.chart != "none":
    import matplotlib.pyplot as plt

    markers = itertools.cycle(('^', 'o', 's', 'D', '+', '*')) 
    for i in ids:
        plt.plot(
            [dp.timestamp/1000 for dp in datapoints if dp.tag_id == i],
            [dp.rssi for dp in datapoints if dp.tag_id == i],
            # marker=next(markers)
        )
    plt.margins(y=0.1)
    plt.autoscale(tight=True)
    plt.xlabel("Time (sec)")
    plt.ylabel("RSSI (dBm)")
    plt.legend(ids)
    if not args.chart:
        plt.show()
    else:
        plt.savefig(args.chart)