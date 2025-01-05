#!/usr/bin/env python3
import sys
import re
import matplotlib.pyplot as plt
import numpy as np

def parse_dualq_monitor_delay_only(filename):
    """
    Parse dualq_monitor_{idx}.txt to extract:
      - times (seconds)
      - delay_c (microseconds, Classic)
      - delay_l (microseconds, L4S)

    Ignores dropped packets, backlog, and packet counts, focusing only on delay.

    Returns:
        times (list[float]): Timestamps (sorted by time).
        delay_c (list[float]): Classic queue delay in microseconds.
        delay_l (list[float]): L4S queue delay in microseconds.
    """
    times = []
    delay_c_vals = []
    delay_l_vals = []

    # Regex to match lines with time + 'delay_c Xus delay_l Yus'
    # Example line:
    # 1735917316.212567164 qdisc ... delay_c 123us delay_l 45us ...
    pattern_time = re.compile(r'^(\d+\.\d+)')
    pattern_delay = re.compile(r'delay_c\s+(\d+)us\s+delay_l\s+(\d+)us')

    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # 1) Check if the first token is a float => time
                time_match = pattern_time.match(line)
                if not time_match:
                    continue
                t_str = time_match.group(1)
                try:
                    t_val = float(t_str)
                except ValueError:
                    continue

                # 2) Extract the delays
                m_delay = pattern_delay.search(line)
                if not m_delay:
                    continue
                d_c = float(m_delay.group(1))  # microseconds
                d_l = float(m_delay.group(2))  # microseconds

                times.append(t_val)
                delay_c_vals.append(d_c)
                delay_l_vals.append(d_l)

    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        sys.exit(1)

    # Sort by time
    combined = sorted(zip(times, delay_c_vals, delay_l_vals), key=lambda x: x[0])
    if not combined:
        return [], [], []

    times_sorted, c_sorted, l_sorted = zip(*combined)
    return list(times_sorted), list(c_sorted), list(l_sorted)


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <experiment_idx>")
        sys.exit(1)

    try:
        exp_idx = int(sys.argv[1])
    except ValueError:
        print("Error: experiment_idx must be an integer.")
        sys.exit(1)

    filename = f"dualq_monitor_{exp_idx}.txt"
    print(f"=== Parsing DualQ Monitor File for Delay Only: {filename} ===")

    times, delay_c_us, delay_l_us = parse_dualq_monitor_delay_only(filename)
    if not times:
        print("No valid delay data found. Exiting.")
        sys.exit(0)

    # Normalize time (start at zero)
    t0 = times[0]
    rel_times = [t - t0 for t in times]

    # Convert microseconds to milliseconds
    delay_c_ms = [x / 1000.0 for x in delay_c_us]
    delay_l_ms = [x / 1000.0 for x in delay_l_us]

    # Build a single figure with 2 subplots
    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # 1) Classic Queue Delay
    ax_top.plot(rel_times, delay_c_ms, color='blue', linewidth=1)
    ax_top.set_ylabel("Classic Delay (ms)")
    ax_top.set_title(f"Classic Queue Delay Over Time (Experiment {exp_idx})")
    ax_top.grid(True, linestyle="--", alpha=0.5)

    # 2) L4S Queue Delay
    ax_bot.plot(rel_times, delay_l_ms, color='green', linewidth=1)
    ax_bot.set_ylabel("L4S Delay (ms)")
    ax_bot.set_xlabel("Time (s)")
    ax_bot.set_title(f"L4S Queue Delay Over Time (Experiment {exp_idx})")
    ax_bot.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    out_png = f"dualq_monitor_{exp_idx}_delays_only.png"
    plt.savefig(out_png)
    print(f"Plot saved to: {out_png}")
    plt.show()

    # Summary stats
    c_delay_mean = np.mean(delay_c_ms)
    c_delay_std = np.std(delay_c_ms)
    l_delay_mean = np.mean(delay_l_ms)
    l_delay_std = np.std(delay_l_ms)

    print("\n=== DualQ Delay-Only Summary ===")
    print(f"Classic Delay (ms): mean={c_delay_mean:.3f}, std={c_delay_std:.3f}")
    print(f"L4S    Delay (ms): mean={l_delay_mean:.3f}, std={l_delay_std:.3f}")


if __name__ == "__main__":
    main()
