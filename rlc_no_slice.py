#!/usr/bin/env python3
import sys
import re
import matplotlib.pyplot as plt
from collections import defaultdict
import numpy as np

def plot_buffer_size_over_time(idx):
    """
    Parse gnb_log_{idx}.log, extract buffer size/time for each UE, map RNTI(hex)->CU-UE-ID,
    convert hex RNTI to decimal str to match the buffer lines, and plot buffer size over time.

    The plot is saved to 'gnb_log_{idx}_buffer_size.png'.

    Args:
        idx (int): Experiment index (to find gnb_log_{idx}.log).

    Returns:
        float or None:
            - If data is found, returns the smallest mean buffer occupancy among all UEs.
            - If no data is found, returns None.
    """
    filename = f"gnb_log_{idx}.log"

    # 1) Regex to parse lines that map RNTI->CU-UE-ID
    # Example: "UE RNTI c566 CU-UE-ID 1 in-sync"
    rnti_map_pattern = re.compile(
        r'UE\s+RNTI\s+([0-9a-fA-F]+)\s+CU-UE-ID\s+(\d+)\s+in-sync'
    )

    # 2) Regex for buffer lines:
    # Example: "[MAC] [gNB 1][ 100.123][100.123] DTCH1->DLSCH, RLC status for UE 50534: 1024 bytes in buffer"
    buffer_pattern = re.compile(
        r'\[MAC\]\s+\[gNB\s+\d+\]\[\s*\d+\.\d+\]\[(\d+\.\d+)\]\s+DTCH\d+->DLSCH, '
        r'RLC status for UE\s+(\d+):\s+(\d+)\s+bytes in buffer'
    )

    # Store data as ue_data[<decimal_str_rnti>] = [(rel_time, buffer_size)]
    ue_data = defaultdict(list)
    first_timestamp = None

    # RNTI->CU-UE (decimal str => "1"/"2" etc.)
    rnti_to_cu_ue = {}

    # Parse file
    try:
        with open(filename, 'r') as f:
            for line in f:
                # A) Match RNTI->CU-UE mapping lines
                rnti_match = rnti_map_pattern.search(line)
                if rnti_match:
                    hex_str, cu_ue_id = rnti_match.groups()
                    # Convert the hex RNTI to decimal
                    dec_val = int(hex_str, 16)
                    dec_str = str(dec_val)
                    # Map "50534" => "1" for example
                    rnti_to_cu_ue[dec_str] = cu_ue_id
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

                    ue_data[rnti_dec_str].append((rel_time, buffer_size))

    except FileNotFoundError:
        print(f"File not found: {filename}")
        return None

    if not ue_data:
        print(f"No relevant data found in the log file: {filename}")
        return None

    # Plot
    plt.figure(figsize=(10, 6))
    ue_means = {}

    for dec_rnti, data_points in ue_data.items():
        times, bufs = zip(*data_points)
        # Retrieve the mapped UE number; default to "UNKNOWN" if not found
        mapped_ue = rnti_to_cu_ue.get(dec_rnti, "UNKNOWN")
        label = f"RNTI-dec {dec_rnti} => UE{mapped_ue}"
        plt.scatter(times, bufs, label=label, s=10)

        mean_buf = np.mean(bufs)
        ue_means[dec_rnti] = mean_buf

    plt.xlabel("Time (s) [Relative to Start]")
    plt.ylabel("Buffer Size (Bytes)")
    plt.title(f"Buffer Size Over Time (Experiment {idx})")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()

    outname = f"gnb_log_{idx}_buffer_size.png"
    plt.savefig(outname)
    print(f"Plot saved to: {outname}")
    plt.show()

    # Summaries
    lowest_dec = min(ue_means, key=ue_means.get)
    lowest_val = ue_means[lowest_dec]
    others = [v for k, v in ue_means.items() if k != lowest_dec]
    other_mean = np.mean(others) if others else 0

    print("\n=== Summary of Mean Buffer Occupancies ===")
    # Print both RNTI-dec and mapped UE
    for dec_rnti in sorted(ue_means.keys(), key=lambda x: int(x)):
        mapped_ue = rnti_to_cu_ue.get(dec_rnti, "UNKNOWN")
        print(f"  RNTI-dec {dec_rnti} => UE{mapped_ue}, mean {ue_means[dec_rnti]:.2f} bytes")

    print("\n=== UE (RNTI-dec) with the Smallest Mean Buffer Occupancy ===")
    mapped_lowest = rnti_to_cu_ue.get(lowest_dec, "UNKNOWN")
    print(f"  -> RNTI-dec {lowest_dec} => UE{mapped_lowest} has mean {lowest_val:.2f} bytes")

    print("\n=== Mean Buffer Occupancy of All Other RNTIs ===")
    if others:
        print(f"  -> Mean of others: {other_mean:.2f} bytes")
    else:
        print("  -> No other UEs found.")

    return lowest_val


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <experiment_idx>")
        sys.exit(1)

    try:
        exp_idx = int(sys.argv[1])
    except ValueError:
        print("Experiment index must be an integer.")
        sys.exit(1)

    plot_buffer_size_over_time(exp_idx)
