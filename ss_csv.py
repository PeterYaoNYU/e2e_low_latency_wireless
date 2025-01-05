#!/usr/bin/env python3
import sys
import os
import re
import csv
import statistics

def parse_srtt_from_log(log_file):
    """
    Parse a single ss-style log file to find srtt samples.
    Exclude fd=4 (control flow).
    
    Returns:
      flow_srtt_map: dict of { fd_number (int) : [list_of_srtt_floats] }
    """
    flow_srtt_map = {}
    # We'll keep track of the last fd encountered. If it's one of {5,7,9,11,...}
    # then the next line might contain 'rtt:' data we want.
    last_fd = None

    # Regex to find e.g. 'fd=5' in the line
    fd_pattern = re.compile(r'fd=(\d+)')
    # Regex to find e.g. rtt:110.093
    srtt_pattern = re.compile(r'rtt:(\d+\.\d+)')

    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line_stripped = line.strip()
            # Check if line has something like 'fd=7'
            match_fd = fd_pattern.search(line_stripped)
            if match_fd:
                fd_val = int(match_fd.group(1))
                # We'll store it if it's not 4
                if fd_val != 4:
                    last_fd = fd_val
                else:
                    last_fd = None  # ignore fd=4
            else:
                # If the last line had fd=5/7/9/11... then this line might have 'rtt:'
                if last_fd is not None:
                    match_srtt = srtt_pattern.search(line_stripped)
                    if match_srtt:
                        srtt_val = float(match_srtt.group(1))
                        flow_srtt_map.setdefault(last_fd, []).append(srtt_val)
                    # after reading potential srtt, reset
                    last_fd = None

    return flow_srtt_map


def is_cubic_file(filename):
    """
    Simple check if the filename indicates a 'cubic' file.
    """
    # e.g. "32-ss-cubic.txt", "32-ss-cubic-2.txt", "32-ss-cubic-3.txt"
    # Return True if it has '-ss-cubic' in it.
    # (We also skip 'prague' or anything else.)
    return ('-ss-cubic' in filename)


def main(start_idx, end_idx, prefix):
    """
    For each i in [start_idx, end_idx], parse these files if they exist:
      - {i}-ss-prague.txt
      - {i}-ss-cubic.txt
      - {i}-ss-cubic-2.txt
      - {i}-ss-cubic-3.txt

    Gather srtt samples for each flow (fd != 4).
    Then compute mean srtt per flow, also an 'ALL_FLOWS' aggregator for that file,
    also a 'ALL_CUBIC' aggregator across the 3 cubic files for that idx.
    
    Save to CSV: {prefix}_srtt_results.csv
       columns: idx, file, flow, mean_srtt
    """
    csv_rows = []

    # We'll keep a dictionary to sum up all cubic flows for each idx
    #   cubic_srtt_list[i] = [all srtt samples from the cubic files for idx i]
    cubic_srtt_list = {}

    # The candidate file patterns for each idx:
    # We can unify them in a list and loop
    def candidate_files(i):
        return [
            f"{i}-ss-prague.txt",
            f"{i}-ss-cubic.txt",
            f"{i}-ss-cubic-2.txt",
            f"{i}-ss-cubic-3.txt"
        ]

    for i in range(start_idx, end_idx + 1):
        for fname in candidate_files(i):
            if not os.path.isfile(fname):
                # skip if doesn't exist
                continue

            flow_srtt_map = parse_srtt_from_log(fname)
            # flow_srtt_map is { fd : [list_of_srtt_floats], ... }

            # Add rows for each fd
            for fd, srtt_samples in flow_srtt_map.items():
                if len(srtt_samples) > 0:
                    mean_val = statistics.mean(srtt_samples)
                    csv_rows.append({
                        "idx": i,
                        "file": fname,
                        "flow": str(fd),
                        "mean_srtt": f"{mean_val:.3f}"
                    })

            # Now aggregator for 'ALL_FLOWS' in this file
            all_samples_file = []
            for fd, srtt_samples in flow_srtt_map.items():
                all_samples_file.extend(srtt_samples)
            if all_samples_file:
                mean_file_srtt = statistics.mean(all_samples_file)
                csv_rows.append({
                    "idx": i,
                    "file": fname,
                    "flow": "ALL_FLOWS",
                    "mean_srtt": f"{mean_file_srtt:.3f}"
                })

            # If this is a cubic file, also gather them for the "ALL_CUBIC" aggregator
            if is_cubic_file(fname):
                cubic_srtt_list.setdefault(i, [])
                for fd, srtt_samples in flow_srtt_map.items():
                    cubic_srtt_list[i].extend(srtt_samples)

        # After we parse all 4 files for this idx, we can compute aggregator for "ALL_CUBIC"
        if i in cubic_srtt_list and len(cubic_srtt_list[i]) > 0:
            mean_cubic_srtt = statistics.mean(cubic_srtt_list[i])
            # Add a row representing "ALL_CUBIC" aggregator
            csv_rows.append({
                "idx": i,
                "file": "ALL_CUBIC",   # special placeholder
                "flow": "ALL_FLOWS",
                "mean_srtt": f"{mean_cubic_srtt:.3f}"
            })

    # Now write the CSV
    out_csv = f"{prefix}_srtt_results.csv"
    fieldnames = ["idx", "file", "flow", "mean_srtt"]
    with open(out_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"Saved SRTT results to {out_csv}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <start_idx> <end_idx> <prefix>")
        sys.exit(1)

    start_idx = int(sys.argv[1])
    end_idx = int(sys.argv[2])
    prefix = sys.argv[3]

    main(start_idx, end_idx, prefix)
