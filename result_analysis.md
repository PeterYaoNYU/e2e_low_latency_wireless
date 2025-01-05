This is document is about analyzing the data after running the experiments.

## Latency
To analyze the latency, we first transform the data into a summary of CSV files, containing the per-flow latency informaiton, then we generate plots. You can change the code to customize the things to document. 

An example would be:
```bash
python3 .\ss_csv.py {begin_idx} {end_idx} {csv_prefix}
python3 .\rtt_plot.py {csv_prefix}
```

Where {csv_prefix} is a string of your choice. 

## Throughput

It follows the same process as the latency data. First a CSV summary, then we plot based on the CSV. 

```bash
python3 .\iperf_csv.py {begin_idx} {end_idx} {csv_prefix}
python3 .\thp_plot.py {csv_prefix}
```

## RLC Queue
For experiements where there is *no slicing*, run the following script to analyze the RLC buffer occupancy. UE 1 is the L4S Low Latency UE, and UE2~3 are cubic UEs. 

```bash
python3 ./rlc_no_slice.py {experiment idx}
```

For the slicing experiments:
```bash
python3 ./rlc_sliced.py {experiment idx}
```

The unit is ***Bytes***. 

### Upstream Queue Occupancy. 

For separate queue experiments, we have scripts to gain insight into Low Latency Queue delay. 

```bash
python3 ./dualq_plot.py {experiment_idx}
```

For FIFO queue, use this:

```bash
python3 ./fifo_plot.py {experiment_idx}
```