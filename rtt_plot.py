#!/usr/bin/env python3
import sys
import csv
import statistics
import re
import os
import matplotlib.pyplot as plt

def get_ue_type(filename):
    """
    Based on the filename, return one of:
      'prague', 'cubic1', 'cubic2', 'cubic3', or 'all_cubic'.
    - If file == 'ALL_CUBIC', we treat it as 'all_cubic'.
    - If ends with '-ss-prague.txt', treat as 'prague'.
    - If ends with '-ss-cubic.txt', treat as 'cubic1'.
    - If ends with '-ss-cubic-2.txt', treat as 'cubic2'.
    - If ends with '-ss-cubic-3.txt', treat as 'cubic3'.
    Otherwise, return 'unknown'.
    """
    if filename == "ALL_CUBIC":
        return "all_cubic"

    fname = os.path.basename(filename).lower()
    if fname.endswith("-ss-prague.txt"):
        return "prague"
    if fname.endswith("-ss-cubic.txt"):
        return "cubic1"
    if fname.endswith("-ss-cubic-2.txt"):
        return "cubic2"
    if fname.endswith("-ss-cubic-3.txt"):
        return "cubic3"
    return "unknown"

def main(prefix):
    """
    1) Reads {prefix}_srtt_results.csv, which has columns:
         idx, file, flow, mean_srtt
    2) Produces two plots in PDF:
       a) {prefix}_srtt_ue_plot.pdf -> UE-level mean±std for:
          [prague, ALL_CUBIC, cubic1, cubic2, cubic3]
          using only rows flow="ALL_FLOWS", aggregated across all idx.
       b) {prefix}_srtt_flow_plot.pdf -> Per-flow mean±std (fd=5,7,9,11,...) 
          skipping aggregator flows (ALL_FLOWS) and file="ALL_CUBIC".
    """

    csv_filename = f"{prefix}_srtt_results.csv"
    try:
        with open(csv_filename, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        print(f"File not found: {csv_filename}")
        sys.exit(1)

    # Convert mean_srtt to float
    # We'll store each row in a list of (idx, ue_type, flow, srtt)
    data = []
    for r in rows:
        idx_val = r["idx"]
        file_val = r["file"]
        flow_val = r["flow"]
        srtt_str = r["mean_srtt"]
        try:
            srtt_val = float(srtt_str)
        except ValueError:
            srtt_val = 0.0
        ue_type = get_ue_type(file_val)
        data.append((idx_val, file_val, ue_type, flow_val, srtt_val))

    # ---------------------------------------------------------------------
    # Plot #1: UE-level => use only rows where flow="ALL_FLOWS".
    # We gather data for 5 categories: prague, all_cubic, cubic1,2,3.
    # We compute mean & stdev across *all idx* in the CSV for each category.
    # ---------------------------------------------------------------------
    # We'll gather srtts in a dict:  ue_agg[ue_type] -> list_of_srtts
    ue_agg = {
        "prague": [],
        "all_cubic": [],
        "cubic1": [],
        "cubic2": [],
        "cubic3": [],
    }

    for (idxv, filev, uet, flowv, srttv) in data:
        if flowv == "ALL_FLOWS":
            # aggregator line
            # if this ue_type is one of the keys, store the srtt
            if uet in ue_agg:
                ue_agg[uet].append(srttv)

    # Now compute mean & std for each in the order: prague, all_cubic, cubic1,2,3
    def mean_std(vals):
        if not vals:
            return (0.0, 0.0, 0)
        if len(vals) == 1:
            return (vals[0], 0.0, 1)
        return (statistics.mean(vals), statistics.pstdev(vals), len(vals))

    bars_order = ["prague", "all_cubic", "cubic1", "cubic2", "cubic3"]
    results1 = []
    for cat in bars_order:
        mu, sd, n = mean_std(ue_agg[cat])
        # store (category_label, mean, std)
        # rename 'all_cubic' to 'Cubic All' as a label
        label_map = {
            "prague": "Prague",
            "all_cubic": "Cubic All",
            "cubic1": "Cubic1",
            "cubic2": "Cubic2",
            "cubic3": "Cubic3",
        }
        results1.append((label_map[cat], mu, sd))

    # Make the bar plot
    fig1, ax1 = plt.subplots(figsize=(8,4))
    xvals = range(len(results1))
    labels1 = [r[0] for r in results1]
    means1 = [r[1] for r in results1]
    stds1 = [r[2] for r in results1]

    ax1.bar(
        xvals, means1, yerr=stds1,
        color="mediumseagreen",
        ecolor="black", capsize=5, alpha=0.8
    )
    ax1.set_xticks(xvals)
    ax1.set_xticklabels(labels1, rotation=0)
    ax1.set_ylabel("Mean SRTT (ms)")
    ax1.set_title("UE-Level Mean ± StdDev SRTT (Across All Indices)")

    plt.tight_layout()
    outname1 = f"{prefix}_srtt_ue_plot.pdf"
    plt.savefig(outname1)
    print(f"Saved Plot #1 to {outname1}")
    plt.close(fig1)

    # ---------------------------------------------------------------------
    # Plot #2: Per-flow => skip aggregator rows (flow="ALL_FLOWS") and skip file="ALL_CUBIC"
    # We gather for each (ue_type, flow), across all idx, a list of srtt. Then compute mean & std.
    # Then produce a bar for each combination, e.g. prague-s5, prague-s7, cubic1-s5, ...
    # ---------------------------------------------------------------------
    flow_map = {}  # key=(ue_type, flow_num), val=list_of_srtt
    for (idxv, filev, uet, flowv, srttv) in data:
        if flowv == "ALL_FLOWS":
            continue
        if filev == "ALL_CUBIC":
            continue
        # This is a real flow
        # We'll define a key=(ue_type, flowv)
        flow_map.setdefault((uet, flowv), []).append(srttv)

    # Now we compute mean & std for each key
    flow_summaries = []
    for key, srtt_list in flow_map.items():
        ue_t, flow_id = key
        mu, sd, n = mean_std(srtt_list)
        flow_summaries.append((ue_t, flow_id, mu, sd))

    # We'll define an ordering for the ue_type so it appears prague, then cubic1,2,3
    def ue_type_order(uet):
        # if unknown, place it last
        order_map = {
            "prague": 1,
            "cubic1": 2,
            "cubic2": 3,
            "cubic3": 4,
        }
        return order_map.get(uet, 99)

    def flow_id_order(fid):
        # try to parse as int
        try:
            return int(fid)
        except ValueError:
            return 9999

    flow_summaries.sort(key=lambda x: (ue_type_order(x[0]), flow_id_order(x[1])))

    # Build data for bar chart
    labels2 = []
    means2 = []
    stds2 = []
    for (uet, fid, mu, sd) in flow_summaries:
        # We'll label e.g. "prague-s5" or "cubic1-s7"
        lbl = f"{uet}-{fid}"
        labels2.append(lbl)
        means2.append(mu)
        stds2.append(sd)

    fig2, ax2 = plt.subplots(figsize=(10,4))
    xvals2 = range(len(labels2))
    ax2.bar(
        xvals2, means2, yerr=stds2,
        color="mediumseagreen",
        ecolor="black", capsize=5, alpha=0.8
    )
    ax2.set_xticks(xvals2)
    ax2.set_xticklabels(labels2, rotation=45, ha="right")
    ax2.set_ylabel("Mean SRTT (ms)")
    ax2.set_title("Per-Flow Mean ± StdDev SRTT (Across All Indices)")

    plt.tight_layout()
    outname2 = f"{prefix}_srtt_flow_plot.pdf"
    plt.savefig(outname2)
    print(f"Saved Plot #2 to {outname2}")
    plt.close(fig2)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <prefix>")
        sys.exit(1)

    prefix_arg = sys.argv[1]
    main(prefix_arg)
