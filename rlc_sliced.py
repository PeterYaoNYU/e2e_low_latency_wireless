#!/usr/bin/env python3
import sys
import re
import matplotlib.pyplot as plt
from collections import defaultdict
import numpy as np

def plot_buffer_size_over_time_slice(idx):
    """
    Parse gnb_log_{idx}.log for slice-based info:
      - time
      - (UE RNTI, slice)
      - buffer_size
    Also parse lines like "UE RNTI c566 CU-UE-ID 1 in-sync..." to map RNTI(hex) -> CU-UE-ID,
    converting the hex RNTI to decimal for consistent matching with buffer lines.

    Then we plot (UE, slice) buffer size over time, plus print stats for each slice.

    The resulting plot is saved to 'gnb_log_{idx}_slice_buffer_size.png'.
    """
    filename = f"gnb_log_{idx}.log"

    # 1) Regex to map RNTI->CU-UE-ID
    # e.g. "UE RNTI c566 CU-UE-ID 1 in-sync..."
    rnti_map_pattern = re.compile(
        r'UE\s+RNTI\s+([0-9a-fA-F]+)\s+CU-UE-ID\s+(\d+)\s+in-sync'
    )

    # 2) Regex for slice-based buffer lines:
    # [MAC] [gNB X][ 100.123][100.123] DTCH->DLSCH, RLC status for UE 50534, slice 2: 1024 bytes in buffer
    pattern = re.compile(
        r'\[MAC\]\s+\[gNB\s+\d+\]\[\s*\d+\.\d+\]\[(\d+\.\d+)\]\s+DTCH\d+->DLSCH,\s+'
        r'RLC status for UE\s+(\d+),\s*slice\s+(\d+):\s+(\d+)\s+bytes in buffer'
    )

    ue_data = defaultdict(list)       # {(dec_rnti_str, slice_id): [(rel_time, buf_size)]}
    ue_data_valid = defaultdict(list) # for t>60
    first_timestamp = None

    # RNTI map: decimal str => CU-UE-ID
    rnti_to_cu_ue = {}

    # Parse
    try:
        with open(filename, 'r') as f:
            for line in f:
                # A) RNTI->CU-UE mapping lines
                rnti_match = rnti_map_pattern.search(line)
                if rnti_match:
                    hex_str, cu_ue_id = rnti_match.groups()
                    # Convert hex RNTI to decimal
                    dec_val = int(hex_str, 16)
                    dec_str = str(dec_val)
                    rnti_to_cu_ue[dec_str] = cu_ue_id
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

                    ue_data[(dec_rnti_str, slice_id_str)].append((rel_time, buffer_size))
                    if rel_time > 60:
                        ue_data_valid[(dec_rnti_str, slice_id_str)].append((rel_time, buffer_size))

    except FileNotFoundError:
        print(f"File {filename} not found.")
        return

    if not ue_data:
        print(f"No relevant data found in the log file: {filename}")
        return

    # Plot
    plt.figure(figsize=(10,6))
    for (dec_rnti_str, slice_id), data_points in ue_data.items():
        times, bufs = zip(*data_points)
        # Retrieve the mapped UE number; default to "UNKNOWN" if not found
        mapped_ue = rnti_to_cu_ue.get(dec_rnti_str, "UNKNOWN")
        label = f"RNTI-dec {dec_rnti_str} => UE{mapped_ue}, slice {slice_id}"
        plt.scatter(times, bufs, label=label, s=10)

    plt.xlabel("Time (s) [Relative to Start]")
    plt.ylabel("Buffer Size (Bytes)")
    plt.title(f"(UE, Slice) Buffer Size Over Time (Experiment {idx})")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()

    # Save the plot
    outfile = f"gnb_log_{idx}_slice_buffer_size.png"
    plt.savefig(outfile)
    print(f"Plot saved to: {outfile}")
    plt.show()

    # Print stats

    # A) Overall mean occupancy per (UE RNTI-dec, slice)
    print(f"\n=== Experiment {idx}: Overall mean buffer occupancy for each (UE-dec, slice) ===")
    for (dec_rnti_str, slice_id), data_points in ue_data.items():
        _, bufs = zip(*data_points)
        mean_val = np.mean(bufs)
        mapped_ue = rnti_to_cu_ue.get(dec_rnti_str, "UNKNOWN")
        print(f"  RNTI-dec {dec_rnti_str} => UE{mapped_ue}, slice {slice_id}, mean: {mean_val:.2f} bytes")

    # B) Mean occupancy AFTER 60s
    print(f"\n=== Experiment {idx}: Mean buffer occupancy AFTER 60s for each (UE-dec, slice) ===")
    if ue_data_valid:
        for (dec_rnti_str, slice_id), data_points in ue_data_valid.items():
            _, bufs = zip(*data_points)
            mean_val = np.mean(bufs)
            mapped_ue = rnti_to_cu_ue.get(dec_rnti_str, "UNKNOWN")
            print(f"  RNTI-dec {dec_rnti_str} => UE{mapped_ue}, slice {slice_id}, mean after 60s: {mean_val:.2f} bytes")
    else:
        print("  No data found after 60s.")

    # C) slice=2 overall mean across all UEs
    slice2_bufs = []
    for (dec_rnti_str, slice_id), data_points in ue_data.items():
        if slice_id == "2":
            for _, b in data_points:
                slice2_bufs.append(b)

    if slice2_bufs:
        slice2_mean = np.mean(slice2_bufs)
        print(f"\n=== Slice=2 overall mean across all UEs: {slice2_mean:.2f} bytes")
    else:
        print("\n=== No data found for slice=2 overall.")

    # D) slice=2 mean after 60s across all UEs
    slice2_bufs_60 = []
    for (dec_rnti_str, slice_id), data_points in ue_data_valid.items():
        if slice_id == "2":
            for _, b in data_points:
                slice2_bufs_60.append(b)

    if slice2_bufs_60:
        slice2_mean_60s = np.mean(slice2_bufs_60)
        print(f"=== Slice=2 mean after 60s across all UEs: {slice2_mean_60s:.2f} bytes")
    else:
        print("=== No data found for slice=2 after 60s.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <experiment_idx>")
        sys.exit(1)

    try:
        exp_idx = int(sys.argv[1])
    except ValueError:
        print("Experiment index must be an integer.")
        sys.exit(1)

    plot_buffer_size_over_time_slice(exp_idx)
