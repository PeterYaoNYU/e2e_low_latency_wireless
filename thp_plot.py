#!/usr/bin/env python3
import sys
import csv
import statistics
import os
import re
import matplotlib.pyplot as plt

def file_to_ue_type(filename):
    """
    Given a filename like "32-iperf-cubic.json", "32-iperf-cubic-2.json", etc.,
    return a string that identifies the 'UE type':
      "prague", "cubic1", "cubic2", "cubic3"
    """
    # We'll check for 'prague' vs 'cubic'
    # Then check for the suffix '-2' or '-3'
    # This function is just an example; adapt if your naming is different.
    fname = os.path.basename(filename).lower()
    if "prague" in fname:
        return "prague"
    if "cubic" in fname:
        # Check if it matches "-cubic-2.json" or "-cubic-3.json"
        if "-cubic-2.json" in fname:
            return "cubic2"
        elif "-cubic-3.json" in fname:
            return "cubic3"
        else:
            # default: "cubic1"
            return "cubic1"
    return "unknown"

def main(prefix):
    """
    Reads the CSV file {prefix}_iperf_results.csv with columns:
       idx, file, socket, bits_per_second

    Produces two plots (saved as PDF):
      1) Per-UE (prague, cubic combined, cubic1, cubic2, cubic3) across runs
         -> each bar is the mean throughput, error bar is stdev.
      2) Per-flow, each bar is a distinct flow (type + socket),
         plus "combined" flows for each socket across cubic1, cubic2, cubic3.
         -> each bar is the mean throughput, error bar is stdev.
    """

    csv_filename = f"{prefix}_iperf_results.csv"
    try:
        with open(csv_filename, 'r', newline='') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            print(f"Reading CSV file: {csv_filename}")
            print(f"CSV Headers: {headers}")
            rows = list(reader)
    except FileNotFoundError:
        print(f"File not found: {csv_filename}")
        sys.exit(1)

    # Convert numeric columns
    # We'll store them in a list of (idx, ue_type, socket, mbps).
    data = []
    for r in rows:
        idx = int(r["idx"])
        file_ = r["file"]
        socket_ = r["socket"]
        mbps = float(r["mbps"])

        ue_type = file_to_ue_type(file_)
        data.append((idx, ue_type, socket_, mbps))

    # -----------------------------------------------------------
    #  Plot #1: "Per-UE" level
    #  We want: prague, cubic (combined), cubic1, cubic2, cubic3
    #  For each run (idx):
    #    - prague throughput = sum of "ALL_FLOWS" from ue_type=prague
    #    - cubic1 = sum of "ALL_FLOWS" from ue_type=cubic1
    #    - cubic2 = sum of "ALL_FLOWS" from ue_type=cubic2
    #    - cubic3 = sum of "ALL_FLOWS" from ue_type=cubic3
    #    - cubic (combined) = cubic1 + cubic2 + cubic3
    # then we average across idx for each category, and compute stdev.
    # We'll store them in a dict:  ue_dict[ue_type][idx] = throughput
    # For prague, cubic1,2,3 we only store the sum of rows where socket="ALL_FLOWS" 
    # (assuming each file-level UE is the "ALL_FLOWS" row).
    # Then "cubic combined" we sum the 3 for that idx.
    # -----------------------------------------------------------

    # We'll gather the "ALL_FLOWS" throughput in a structure:
    ue_allflows = {
        "prague": {},
        "cubic1": {},
        "cubic2": {},
        "cubic3": {}
    }

    # Fill ue_allflows
    for (idx, ue_type, sock, mbps) in data:
        if sock != "ALL_FLOWS":
            continue  # only consider the file-level sum
        if ue_type in ue_allflows:
            # store ue_allflows[ue_type][idx] = sum 
            # (if multiple lines are there, we accumulate, but typically there's exactly one line "ALL_FLOWS")
            ue_allflows[ue_type].setdefault(idx, 0.0)
            ue_allflows[ue_type][idx] += mbps

    # Now build arrays for each of the 5 bars: prague, cubic(all), cubic1,2,3
    prague_vals = list(ue_allflows["prague"].values())
    c1_vals = list(ue_allflows["cubic1"].values())
    c2_vals = list(ue_allflows["cubic2"].values())
    c3_vals = list(ue_allflows["cubic3"].values())

    # We also want for each idx, c1 + c2 + c3
    # We'll iterate over all idx we find in c1,2,3, sum them (handle missing as 0).
    all_idxs = set(ue_allflows["cubic1"].keys()) | \
               set(ue_allflows["cubic2"].keys()) | \
               set(ue_allflows["cubic3"].keys())
    cubic_combo = []
    for i in sorted(all_idxs):
        c1 = ue_allflows["cubic1"].get(i, 0.0)
        c2 = ue_allflows["cubic2"].get(i, 0.0)
        c3 = ue_allflows["cubic3"].get(i, 0.0)
        cubic_combo.append(c1 + c2 + c3)

    # We define a helper to get mean & stdev:
    def mean_std(vals):
        if len(vals) == 0:
            return (0.0, 0.0)
        if len(vals) == 1:
            return (vals[0], 0.0)
        return (statistics.mean(vals), statistics.pstdev(vals))

    # gather (mean, std) for each
    prague_mu, prague_sd = mean_std(prague_vals)
    c1_mu, c1_sd = mean_std(c1_vals)
    c2_mu, c2_sd = mean_std(c2_vals)
    c3_mu, c3_sd = mean_std(c3_vals)
    ccombo_mu, ccombo_sd = mean_std(cubic_combo)

    # We'll plot them in order: prague, cubic(all), cubic1, cubic2, cubic3
    bars_order = [
        ("prague", prague_mu, prague_sd),
        ("cubic (combo)", ccombo_mu, ccombo_sd),
        ("cubic1", c1_mu, c1_sd),
        ("cubic2", c2_mu, c2_sd),
        ("cubic3", c3_mu, c3_sd),
    ]

    # Plot #1
    fig1, ax1 = plt.subplots(figsize=(8,4))
    xvals = range(len(bars_order))
    means = [b[1] for b in bars_order]
    stds = [b[2] for b in bars_order]
    labels = [b[0] for b in bars_order]

    ax1.bar(xvals, means, yerr=stds, color="cornflowerblue", capsize=5, alpha=0.8)
    ax1.set_xticks(xvals)
    ax1.set_xticklabels(labels, rotation=0)
    ax1.set_ylabel("Throughput (Mbps)")
    ax1.set_title("Per-UE Mean ± StdDev Throughput (Across All idx)")

    plt.tight_layout()
    outname1 = f"{prefix}_thp_plot_ue_level.pdf"
    plt.savefig(outname1)
    print(f"Saved Plot #1 to {outname1}")
    plt.close(fig1)

    # -----------------------------------------------------------
    # Plot #2: "Per-flow" across all idx, including combined cubic flows by socket.
    #
    # Steps:
    #   A) For each row with socket != ALL_FLOWS, we have a single flow -> (ue_type, socket)
    #      e.g. "prague-s5", "cubic1-s5", etc.
    #      We'll gather throughput across all idx in a dictionary keyed by (ue_type, socket).
    #   B) For "cubic" flows, we also want to compute a "combined" for each socket across
    #      cubic1, cubic2, cubic3. For each idx, sum the values for that socket across
    #      these three ue_types. Then we gather across idx -> produce mean+std -> label e.g. "cubic-s5 (combo)".
    # -----------------------------------------------------------

    # A) gather flows
    flow_dict = {}  # key=(ue_type, socket), val = list of throughput across different idx
    # We'll also store each row's (idx) so we can do the combination step.
    flow_entries = []  # list of (idx, ue_type, socket, mbps)
    for (idx, ue_type, sock, mbps) in data:
        if sock == "ALL_FLOWS":
            continue
        flow_entries.append((idx, ue_type, sock, mbps))
        flow_dict.setdefault((ue_type, sock), []).append(mbps)

    # B) For each socket that appears in any cubicX, we sum across cubic1,2,3 for that idx
    #    then store under (ue_type="cubic-combined", socket=xxx).
    # We'll first figure out which sockets exist under "cubic1","cubic2","cubic3".
    cubic_types = ["cubic1", "cubic2", "cubic3"]
    # For ease, we gather all (idx, socket) => {c1, c2, c3} throughput
    # e.g.  combo_map[(idx, socket)] = dict( c1=..., c2=..., c3=... )
    combo_map = {}
    for (idx_, ut_, s_, mb_) in flow_entries:
        if ut_ in cubic_types:
            combo_map.setdefault((idx_, s_), {"c1":0,"c2":0,"c3":0})
            if ut_=="cubic1":
                combo_map[(idx_, s_)]["c1"] += mb_
            elif ut_=="cubic2":
                combo_map[(idx_, s_)]["c2"] += mb_
            elif ut_=="cubic3":
                combo_map[(idx_, s_)]["c3"] += mb_

    # Now compute sums
    for (idx_, s_), dvals in combo_map.items():
        combined_val = dvals["c1"] + dvals["c2"] + dvals["c3"]
        # store it in flow_dict under key=("cubic-combined", s_)
        flow_dict.setdefault(("cubic-combined", s_), []).append(combined_val)

    # Now we have flow_dict with keys like ("prague","5"), ("cubic1","5"), ..., ("cubic-combined","5"), etc.
    # We'll produce one bar per key, labeled e.g. "prague-s5" or "cubic1-s7" or "cubic-combined-s7" etc.
    # We'll also compute mean & std for each key.
    flow_summaries = []
    for key, vals in flow_dict.items():
        mu, sd = mean_std(vals)
        flow_summaries.append((key[0], key[1], mu, sd))

    # We sort them by "type then socket," but put "cubic-combined" near the other "cubic" ones if we like.
    # Let's define a custom sort so that "prague" < "cubic1" < "cubic2" < "cubic3" < "cubic-combined".
    # Then sort by socket number ascending.
    def flow_sort_key(item):
        # item is (ue_type, socket, mu, sd)
        ue_type_order = {
            "prague": 1,
            "cubic1": 2,
            "cubic2": 3,
            "cubic3": 4,
            "cubic-combined": 5,
        }.get(item[0], 999)  # unknown => big
        # attempt to parse socket as int if possible
        try:
            socket_val = int(item[1])
        except ValueError:
            socket_val = 9999
        return (ue_type_order, socket_val)

    flow_summaries.sort(key=flow_sort_key)

    # We'll make a bar chart with error bars for each flow
    labels2 = []
    means2 = []
    stds2 = []
    for (ue_t, sock, mu, sd) in flow_summaries:
        # Label
        if ue_t == "cubic-combined":
            lbl = f"cubic-combo-s{sock}"
        else:
            lbl = f"{ue_t}-s{sock}"
        labels2.append(lbl)
        means2.append(mu)
        stds2.append(sd)

    fig2, ax2 = plt.subplots(figsize=(10,5))
    xvals2 = range(len(labels2))
    ax2.bar(xvals2, means2, yerr=stds2, color="cornflowerblue", capsize=5, alpha=0.8)
    ax2.set_xticks(xvals2)
    ax2.set_xticklabels(labels2, rotation=45, ha="right")
    ax2.set_ylabel("Throughput (Mbps)")
    ax2.set_title("Per-Flow Mean ± StdDev (Across All idx)")
    plt.tight_layout()

    outname2 = f"{prefix}_thp_plot_flow_level.pdf"
    plt.savefig(outname2)
    print(f"Saved Plot #2 to {outname2}")
    plt.close(fig2)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <prefix>")
        sys.exit(1)

    prefix_arg = sys.argv[1]
    main(prefix_arg)
