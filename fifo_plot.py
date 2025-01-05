#!/usr/bin/env python3
import sys
import re
import matplotlib.pyplot as plt
import numpy as np

def parse_fifo_file(filename):
    """
    Parse a single TBF qdisc monitor file line by line.

    Expected format (example line):
    ---------------------------------------------------------------------------
    1735868880.594344798 qdisc tbf 8004: root refcnt 2 rate 50Mbit ...
      ... Sent 1268961 bytes 916 pkt (dropped 0, overlimits 347 requeues 0)
      backlog 0b 0p requeues 0
    ---------------------------------------------------------------------------
    
    We extract:
    - timestamp (float) from the first token
    - dropped (cumulative integer) from "(dropped N, ...)"
    - backlog_bytes (integer) from "backlog Xb ..."
    - backlog_packets (integer) from "backlog ... Yp"
    """
    times = []
    dropped_vals = []
    backlog_pkts = []
    backlog_bytes_vals = []

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if len(parts) < 1:
                continue
            
            # 1) Parse timestamp from the first field
            try:
                ts = float(parts[0])
            except ValueError:
                # If the first token is not a float, skip
                continue
            
            # 2) Extract 'dropped' using regex (dropped N, ...)
            dropped_match = re.search(r'\(dropped\s+(\d+),', line)
            if not dropped_match:
                continue
            dropped_cum = int(dropped_match.group(1))
            
            # 3) Extract backlog in bytes & packets: "backlog Xb Yp"
            backlog_match = re.search(r'backlog\s+(\d+)b\s+(\d+)p', line)
            if not backlog_match:
                continue
            backlog_bytes = int(backlog_match.group(1))
            backlog_pkts_val = int(backlog_match.group(2))
            
            # Store extracted values
            times.append(ts)
            dropped_vals.append(dropped_cum)
            backlog_pkts.append(backlog_pkts_val)
            backlog_bytes_vals.append(backlog_bytes)
    
    return times, dropped_vals, backlog_pkts, backlog_bytes_vals


def plot_fifo_monitor(exp_idx, link_speed_mbps=50.0):
    """
    1) Parse 'fifo_monitor_{exp_idx}.txt'.
    2) Compute instantaneous drops from the cumulative 'dropped' values,
       using the first line's 'dropped' as the base reference (thus first line => 0 drop).
    3) Plot a single figure with three subplots:
       a) Backlog (packets) over time
       b) Instantaneous drops over time
       c) Inferred queue delay (seconds) over time

    4) Print summary stats (mean & std dev) for backlog, drops, and delay.

    Args:
        exp_idx (int): The experiment index, so we parse 'fifo_monitor_{exp_idx}.txt'.
        link_speed_mbps (float): Link speed in Mbps, used for inferring queue delay.
    """
    filename = f"fifo_monitor_{exp_idx}.txt"
    print(f"=== Parsing FIFO monitor file: {filename} ===")

    # Attempt to parse the file
    try:
        times, dropped_cum, backlog_p, backlog_b = parse_fifo_file(filename)
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        sys.exit(1)

    if not times:
        print(f"No valid data lines found in {filename}. Exiting.")
        sys.exit(0)

    # 1) Sort by time
    combined = sorted(zip(times, dropped_cum, backlog_p, backlog_b), key=lambda x: x[0])
    times_sorted, dropped_sorted, backlog_p_sorted, backlog_b_sorted = zip(*combined)

    # 2) Normalize time (start at zero)
    t0 = times_sorted[0]
    rel_times = [t - t0 for t in times_sorted]

    # 3) Compute instantaneous drops
    #    The first line's 'dropped' is used as a baseline => inst_drops[0] = 0
    inst_drops = []
    for i in range(len(dropped_sorted)):
        if i == 0:
            inst_drops.append(0)  # baseline
        else:
            diff = dropped_sorted[i] - dropped_sorted[i-1]
            inst_drops.append(diff if diff > 0 else 0)

    # 4) Inferred queue delay (s):
    #    delay = (backlog_bytes * 8 bits) / link_speed_bps
    link_speed_bps = link_speed_mbps * 1e6
    queue_delays = [(b_bytes * 8.0) / link_speed_bps for b_bytes in backlog_b_sorted]

    # 5) Color points: red if drop > 0, else blue
    colors = ['red' if dd > 0 else 'blue' for dd in inst_drops]

    # Create a single figure with three subplots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    # Subplot 1: backlog (packets)
    ax1.scatter(rel_times, backlog_p_sorted, c=colors, s=20, alpha=0.5)
    ax1.set_ylabel("Backlog (pkts)")
    ax1.set_title(f"FIFO Queue Backlog Over Time (Exp {exp_idx})")
    ax1.grid(True, linestyle="--", alpha=0.5)

    # Subplot 2: inst. drops
    ax2.plot(rel_times, inst_drops, color='black', linewidth=1, alpha=0.7)
    ax2.set_ylabel("Packet Drops (inst.)")
    ax2.set_title(f"Instantaneous Drops Over Time (Exp {exp_idx})")
    ax2.grid(True, linestyle="--", alpha=0.5)

    # Subplot 3: queue delay
    ax3.plot(rel_times, queue_delays, color='green', linewidth=1, alpha=0.7)
    ax3.set_ylabel("Queue Delay (s)")
    ax3.set_xlabel("Time (s)")
    ax3.set_title(f"Inferred Queue Delay Over Time (Exp {exp_idx})")
    ax3.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    out_png = f"fifo_monitor_{exp_idx}_singleplot.png"
    plt.savefig(out_png)
    print(f"Plot saved to: {out_png}")
    plt.show()

    # 6) Summary metrics
    backlog_mean = np.mean(backlog_p_sorted)
    backlog_std  = np.std(backlog_p_sorted)
    drops_mean   = np.mean(inst_drops)
    drops_std    = np.std(inst_drops)
    delay_mean   = np.mean(queue_delays)
    delay_std    = np.std(queue_delays)

    print("\n=== FIFO TBF Summary Metrics ===")
    print(f"Backlog (pkts): mean={backlog_mean:.2f}, std={backlog_std:.2f}")
    print(f"Drops (inst.): mean={drops_mean:.2f}, std={drops_std:.2f}")
    print(f"Delay (s): mean={delay_mean:.4f}, std={delay_std:.4f}")


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <experiment_idx>")
        sys.exit(1)

    try:
        exp_idx = int(sys.argv[1])
    except ValueError:
        print("experiment_idx must be an integer.")
        sys.exit(1)

    plot_fifo_monitor(exp_idx, link_speed_mbps=50.0)


if __name__ == "__main__":
    main()
