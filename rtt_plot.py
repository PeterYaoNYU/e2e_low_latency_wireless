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


def main(prefix, bottom_text, include_legend=True):
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
    # We'll store each row in a list of (idx, file, ue_type, flow, srtt)
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
            if uet in ue_agg:
                ue_agg[uet].append(srttv)

    def mean_std(vals):
        if not vals:
            return (0.0, 0.0, 0)
        if len(vals) == 1:
            return (vals[0], 0.0, 1)
        return (statistics.mean(vals), statistics.pstdev(vals), len(vals))

    bars_order = ["prague", "all_cubic"]
    results1 = []
    label_map = {
        "prague": "Low Latency",
        "all_cubic": "Non-low Latency",
    }
    for cat in bars_order:
        mu, sd, n = mean_std(ue_agg[cat])
        # store (category_label, mean, std)
        results1.append((label_map[cat], mu, sd))

    # Parse multi-run.csv for relevant story id
    story_id = None
    m = re.search(r'story(\d+)', prefix.lower())
    if m:
        story_id = m.group(1)
    print("Story ID:", story_id, type(story_id))

    base_delay = rlc_delay = upstream_latency = None
    if story_id is not None:
        try:
            with open('multi-run.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["Story ID"].strip() == story_id:
                        base_delay = float(row["RAN Base delay"].strip())
                        # Sometimes the header might be "Delay RLC " (with trailing space)
                        rlc_header = "Delay RLC " if "Delay RLC " in row else "Delay RLC"
                        rlc_delay = float(row[rlc_header].strip())
                        upstream_latency = float(row["Latency @ upstream Q"].strip())
                        break
        except Exception as e:
            print("Error reading multi-run.csv:", e)

    # Make the bar plot #1
    fig1, ax1 = plt.subplots(figsize=(4, 3))  # Smaller figure
    xvals = range(len(results1))
    labels1 = [r[0] for r in results1]
    means1 = [r[1] for r in results1]
    stds1 = [r[2] for r in results1]

    # Define shades of green for the stacked segments
    base_color = plt.cm.Greens(0.6)      # Darker green for RAN Base delay
    rlc_color = plt.cm.Greens(0.4)       # Medium green for Delay RLC
    upstream_color = plt.cm.Greens(0.2)  # Lighter green for Latency @ upstream Q

    # Plot the "Low Latency" bar (x=0)
    if base_delay is not None and rlc_delay is not None and upstream_latency is not None:
        # Stacked bar segments for "Low Latency"
        ax1.bar(xvals[0], base_delay, color=base_color, alpha=0.8, label="RAN Base Delay")
        ax1.bar(xvals[0], rlc_delay, bottom=base_delay, color=rlc_color, alpha=0.8, label="RLC Buffer Delay")
        ax1.bar(xvals[0], upstream_latency, bottom=(base_delay + rlc_delay),
                color=upstream_color, alpha=0.8, label="Upstream Queue Delay")
        # Add error bar across the entire stacked bar
        ax1.errorbar(xvals[0], means1[0], yerr=stds1[0], color='black', capsize=5)
        # Add legend if requested
        if include_legend:
            ax1.legend(
                # bbox_to_anchor=(0.25, 1.05, 0.35, 0.2),  # narrower width (0.35) vs. the old 0.50
                fontsize=8,          # smaller font
                labelspacing=0.2,    # reduce vertical space between labels
                handlelength=1.0,    # shorter handle
                handletextpad=0.4,   # reduce spacing between handle and text
                columnspacing=0.8,   # reduce spacing between columns (if ncol>1)
                ncol=1               # single column of legend items
            )
    else:
        # Fallback: single bar if multi-run data not available
        ax1.bar(xvals[0], means1[0], yerr=stds1[0], color="mediumseagreen",
                capsize=5, alpha=0.8)

    # Plot the "Non-low Latency" bar (x=1)
    ax1.bar(xvals[1], means1[1], yerr=stds1[1], color="mediumseagreen",
            capsize=5, alpha=0.8)

    ax1.set_xticks(xvals)
    ax1.set_xticklabels(labels1, rotation=0)
    ax1.set_ylabel("Mean SRTT (ms)")
    plt.tight_layout(pad=0.5)  # Reduce extra padding
    outname1 = f"{prefix}_srtt_ue_plot.pdf"
    
    if bottom_text.strip():
        plt.subplots_adjust(bottom=0.14)
        fig1.text(0.5, 0.02, bottom_text, ha='center', va='center')
        
    plt.savefig(outname1)
    print(f"Saved Plot #1 to {outname1}")
    plt.close(fig1)
    
    print("prague rtt:", results1[0][1])
    print("cubic average rtt:", results1[1][1])

    # ---------------------------------------------------------------------
    # Plot #2: Per-flow => skip aggregator rows (flow="ALL_FLOWS") and skip file="ALL_CUBIC".
    # Then bar chart for each (ue_type, flow_id).
    # ---------------------------------------------------------------------
    flow_map = {}  # key=(ue_type, flow_num), val=list_of_srtt
    for (idxv, filev, uet, flowv, srttv) in data:
        if flowv == "ALL_FLOWS":
            continue
        if filev == "ALL_CUBIC":
            continue
        flow_map.setdefault((uet, flowv), []).append(srttv)

    flow_summaries = []
    for key, srtt_list in flow_map.items():
        ue_t, flow_id = key
        mu, sd, n = mean_std(srtt_list)
        flow_summaries.append((ue_t, flow_id, mu, sd))

    def ue_type_order(uet):
        order_map = {
            "prague": 1,
            "cubic1": 2,
            "cubic2": 3,
            "cubic3": 4,
        }
        return order_map.get(uet, 99)

    def flow_id_order(fid):
        try:
            return int(fid)
        except ValueError:
            return 9999

    # Sort so prague flows come first, then cubic1,2,3
    flow_summaries.sort(key=lambda x: (ue_type_order(x[0]), flow_id_order(x[1])))

    labels2 = []
    means2 = []
    stds2 = []
    for (uet, fid, mu, sd) in flow_summaries:
        lbl = f"{uet}-{fid}"
        labels2.append(lbl)
        means2.append(mu)
        stds2.append(sd)

    fig2, ax2 = plt.subplots(figsize=(6, 3))  # Smaller figure
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
    plt.tight_layout(pad=0.5)
    outname2 = f"{prefix}_srtt_flow_plot.pdf"
    plt.savefig(outname2)
    print(f"Saved Plot #2 to {outname2}")
    plt.close(fig2)


if __name__ == "__main__":
    # We expect 1 or 2 extra args: prefix, and optionally "--no-legend"
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print(f"Usage: {sys.argv[0]} <prefix> [--no-legend]")
        sys.exit(1)

    prefix_arg = sys.argv[1]
    include_legend_arg = True
    
    bottom_text = sys.argv[2] if len(sys.argv) >= 3 else ""

    if len(sys.argv) == 4 and sys.argv[3] == "--no-legend":
        include_legend_arg = False

    main(prefix_arg, bottom_text,  include_legend=include_legend_arg)
