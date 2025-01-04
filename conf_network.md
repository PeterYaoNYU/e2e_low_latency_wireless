## Slicing v.s. No Slicing. 

We start we no slicing. To go into slicing mode, assuming the flexric is already running as specified before. 

```bash
cd /mydata/flexric  
./build/examples/xApp/c/slice/xapp_rc_slice_ctrl_fair
```

To go back to no slicing, kill the gnb and start afresh. You may need to refer back to [previous tutorial](./setup_network.md).

## Shared Queue v.s.Separate Queue

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

