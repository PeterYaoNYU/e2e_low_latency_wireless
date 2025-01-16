#!/usr/bin/env python3
import sys
import re
import os
import numpy as np

def parse_fifo_file(filename):
    """
    Parse a single TBF qdisc monitor file line by line.

    Expected format (example line):
    ---------------------------------------------------------------------------
    1735868880.594344798 qdisc tbf 8004: root refcnt 2 rate 50Mbit ...
      ... Sent 1268961 bytes 916 pkt (dropped 0, overlimits 347 requeues 0)
      backlog 0b 0p requeues 0
    ---------------------------------------------------------------------------

    We extract:
    - timestamp (float) from the first token
    - dropped (cumulative integer) from "(dropped N, ...)"
    - backlog_bytes (integer) from "backlog Xb ..."
    - backlog_pkts (integer) from "... Yp"
    """
    times = []
    dropped_vals = []
    backlog_pkts = []
    backlog_bytes_vals = []
    
    begin_ts = -1

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) < 1:
                continue

            # 1) Parse timestamp from the first field
            try:
                ts = float(parts[0])
            except ValueError:
                # If the first token is not a float, skip
                continue
            
            if begin_ts < 0:
                begin_ts = ts
                print(f"Begin timestamp: {begin_ts}")
                
            if (ts - begin_ts) < 60:
                continue

            # 2) Extract 'dropped' using regex (dropped N, ...)
            dropped_match = re.search(r'\(dropped\s+(\d+),', line)
            if not dropped_match:
                continue
            dropped_cum = int(dropped_match.group(1))

            # 3) Extract backlog in bytes & packets: "backlog Xb Yp"
            backlog_match = re.search(r'backlog\s+(\d+)b\s+(\d+)p', line)
            if not backlog_match:
                continue
            backlog_bytes = int(backlog_match.group(1))
            backlog_pkts_val = int(backlog_match.group(2))

            # Store extracted values
            times.append(ts)
            dropped_vals.append(dropped_cum)
            backlog_pkts.append(backlog_pkts_val)
            backlog_bytes_vals.append(backlog_bytes)

    return times, dropped_vals, backlog_pkts, backlog_bytes_vals


def compute_mean_queue_delay(begin_idx, end_idx, link_speed_mbps):
    """
    1) For each experiment index in [begin_idx, end_idx], parse fifo_monitor_{i}.txt.
    2) Convert backlog_bytes to queue delay using:
         delay = (backlog_bytes * 8 bits) / link_speed_bps
       where link_speed_bps = link_speed_mbps * 1e6
    3) Accumulate all queue delays from all timestamps of all experiments in one list.
    4) Return the mean delay over that entire collection.
    """

    link_speed_bps = link_speed_mbps * 1e6
    all_delays = []

    for exp_idx in range(begin_idx, end_idx + 1):
        fname = f"fifo_monitor_{exp_idx}.txt"
        if not os.path.isfile(fname):
            print(f"Warning: File not found: {fname}")
            continue

        # Parse the file
        times, dropped_vals, backlog_pkts, backlog_bytes_vals = parse_fifo_file(fname)
        if not times:
            print(f"Warning: No valid data in {fname}")
            continue

        # Compute queue delays for each timestamp line
        for b_bytes in backlog_bytes_vals:
            delay_sec = (b_bytes * 8.0) / link_speed_bps
            if delay_sec > 0.1:
                continue
            all_delays.append(delay_sec)

    if not all_delays:
        return 0.0  # Or None, if you'd prefer

    return np.mean(all_delays), np.std(all_delays)


def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <begin_idx> <end_idx> <link_speed_mbps>")
        sys.exit(1)

    try:
        begin_idx = int(sys.argv[1])
        end_idx = int(sys.argv[2])
        link_speed = float(sys.argv[3])
    except ValueError:
        print("Error: <begin_idx>, <end_idx> must be integers and <link_speed_mbps> must be a float.")
        sys.exit(1)

    mean_delay, std_delay = compute_mean_queue_delay(begin_idx, end_idx, link_speed)
    print(f"=== Mean Queue Delay for experiments [{begin_idx}, {end_idx}] at {link_speed} Mbps ===")
    print(f"{mean_delay:.6f} seconds, std dev: {std_delay:.6f}")


if __name__ == "__main__":
    main()
