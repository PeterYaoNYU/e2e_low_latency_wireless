#!/usr/bin/env python3
import sys
import os
import json
import csv
import statistics

def parse_iperf_json(json_filename):
    """
    Parse a single iperf JSON file to extract:
      - Per-flow throughput from "end" -> "streams" -> "sender" -> "bits_per_second"
      - 'socket' as an ID for the flow

    Returns:
        flows_data (list of dict): one dict per flow, e.g.:
            [
              {
                "socket": 5,
                "mbps": 1.4039801869286518,   # bits_per_second / 1e6
                "file": "32-iperf-cubic.json"
              },
              ...
            ]
        total_mbps (float): sum of all flow bitrates (in Mbps, sender side)
    """
    flows_data = []
    total_mbps = 0.0

    try:
        with open(json_filename, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Could not open or parse {json_filename}")
        return flows_data, total_mbps

    # The structure we care about is typically in data["end"]["streams"]
    end_block = data.get("end", {})
    streams = end_block.get("streams", [])

    for flow in streams:
        sender_info = flow.get("sender", {})
        bps = sender_info.get("bits_per_second", 0.0)
        sock = sender_info.get("socket", None)
        mbps = bps / 1e6  # convert to Mbps

        flows_data.append({
            "socket": sock,
            "mbps": mbps,
            "file": os.path.basename(json_filename)
        })
        total_mbps += mbps

    return flows_data, total_mbps


def main(start_idx, end_idx, prefix):
    """
    Parse iperf JSON files for each idx in [start_idx, end_idx], specifically:
       {idx}-iperf-cubic.json
       {idx}-iperf-cubic-2.json
       {idx}-iperf-cubic-3.json
       {idx}-iperf-prague.json

    Write out:
     1) A CSV file with all per-flow data in Mbps:  {prefix}_iperf_results.csv
        - One row per flow + one row for the file-level sum ("socket"=ALL_FLOWS)

     2) Another CSV {prefix}_iperf_results_multi_ue.csv summarizing:
        - Mean & std dev of each cubic “UE” (socket) across runs
        - Combined (sum) throughput of all cubic flows across runs
        - Same for prague

    Usage: parse_iperf.py <start_idx> <end_idx> <prefix>
    """
    # This will store detailed per-flow rows
    csv_rows = []

    # We'll keep track of each (socket, filename) throughput across runs,
    # if you want more granular stats. But for your multi-UE summary, we also
    # want to group by "cubic" or "prague".
    flows_across_runs = {}   # key=(socket, file), val=list of mbps across runs

    # We'll track throughput of each "UE" (i.e., socket) under "cubic" or "prague".
    #   cubic_ue_across_runs[socket] = [list of total mbps across runs]
    #   prague_ue_across_runs[socket] = ...
    cubic_ue_across_runs = {}
    prague_ue_across_runs = {}

    # We'll also track the sum of all cubic flows in each run, and sum of all prague flows
    #   cubic_sum_per_run[idx] = total_mbps
    #   prague_sum_per_run[idx] = total_mbps
    cubic_sum_per_run = {}
    prague_sum_per_run = {}

    # 1) Loop over each idx
    for i in range(start_idx, end_idx + 1):
        # The 4 candidate files
        candidate_files = [
            f"{i}-iperf-cubic.json",
            f"{i}-iperf-cubic-2.json",
            f"{i}-iperf-cubic-3.json",
            f"{i}-iperf-prague.json"
        ]

        # Initialize sums for cubic & prague in this run
        cubic_sum_run = 0.0
        prague_sum_run = 0.0

        for fname in candidate_files:
            if not os.path.exists(fname):
                continue

            flows, total_mbps = parse_iperf_json(fname)
            # 2) Save a row for each flow
            for flow in flows:
                socket_num = flow["socket"]
                mbps = flow["mbps"]

                # Add this row to the big CSV listing
                csv_rows.append({
                    "idx": i,
                    "file": fname,
                    "socket": socket_num,
                    "mbps": mbps
                })

                # Keep in a dictionary for per-(socket, file) stats
                key = (socket_num, fname)
                if key not in flows_across_runs:
                    flows_across_runs[key] = []
                flows_across_runs[key].append(mbps)

                # If this is cubic, store under cubic_ue_across_runs
                if "cubic" in fname:
                    cubic_sum_run += mbps
                    if socket_num not in cubic_ue_across_runs:
                        cubic_ue_across_runs[socket_num] = []
                    cubic_ue_across_runs[socket_num].append(mbps)
                elif "prague" in fname:
                    prague_sum_run += mbps
                    if socket_num not in prague_ue_across_runs:
                        prague_ue_across_runs[socket_num] = []
                    prague_ue_across_runs[socket_num].append(mbps)

            # Add a row for the total in that file
            csv_rows.append({
                "idx": i,
                "file": fname,
                "socket": "ALL_FLOWS",
                "mbps": total_mbps
            })

        # track sums for this entire run
        cubic_sum_per_run[i] = cubic_sum_run
        prague_sum_per_run[i] = prague_sum_run

    # 3) Write the main CSV (per-flow lines)
    csv_filename = f"{prefix}_iperf_results.csv"
    fieldnames = ["idx", "file", "socket", "mbps"]
    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"Saved detailed per-flow CSV to: {csv_filename}")

    # 4) Summaries: compute mean & stdev for each socket under cubic, prague,
    #    plus the "ALL" sum across runs for cubic & prague.

    # For each run i, we have cubic_sum_per_run[i] and prague_sum_per_run[i].
    # We'll store them in lists for stats across runs.
    cubic_sum_vals = [cubic_sum_per_run[idx] for idx in range(start_idx, end_idx + 1)]
    prague_sum_vals = [prague_sum_per_run[idx] for idx in range(start_idx, end_idx + 1)]

    # We'll create a second CSV with lines for:
    #   type (cubic/prague), ue (socket or "ALL"),
    #   mean_mbps, std_mbps, n
    multi_ue_rows = []
    def compute_mean_std(values):
        if len(values) == 0:
            return (0.0, 0.0, 0)
        if len(values) == 1:
            return (values[0], 0.0, 1)
        return (statistics.mean(values), statistics.pstdev(values), len(values))

    # (a) For cubic UEs
    for sock, values in cubic_ue_across_runs.items():
        mu, sd, n = compute_mean_std(values)
        multi_ue_rows.append({
            "type": "cubic",
            "ue": str(sock),
            "mean_mbps": mu,
            "std_mbps": sd,
            "count": n
        })

    # (b) For the "ALL" cubic sum across runs
    mu, sd, n = compute_mean_std(cubic_sum_vals)
    multi_ue_rows.append({
        "type": "cubic",
        "ue": "ALL",
        "mean_mbps": mu,
        "std_mbps": sd,
        "count": n
    })

    # (c) For prague UEs
    for sock, values in prague_ue_across_runs.items():
        mu, sd, n = compute_mean_std(values)
        multi_ue_rows.append({
            "type": "prague",
            "ue": str(sock),
            "mean_mbps": mu,
            "std_mbps": sd,
            "count": n
        })

    # (d) For the "ALL" prague sum across runs
    mu, sd, n = compute_mean_std(prague_sum_vals)
    multi_ue_rows.append({
        "type": "prague",
        "ue": "ALL",
        "mean_mbps": mu,
        "std_mbps": sd,
        "count": n
    })

    # 5) Write the multi-UE summary CSV
    multi_filename = f"{prefix}_iperf_results_multi_ue.csv"
    fieldnames2 = ["type", "ue", "mean_mbps", "std_mbps", "count"]
    with open(multi_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames2)
        writer.writeheader()
        writer.writerows(multi_ue_rows)

    print(f"Saved multi-UE summary CSV to: {multi_filename}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <start_idx> <end_idx> <prefix>")
        sys.exit(1)

    start_idx = int(sys.argv[1])
    end_idx = int(sys.argv[2])
    prefix = sys.argv[3]
    main(start_idx, end_idx, prefix)
