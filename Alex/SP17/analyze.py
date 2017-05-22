#!/usr/bin/env python3

import argparse
import os
import io
import time
import serial
import csv
import statistics as st
import matplotlib.pyplot as plt


class __BinaryToText:
    ''' Converts a file opened in binary mode into text mode. '''
    def __init__(self, f):
        self.f = f

    def __iter__(self):
        return self

    def __next__(self):
        return self.f.readline().decode("ascii")


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


def calculate_stats(datapoints):
    ''' Calculate various statistics on the data set. '''
    stats = {}
    ids = __get_ids(datapoints)
    seq_num_received = dict([(tag, [dp["sequence_num"] for dp in datapoints if dp["tag_id"] == tag]) for tag in ids])
    stats["num_received"] = dict([(key, len(seq_num_received[key])) for key in seq_num_received])
    stats["num_expected"] = dict([(key, 1) for key in seq_num_received])
    for key in seq_num_received:
        prev = seq_num_received[key][0]
        for curr in seq_num_received[key][1:]:
            if curr > prev:
                stats["num_expected"][key] += curr - prev
            elif curr < prev:
                stats["num_expected"][key] += curr - prev + 256
            else:
                stats["num_expected"][key] += 1
            prev = curr
    stats["loss_rate"] = dict([(tag, round(1-stats["num_received"][tag]/stats["num_expected"][tag], 3)) for tag in ids])

    def fn_over_rssi(fn):
        return dict([(tag, round(fn([dp["rssi"] for dp in datapoints if dp["tag_id"] == tag]), 3)) for tag in ids])

    def fn_over_rssi_and_ch(fn):
        return dict([(tag, dict([(ch, round(fn([dp["rssi"] for dp in datapoints if dp["tag_id"] == tag and dp["channel"] == ch]), 3)) for ch in [37, 38, 39]])) for tag in ids])

    stats["rssi_avg"] = fn_over_rssi(st.mean)
    stats["rssi_sd"] = fn_over_rssi(st.stdev)
    stats["rssi_avg_by_ch"] = fn_over_rssi_and_ch(st.mean)
    stats["rssi_sd_by_ch"] = fn_over_rssi_and_ch(st.stdev)

    stats["predicted_order_naive"] = sorted(stats["rssi_avg"], key=stats["rssi_avg"].get, reverse=True)
    
    return stats


def parse_psd(f, tag_id=None):
    ''' Parse the TI sniffer save file. '''
    datapoints = []
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
        # TODO: most of this is hardly used - only needed for keeping
        # position while parsing. Try to optimize.
        p = {}
        p["info"] = ord(b)
        p["num"] = int.from_bytes(f.read(4), byteorder="little")
        p["timestamp"] = int.from_bytes(f.read(8), byteorder="little")
        p["length"] = int.from_bytes(f.read(2), byteorder="little")
        p["ble_length"] = ord(f.read(1))
        p["ble_access_addr"] = [b for b in reversed(f.read(4))]
        p["ble_header"] = int.from_bytes(f.read(2), byteorder="little")
        p["ble_adv_addr"] = [b for b in reversed(f.read(6))]
        p["ble_payload"] = f.read(p["ble_length"] - 17)
        p["ble_crc"] = int.from_bytes(f.read(3), byteorder="little")
        p["rssi"] = ord(f.read(1))
        p["status"] = ord(f.read(1))
        
        # Convert the data
        # Timestamp conversion from TI document # SWRU187G, page 23
        timeLo = p["timestamp"] & 0xFFFF
        timeHi = p["timestamp"] >> 16
        p["timestamp"] = (timeHi * 5000 + timeLo)//32000
        p["ble_seq_num"] = p["ble_payload"][2]
        p["rssi"] = p["rssi"] - 94 # Conversion determined empirically
        
        # Build the data point
        dp = {}
        dp["tag_id"] = tag_id if tag_id is not None else int(p["ble_adv_addr"][-1])
        dp["sequence_num"] = int(p["ble_seq_num"])
        dp["timestamp"] = int(p["timestamp"])
        dp["rssi"] = int(p["rssi"])
        # TODO: determine channel packet was received on
        datapoints.append(dp)
        
        # Skip to the next packet
        f.seek(256 - p["length"], io.SEEK_CUR)
    return datapoints


def parse_csv(f, dumpfile=None, tag_id=None):
    ''' Parse the CSV-formatted file or serial port output. '''
    datapoints = []
    if dumpfile:
        writer = csv.writer(dumpfile)
    reader = csv.reader(f)
    timestamp_offset = None
    startTime = time.time()
    for row in reader:
        if dumpfile:
            writer.writerow(row)
        dp = {}
        dp["tag_id"] = tag_id if tag_id is not None else int(row[0])
        dp["sequence_num"] = int(row[1])
        if timestamp_offset == None:
            timestamp_offset = int(row[2])
        dp["timestamp"] = int(row[2]) - timestamp_offset
        dp["rssi"] = int(row[3])
        dp["channel"] = __freq_to_channel_num(int(row[4]))
        datapoints.append(dp)
        if args.time != None and (time.time() - startTime) >= args.time:
            break
    return datapoints


