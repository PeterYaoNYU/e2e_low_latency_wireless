## Slicing v.s. No Slicing. 

We start we no slicing. To go into slicing mode, assuming the flexric is already running as specified before. 

```bash
cd /mydata/flexric  
./build/examples/xApp/c/slice/xapp_rc_slice_ctrl_fair
```

To go back to no slicing, kill the gnb and start afresh. You may need to refer back to [previous tutorial](./setup_network.md).


## Queue Discipline

We have a separate [jupyter notebook](./qdisc_cca.ipynb) that walks you through the process, again, the first code block, the SSH connection, need to be modified by you. 

Follow the prompts in the notebook to execute specific code blocks dependeing on the experiment. 

## Shared Queue v.s. Separate Queue

We start with separate queue, whether you use static routing or SRv6 for routing. 

### Static Routing Case
At prague sender node, 
cross traffic change to have prague sender use dualq (***Separate Queue Case***)
```bash
sudo ip route del 12.1.1.128/25 via 10.0.5.2
sudo ip route del 10.0.8.0/24 via 10.0.5.2

sudo ip route add 12.1.1.128/25 via 10.0.3.1
sudo ip route add 10.0.8.0/24 via 10.0.3.1
```


cross traffic change to prague sender to use deep fifo (***Shared FIFO Case***)
```bash
sudo ip route del 12.1.1.128/25 via 10.0.3.1 
sudo ip route del 10.0.8.0/24 via 10.0.3.1 

sudo ip route add 12.1.1.128/25 via 10.0.5.2 
sudo ip route add 10.0.8.0/24 via 10.0.5.2 
```

### SRv6 Case.
<!-- 96040 and 5129. on decap we need the ECN marking to be copied from outer to inner packet headers, as specified ibn  -->
For the experimentation, we use static routing for the setup. Here we provide a guideline to use SRv6 in the experiments. Packets are encapsulated upon ingress in SRv6 h



Also on prague sender node, to use separate queue case:
```bash
sudo ip route del 12.1.1.128/25 encap seg6 mode encap segs 2001:db8:5::2 dev eno2
sudo ip route del 10.0.8.0/24 encap seg6 mode encap segs 2001:db8:5::2 dev eno2

sudo ip route add 12.1.1.128/25 encap seg6 mode encap segs 2001:db8:6::2 dev enp5s0f0
sudo ip route add 10.0.8.0/24 encap seg6 mode encap segs 2001:db8:6::2 dev enp5s0f0
```

to use shared queue case:
```bash
sudo ip route del 12.1.1.128/25 encap seg6 mode encap segs 2001:db8:6::2 dev enp5s0f0
sudo ip route del 10.0.8.0/24 encap seg6 mode encap segs 2001:db8:6::2 dev enp5s0f0

sudo ip route add 12.1.1.128/25 encap seg6 mode encap segs 2001:db8:5::2 dev eno2
sudo ip route add 10.0.8.0/24 encap seg6 mode encap segs 2001:db8:5::2 dev eno2
```

I would like to take the chance to remind again that, as mentioned [previously](./get_resources.md), these need to be executed on either FIFO or dualq nodes, when you are using SRv6 for routing. 

```bash
sudo sysctl -w net.ipv6.conf.all.forwarding=1
sudo sysctl -w net.ipv6.conf.all.seg6_enabled=1
sudo sysctl -w net.ipv6.conf.{prage_dualq_interface}.seg6_enabled=1
sudo sysctl -w net.ipv6.conf.{prague_FIFO_interface}.seg6_enabled=1
sudo sysctl -w net.ipv6.conf.{classis_FIFO_interface}.seg6_enabled=1
sudo sysctl -w net.ipv6.conf.{FIFO_5G_interface}.seg6_enabled=1
sudo sysctl -w net.ipv6.conf.{dualq_5G_interface}.seg6_enabled=1
```

## Configure the Congestion Control
After you intiate the UE each time, you need to make sure that the UEs are using the correct congestion control algorithms intended. You also need to make sure that the sender and cross traffic receiver is using the correct congestion control. 

To simplify the process, we have a ***CCA*** section in the [jupyter notebook](./qdisc_cca.ipynb), where you just need to execute the code blocks to set up the CCA in the UEs, the senders, and the cross traffic receivers. 