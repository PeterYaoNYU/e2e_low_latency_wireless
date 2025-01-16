#!/usr/bin/env python3
import sys
import re
import os
from collections import defaultdict
import numpy as np

def analyze_logs_for_range(begin_idx, end_idx):
    """
    1) Parse log files gnb_log_{i}.log for i in [begin_idx, end_idx].
    2) Collect RLC buffer sizes per UE and per slice.
    3) Compute overall and post-60s means (across all experiments).
    4) Print the final statistics without plotting.
    """

    # Regex to map RNTI->CU-UE-ID
    # e.g. "UE RNTI c566 CU-UE-ID 1 in-sync..."
    rnti_map_pattern = re.compile(
        r'UE\s+RNTI\s+([0-9a-fA-F]+)\s+CU-UE-ID\s+(\d+)\s+in-sync'
    )

    # Regex for slice-based buffer lines:
    #   [MAC] [gNB X][ 100.123][100.123] DTCH->DLSCH, RLC status for UE 50534, slice 2: 1024 bytes in buffer
    pattern = re.compile(
        r'\[MAC\]\s+\[gNB\s+\d+\]\[\s*\d+\.\d+\]\[(\d+\.\d+)\]\s+DTCH\d*->DLSCH,\s+'
        r'RLC status for UE\s+(\d+),\s*slice\s+(\d+):\s+(\d+)\s+bytes in buffer'
    )

    # For aggregating data across experiments
    # We'll store data separately for each UE and each slice.
    #   data_ue[ue_id]["all"] -> list of buffer sizes from t>=0
    #   data_ue[ue_id]["post60"] -> list of buffer sizes from t>60
    data_ue = defaultdict(lambda: {"all": [], "post60": []})

    #   data_slice[slice_id]["all"] -> list of buffer sizes
    #   data_slice[slice_id]["post60"] -> list of buffer sizes
    data_slice = defaultdict(lambda: {"all": [], "post60": []})

    # Process each experiment index in [begin_idx, end_idx]
    for exp_idx in range(begin_idx, end_idx + 1):
        filename = f"gnb_log_{exp_idx}.log"
        if not os.path.isfile(filename):
            print(f"Warning: File not found: {filename}")
            continue

        rnti_to_cu_ue = {}
        first_timestamp = None

        # Read the file line by line
        with open(filename, "r") as f:
            for line in f:
                # A) RNTI->CU-UE mapping lines
                rnti_match = rnti_map_pattern.search(line)
                if rnti_match:
                    hex_str, cu_ue_id_str = rnti_match.groups()
                    dec_val = int(hex_str, 16)
                    rnti_to_cu_ue[str(dec_val)] = cu_ue_id_str
                    continue

                # B) Slice buffer lines
                buf_match = pattern.search(line)
                if buf_match:
                    t_str, dec_rnti_str, slice_id_str, buf_str = buf_match.groups()
                    timestamp = float(t_str)
                    buffer_size = int(buf_str)

                    if first_timestamp is None:
                        first_timestamp = timestamp
                    rel_time = timestamp - first_timestamp

                    # Map dec_rnti_str -> CU-UE-ID (default to "UNKNOWN" if not found)
                    cu_ue_id_str = rnti_to_cu_ue.get(dec_rnti_str, "UNKNOWN")

                    # Store data for recognized UEs only, if you want to skip "UNKNOWN"
                    # or any other IDs. Here, we'll store everything, but only compute
                    # final stats for UEs 1..4 below.
                    data_ue[cu_ue_id_str]["all"].append(buffer_size)
                    if rel_time > 60:
                        data_ue[cu_ue_id_str]["post60"].append(buffer_size)

                    # Also store data by slice (1..2)
                    data_slice[slice_id_str]["all"].append(buffer_size)
                    if rel_time > 60:
                        data_slice[slice_id_str]["post60"].append(buffer_size)

    # Now compute the mean buffer sizes across ALL experiments for:
    #   1) Each UE = 1..4  (since you said "4 UEs in total")
    #   2) Each slice = 1..2

    print("\n=== Overall Mean RLC Buffer Size by UE (aggregated across all experiments) ===")
    print("    (Including t=0 onward) and (After 60s)\n")

    for ue_id in ["1", "2", "3", "4"]:
        ue_all = data_ue[ue_id]["all"]
        ue_post60 = data_ue[ue_id]["post60"]

        if ue_all:
            mean_all = np.mean(ue_all)
        else:
            mean_all = 0.0

        if ue_post60:
            mean_post60 = np.mean(ue_post60)
        else:
            mean_post60 = 0.0

        print(f"UE{ue_id}: mean(all)={mean_all:.2f} bytes, mean(>60s)={mean_post60:.2f} bytes")

    print("\n=== Overall Mean RLC Buffer Size by Slice (aggregated across all experiments) ===")
    print("    (Including t=0 onward) and (After 60s)\n")

    for slice_id_str in ["1", "2"]:
        sl_all = data_slice[slice_id_str]["all"]
        sl_post60 = data_slice[slice_id_str]["post60"]

        if sl_all:
            mean_all = np.mean(sl_all)
        else:
            mean_all = 0.0

        if sl_post60:
            mean_post60 = np.mean(sl_post60)
        else:
            mean_post60 = 0.0

        print(f"Slice {slice_id_str}: mean(all)={mean_all:.2f} bytes, mean(>60s)={mean_post60:.2f} bytes")


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <begin_idx> <end_idx>")
        sys.exit(1)

    try:
        begin_idx = int(sys.argv[1])
        end_idx = int(sys.argv[2])
    except ValueError:
        print("Error: begin_idx and end_idx must be integers.")
        sys.exit(1)

    analyze_logs_for_range(begin_idx, end_idx)


if __name__ == "__main__":
    main()