def plot_data(datapoints, stats, filename=None, disp_chart=True):
    ''' Plot the data points. '''
    fig, axes = plt.subplots(nrows=2, ncols=3, figsize=(16, 9))
    plt.subplots_adjust(wspace=0.2, hspace=0.3, left=0.05, right=0.95, top=0.95, bottom=0.07)
    ids = __get_ids(datapoints)

    # RSSI over time, separated by channel
    for j, channel in enumerate([37, 38, 39]):
        ax = axes[j // 3][j % 3]
        for i in ids:
            timestamps = [dp["timestamp"]/1000 for dp in datapoints if dp["tag_id"] == i and dp["channel"] == channel]
            rssi = [dp["rssi"] for dp in datapoints if dp["tag_id"] == i and dp["channel"] == channel]
            ax.plot(timestamps, rssi)
        ax.set_title("Signal Strength, Channel {}".format(channel))
        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel("RSSI (dBm)")
        ax.legend(ids)
        ax.margins(y=0.1)
        ax.autoscale(tight=True)

    # RSSI over time, not separated
    ax = axes[1][0]
    for i in ids:
        timestamps = [dp["timestamp"]/1000 for dp in datapoints if dp["tag_id"] == i]
        rssi = [dp["rssi"] for dp in datapoints if dp["tag_id"] == i]
        ax.plot(timestamps, rssi)
    ax.set_title("Signal Strength, Channels 37-39")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("RSSI (dBm)")
    ax.legend(ids)
    ax.margins(y=0.1)
    ax.autoscale(tight=True)

    # RSSI standard deviation by channel
    ax = axes[1][1]
    bar_width = 1.0/(len(ids)*1.5)
    for i, id in enumerate(ids):
        index = [(i-(len(ids)-1)/2)*bar_width + j for j in range(4)]
        sds = [stats["rssi_sd"][id]] + list(stats["rssi_sd_by_ch"][id].values())
        color = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'b'][i]
        ax.bar(index, sds, width=bar_width, color=color, align='center')
    ax.set_title("Signal Strength Variability")
    ax.set_xlabel("Channel(s)")
    ax.set_ylabel("Standard deviation (dBm)")
    ax.set_xticks(range(4))
    ax.set_xticklabels(["all", "37", "38", "39"])
    ax.legend(ids)
    ax.set_xmargin(0.1)
    ax.autoscale()

    # Advertisement drift over time
    ax = axes[1][2]
    for i in ids:
        datapoints_for_tag = [dp for dp in datapoints if dp["tag_id"] == i]
        timestamps = [dp["timestamp"]/1000 for dp in datapoints_for_tag]
        timestamp_diffs = [0] + [curr["timestamp"] - prev["timestamp"] - \
                100*((curr["sequence_num"] - prev["sequence_num"]) % 256) \
                for prev, curr in zip(datapoints_for_tag, datapoints_for_tag[1:])]
        ax.plot(timestamps, timestamp_diffs)
    ax.set_title("Advertisement Jitter and Drift")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Period jitter (ms)")
    ax.legend(ids)
    ax.margins(y=1)
    ax.autoscale(tight=True)

    if filename:
        plt.savefig(filename)
    if disp_chart:
        plt.show()


def write_log(datapoints, f):
    ''' Write the data points to a log file. '''
    ids = __get_ids(datapoints)
    writer = csv.writer(f)
    writer.writerow(["Timestamp"] + ids)

    for dp in datapoints:
        row = [dp["timestamp"]] + [None]*len(ids)
        row[1 + ids.index(dp["tag_id"])] = dp["rssi"]
        writer.writerow(row)


def __main():
    datapoints = []
    for file_num, infile in enumerate(args.infiles):
        file_ext = os.path.splitext(infile)[1]
        dir_name = os.path.dirname(infile)
        renumbered_id = file_num+1 if args.renumber else None
        if file_ext == ".psd":
            with open(infile, "rb") as f:
                datapoints += parse_psd(f, tag_id=renumbered_id)
        elif dir_name == "/dev" or infile.startswith("COM"):
            if args.outdir:
                dumpfile = open(os.path.join(args.outdir, "raw.csv"), "w")
            f = serial.Serial(infile, baudrate=args.baud_rate)
            # Remove the first few lines, which are usually garbage
            for i in range(30):
                f.readline()
            datapoints += parse_csv(__BinaryToText(f), dumpfile, tag_id=renumbered_id)
            if args.outdir:
                dumpfile.close()
        elif os.path.isdir(infile):
            infile += "/raw.csv"
        with open(infile, "r") as f:
            datapoints += parse_csv(f, tag_id=renumbered_id)

    if args.outdir:
        with open(os.path.join(args.outdir, "log.csv"), "w") as f:
            write_log(datapoints, f)

    stats = calculate_stats(datapoints)
    # for tag in __get_ids(datapoints):
    #     print("Tag {}:".format(tag))
    #     print("  Loss: {:.3}%".format(float(stats["loss_rate"][tag])))
    #     print("  RSSI avg: {:.3} dBm".format(float(stats["rssi_avg"][tag])))
    #     print("  RSSI stddev: {:.3} dBm".format(float(stats["rssi_sd"][tag])))
    # print("Detected order: {}".format("".join(map(str, stats["predicted_order_naive"]))))
    # print(stats)

    if args.outdir:
        chart_filename = os.path.join(args.outdir, "chart.png")
    else:
        chart_filename = None
    plot_data(datapoints, stats, filename=chart_filename, disp_chart=args.disp_chart)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("infiles",
        help="data file(s) or serial port to analyze",
        nargs="+")
    arg_parser.add_argument("-o", "--outdir",
        help="directory to write output files")
    arg_parser.add_argument("-c", "--disp-chart",
        help="displays the chart",
        action="store_true")
    arg_parser.add_argument("-t", "--time",
        help="number of seconds to collect data",
        type=int)
    arg_parser.add_argument("-b", "--baud-rate",
        help="baud rate for serial port (default: 115200)",
        type=int, default=115200)
    arg_parser.add_argument("-r", "--renumber",
        help="renumber tag IDs starting from 1",
        action="store_true")
    args = arg_parser.parse_args()

    if args.outdir != None:
        if not os.path.exists(args.outdir):
            os.makedirs(args.outdir)

    __main()
