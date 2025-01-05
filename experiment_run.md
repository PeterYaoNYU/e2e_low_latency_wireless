This document describes how to run an or multiple experiment. 

The first steps would be to configure the network to use the configureation intended (QDisc, Separate/Shared Queue, Slicing/No Slicing), which is described in this [previous document](./conf_network.md). 

Here we ***prepare to run the experiment*** and ***actually run the experiment(s)***.

## Preparation: Decide which experiment to run


You need to decide which paramters you want to use for the experiment. This is done by tuning the parameters in the files *exp_cubic.sh* and *exp_prague.sh".  

### To decide the number of cross traffic to have 
Change line 12 in both files. The number decide the number of cross traffic flows. 
We fix the number of RAN flows in our experiments, but you can tune that on line 13 of both scripts. 

### To have no cross traffic at all. 
Comment out line 52 in exp_prague.sh. Comment out line 82 in exp_cubi.sh. 

Comment out Line 131, 133, 138 and 143 in *experiment.py*. 

Do the uncomment if you want to have cross traffic. By default, there are cross traffic. 

## Actually Run the Experiment
Change the last line in *experiment.py*. The first argument is for the number of runs to have, and the second argument is for the beginning idx of the experiments. 

After changing that, simply call from the command line. 
```bash
python3 experiment.py
```

All generated results, including the latency, throughput, RLC buffer occupancy, and upstream queue occupancy, are downloaded to your local machine after the experiment is done. This gives you visibility into every part in the end-to-end pipeline. 

In the next section, we will give tools to analyze each of these parts. 

