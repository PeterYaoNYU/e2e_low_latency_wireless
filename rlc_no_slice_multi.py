#!/usr/bin/env python3
import sys
import re
import os
import numpy as np
from collections import defaultdict

def parse_gnb_log_file(filename):
    """
    Parse a single gNB log file (e.g., gnb_log_1.log).
    Extract (time, buffer_size) per UE, using the 'RNTI->CU-UE-ID' mapping
    lines and the RLC buffer lines.

    Returns:
        dict: ue_data[ue_id] = list of (relative_time, buffer_size) across this file
    """
    # Regex to parse lines that map RNTI->CU-UE-ID
    # Example: "UE RNTI c566 CU-UE-ID 1 in-sync"
    rnti_map_pattern = re.compile(
        r'UE\s+RNTI\s+([0-9a-fA-F]+)\s+CU-UE-ID\s+(\d+)\s+in-sync'
    )

    # Regex for buffer lines:
    # Example: "[MAC] [gNB 1][ 100.123][100.123] DTCH1->DLSCH, RLC status for UE 50534: 1024 bytes in buffer"
    buffer_pattern = re.compile(
        r'\[MAC\]\s+\[gNB\s+\d+\]\[\s*\d+\.\d+\]\[(\d+\.\d+)\]\s+DTCH\d+->DLSCH,\s+'
        r'RLC status for UE\s+(\d+):\s+(\d+)\s+bytes in buffer'
    )

    # ue_data[ue_id] = list of (rel_time, buf_size)
    ue_data = defaultdict(list)

    # RNTI->UE-ID mapping: e.g., '50534' -> '1'
    rnti_to_cu_ue = {}

    first_timestamp = None

    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # A) Match RNTI->CU-UE-ID mapping lines
                rnti_match = rnti_map_pattern.search(line)
                if rnti_match:
                    hex_str, cu_ue_id_str = rnti_match.groups()
                    dec_val = int(hex_str, 16)
                    dec_str = str(dec_val)
                    rnti_to_cu_ue[dec_str] = cu_ue_id_str
                    continue

                # B) Match buffer lines
                buf_match = buffer_pattern.search(line)
                if buf_match:
                    t_str, rnti_dec_str, buf_str = buf_match.groups()
                    timestamp = float(t_str)
                    buffer_size = int(buf_str)

                    if first_timestamp is None:
                        first_timestamp = timestamp
                    rel_time = timestamp - first_timestamp

                    # Map the decimal RNTI to known UE ID, or "UNKNOWN"
                    ue_id_str = rnti_to_cu_ue.get(rnti_dec_str, "UNKNOWN")
                    # Store the data if it's a recognized UE ID (1..4) or keep all if you wish
                    ue_data[ue_id_str].append((rel_time, buffer_size))

    except FileNotFoundError:
        print(f"File not found: {filename}")
        return {}

    return ue_data

def aggregate_rlc_buffers(begin_idx, end_idx):
    """
    1. For each i in [begin_idx, end_idx], parse 'gnb_log_{i}.log'.
    2. Aggregate (time, buffer_size) data for each UE (1..4).
    3. Return aggregated dictionary of all data points across logs:
       ue_data_all[ue_id] = list of (time, buffer_size).
    """

    # We'll store all data across logs in this dict
    ue_data_all = {
        "1": [],
        "2": [],
        "3": [],
        "4": [],
        # If there might be other IDs or "UNKNOWN", we can store them too:
        # "UNKNOWN": []
    }

    for exp_idx in range(begin_idx, end_idx + 1):
        filename = f"gnb_log_{exp_idx}.log"
        if not os.path.isfile(filename):
            print(f"Warning: {filename} not found.")
            continue

        file_data = parse_gnb_log_file(filename)
        if not file_data:
            print(f"Warning: No valid data found in {filename}.")
            continue

        # Append the data from this file to the global container
        for ue_id, points in file_data.items():
            if ue_id not in ue_data_all:
                ue_data_all[ue_id] = []
            ue_data_all[ue_id].extend(points)

    return ue_data_all

def compute_means(ue_data, skip_first_60=False):
    """
    Given a list of (time, buffer_size) for a UE, compute the mean buffer occupancy.
    If skip_first_60=True, only consider points with time >= 60s.
    Returns 0.0 if no valid data points.
    """
    if not ue_data:
        return 0.0

    # Filter if skip_first_60 is True
    filtered = []
    for (t, buf) in ue_data:
        if skip_first_60 and t < 60:
            continue
        filtered.append(buf)

    if not filtered:
        return 0.0

    return float(np.mean(filtered))

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <begin_idx> <end_idx>")
        sys.exit(1)

    try:
        begin_idx = int(sys.argv[1])
        end_idx = int(sys.argv[2])
    except ValueError:
        print("Error: <begin_idx>, <end_idx> must be integers.")
        sys.exit(1)

    # 1) Parse all logs in [begin_idx, end_idx]
    ue_data_all = aggregate_rlc_buffers(begin_idx, end_idx)
    # ue_data_all["1"], ue_data_all["2"], ue_data_all["3"], ue_data_all["4"]

    # 2) Compute means overall and after 60 seconds, per UE
    #    Also compute combined mean for UE2,3,4.

    # We'll create a helper to fetch the mean for UE
    def get_means_for_ue(ue_id):
        # overall
        mean_overall = compute_means(ue_data_all[ue_id], skip_first_60=False)
        # after 60s
        mean_60 = compute_means(ue_data_all[ue_id], skip_first_60=True)
        return mean_overall, mean_60

    ue1_overall, ue1_60 = get_means_for_ue("1")
    ue2_overall, ue2_60 = get_means_for_ue("2")
    ue3_overall, ue3_60 = get_means_for_ue("3")
    ue4_overall, ue4_60 = get_means_for_ue("4")

    # 3) For UE2,3,4 combined, we unify their data, then compute mean
    ue234_all_data = ue_data_all["2"] + ue_data_all["3"] + ue_data_all["4"]
    ue234_overall = compute_means(ue234_all_data, skip_first_60=False)
    ue234_60 = compute_means(ue234_all_data, skip_first_60=True)

    # 4) Print results
    print("\n=== Aggregated RLC Buffer Statistics (No Slice) ===")
    print(f"Logs: gnb_log_{begin_idx}.log through gnb_log_{end_idx}.log\n")

    print("Per-UE Mean RLC Buffer Occupancy (Bytes), Overall vs After 60s:")
    print(f"  UE1 Overall = {ue1_overall:.2f}, After 60s = {ue1_60:.2f}")
    print(f"  UE2 Overall = {ue2_overall:.2f}, After 60s = {ue2_60:.2f}")
    print(f"  UE3 Overall = {ue3_overall:.2f}, After 60s = {ue3_60:.2f}")
    print(f"  UE4 Overall = {ue4_overall:.2f}, After 60s = {ue4_60:.2f}")

    print("\nUE2,3,4 Combined Mean RLC Buffer Occupancy (Bytes), Overall vs After 60s:")
    print(f"  Overall = {ue234_overall:.2f}, After 60s = {ue234_60:.2f}")

if __name__ == "__main__":
    main()
 