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
    fname = os.path.basename(filename).lower()
    if "prague" in fname:
        return "prague"
    if "cubic" in fname:
        if "-cubic-2.json" in fname:
            return "cubic2"
        elif "-cubic-3.json" in fname:
            return "cubic3"
        else:
            return "cubic1"
    return "unknown"

def main(prefix, additional_space, bottom_text):
    """
    Reads the CSV file {prefix}_iperf_results.csv with columns:
       idx, file, socket, bits_per_second

    Produces two plots (saved as PDF):
      1) Per-UE (prague, combined cubic, etc.) across runs
      2) Per-flow, including combined cubic flows by socket

    If 'additional_space' == 'yes', we add left margin space for
    large y-axis labels. If bottom_text is non-empty, we print
    that text centered at the bottom of both plots.
    """

    csv_filename = f"{prefix}_iperf_results.csv"
    try:
        with open(csv_filename, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        print(f"File not found: {csv_filename}")
        sys.exit(1)

    data = []
    for r in rows:
        idx = int(r["idx"])
        file_ = r["file"]
        socket_ = r["socket"]
        mbps = float(r["mbps"])
        ue_type = file_to_ue_type(file_)
        data.append((idx, ue_type, socket_, mbps))

    # ----------------------------------------------------------------
    # Plot #1: Per-UE throughput
    # ----------------------------------------------------------------
    ue_allflows = {
        "prague": {},
        "cubic1": {},
        "cubic2": {},
        "cubic3": {}
    }

    for (i, ue_type, sock, mbps) in data:
        if sock != "ALL_FLOWS":
            continue
        if ue_type in ue_allflows:
            ue_allflows[ue_type].setdefault(i, 0.0)
            ue_allflows[ue_type][i] += mbps

    prague_vals = list(ue_allflows["prague"].values())
    c1_vals = list(ue_allflows["cubic1"].values())
    c2_vals = list(ue_allflows["cubic2"].values())
    c3_vals = list(ue_allflows["cubic3"].values())

    all_idxs = set(ue_allflows["cubic1"].keys()) | \
               set(ue_allflows["cubic2"].keys()) | \
               set(ue_allflows["cubic3"].keys())
    cubic_combo = []
    for i in sorted(all_idxs):
        c1 = ue_allflows["cubic1"].get(i, 0.0)
        c2 = ue_allflows["cubic2"].get(i, 0.0)
        c3 = ue_allflows["cubic3"].get(i, 0.0)
        cubic_combo.append(c1 + c2 + c3)

    def mean_std(vals):
        if len(vals) == 0:
            return (0.0, 0.0)
        if len(vals) == 1:
            return (vals[0], 0.0)
        return (statistics.mean(vals), statistics.pstdev(vals))

    prague_mu, prague_sd = mean_std(prague_vals)
    ccombo_mu, ccombo_sd = mean_std(cubic_combo)

    bars_order = [
        ("Low-latency", prague_mu, prague_sd),
        ("Non-low Latency", ccombo_mu, ccombo_sd),
    ]

    fig1, ax1 = plt.subplots(figsize=(4, 3))  # Smaller figure size
    xvals = range(len(bars_order))
    means = [b[1] for b in bars_order]
    stds = [b[2] for b in bars_order]
    labels = [b[0] for b in bars_order]

    ax1.bar(xvals, means, yerr=stds, color="cornflowerblue", capsize=5, alpha=0.8)
    ax1.set_xticks(xvals)
    ax1.set_xticklabels(labels, rotation=0)
    ax1.set_ylabel("Throughput (Mbps)")

    plt.tight_layout(pad=0.5)

    # If user wants more space on the left (for decimals)
    if additional_space == "yes":
        plt.subplots_adjust(left=0.15)

    # If user provided text, place it at the bottom
    if bottom_text.strip():
        # Expand bottom margin slightly to fit text
        plt.subplots_adjust(bottom=0.14)
        # Add text centered along bottom
        fig1.text(0.5, 0.02, bottom_text, ha='center', va='center')

    outname1 = f"{prefix}_thp_plot_ue_level.pdf"
    plt.savefig(outname1)
    plt.close(fig1)

    print("Prague Mean:", prague_mu, "Std:", prague_sd)
    print("cubic combo Mean:", ccombo_mu, "Std:", ccombo_sd)
    print("saved plot 1 to ", outname1)

    # ----------------------------------------------------------------
    # Plot #2: Per-flow (including "cubic-combined")
    # ----------------------------------------------------------------
    flow_dict = {}
    flow_entries = []
    cubic_types = ["cubic1", "cubic2", "cubic3"]

    for (idx, ue_type, sock, mbps) in data:
        if sock == "ALL_FLOWS":
            continue
        flow_entries.append((idx, ue_type, sock, mbps))
        flow_dict.setdefault((ue_type, sock), []).append(mbps)

    combo_map = {}
    for (idx_, ut_, s_, mb_) in flow_entries:
        if ut_ in cubic_types:
            combo_map.setdefault((idx_, s_), {"c1": 0, "c2": 0, "c3": 0})
            if ut_ == "cubic1":
                combo_map[(idx_, s_)]["c1"] += mb_
            elif ut_ == "cubic2":
                combo_map[(idx_, s_)]["c2"] += mb_
            elif ut_ == "cubic3":
                combo_map[(idx_, s_)]["c3"] += mb_

    for (idx_, s_), dvals in combo_map.items():
        combined_val = dvals["c1"] + dvals["c2"] + dvals["c3"]
        flow_dict.setdefault(("cubic-combined", s_), []).append(combined_val)

    flow_summaries = []
    for (uet, sock), vals in flow_dict.items():
        mu, sd = mean_std(vals)
        flow_summaries.append((uet, sock, mu, sd))

    def flow_sort_key(item):
        ue_type_order = {
            "prague": 1,
            "cubic1": 2,
            "cubic2": 3,
            "cubic3": 4,
            "cubic-combined": 5,
        }.get(item[0], 999)
        try:
            socket_val = int(item[1])
        except ValueError:
            socket_val = 9999
        return (ue_type_order, socket_val)

    flow_summaries.sort(key=flow_sort_key)

    labels2 = []
    means2 = []
    stds2 = []
    for (uet, sock, mu, sd) in flow_summaries:
        if uet == "cubic-combined":
            lbl = f"cubic-combo-s{sock}"
        else:
            lbl = f"{uet}-s{sock}"
        labels2.append(lbl)
        means2.append(mu)
        stds2.append(sd)

    fig2, ax2 = plt.subplots(figsize=(6, 3))
    xvals2 = range(len(labels2))
    ax2.bar(xvals2, means2, yerr=stds2, color="cornflowerblue", capsize=5, alpha=0.8)
    ax2.set_xticks(xvals2)
    ax2.set_xticklabels(labels2, rotation=45, ha="right")
    ax2.set_ylabel("Throughput (Mbps)")
    ax2.set_title("Per-Flow Mean ± StdDev (Across All idx)")

    plt.tight_layout(pad=0.5)
    if bottom_text.strip():
        plt.subplots_adjust(bottom=0.18)
        fig2.text(0.5, 0.02, bottom_text, ha='center', va='center')

    outname2 = f"{prefix}_thp_plot_flow_level.pdf"
    plt.savefig(outname2)
    plt.close(fig2)
    
    print("saved plot 2 to ", outname2)

if __name__ == "__main__":
    """
    Usage:
      ./script.py <prefix> <additional_space> <bottom_text>

    Example:
      ./script.py myprefix no "Extra info at the bottom"
    """
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <prefix> <additional_space> [bottom_text]")
        sys.exit(1)

    prefix_arg = sys.argv[1]
    additional_space_arg = sys.argv[2]

    # If there's a 4th argument, treat it as bottom_text
    # If not, use empty string
    if len(sys.argv) >= 4:
        bottom_text_arg = " ".join(sys.argv[3:])  # In case user has spaces
    else:
        bottom_text_arg = ""

    main(prefix_arg, additional_space_arg, bottom_text_arg)
