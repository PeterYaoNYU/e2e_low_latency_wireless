## POWDER Profile
We run the experiment on the Powder testbed. The topology profile is available at [this profile page](https://www.powderwireless.net/p/nyunetworks/e2e_separate_queues). More specifically, to reproduce this paper, you need to initiate the ***cross-traffic branch***. This involves 1 d434 compute node, 4 d710 compute node, and 2 Xen VM. You may want to reserve these resources ahead of time. 

You can also fork the profile at this [Github Reporsitory](https://github.com/PeterYaoNYU/cloudlab_e2e_topology/tree/cross-traffic). 

## Network Routing with Static Routing. 
When you initiate the profile on POWDER testbed, it does not have the network routing configured. It needs to be set up manually. The IPv4 addresses, however, are coded in the profile. 

Static routing is easier to configure than SRv6. It does not require prior knowledge on SRv6. Not using SRv6 will not change the results. SRv6 is just a way to do routing. 

On classic sender:
```
sudo ip route add 12.1.1.64/26 via 10.0.2.1
```

On fifo queue:
```
sudo ip route add 12.1.1.64/26 via 10.0.0.1
sudo ip route add 12.1.1.128/25 via 10.0.0.1
```
On 
L4S sender:
```
sudo ip route add 12.1.1.128/25 via 10.0.3.1
```

On Dual Queue node:
```
sudo ip route add 12.1.1.128/25 via 10.0.1.1
```


## Network Routing with SRv6. 

For a proof of concept, we use SRv6 to do routing as well. We assign these IPv6 addresses to the interfaces and ensure basic connectivity. 

| Link Name         | IPv6 Subnet     | Node            | IPv6 Address      |
|--------------------|-----------------|-----------------|-------------------|
| net_5g_fifo       | 2001:db8:5::/64 | 5g              | 2001:db8:5::1/64  |
|                   |                 | fifo_deep       | 2001:db8:5::2/64  |
| net_5g_dualq      | 2001:db8:6::/64 | 5g              | 2001:db8:6::1/64  |
|                   |                 | dualq           | 2001:db8:6::2/64  |
| net_fifo_classic  | 2001:db8:7::/64 | fifo_deep       | 2001:db8:7::1/64  |
|                   |                 | classic_sender  | 2001:db8:7::2/64  |
| net_dualq_prague  | 2001:db8:8::/64 | dualq           | 2001:db8:8::1/64  |
|                   |                 | prague_sender   | 2001:db8:8::2/64  |
| net_classic_dualq | 2001:db8:9::/64 | classic_sender  | 2001:db8:9::1/64  |
|                   |                 | dualq           | 2001:db8:9::2/64  |
| net_prague_fifo   | 2001:db8:a::/64 | prague_sender   | 2001:db8:a::1/64  |
|                   |                 | fifo_deep       | 2001:db8:a::2/64  |


In later updates, we will automate this IPv6 address assignment. 

On all nodes, enable segment routing and IPv6 forwarding. It is also very important to not just enable SRv6 on *default*, but also on specific interfaces. 

> Replace the curly brackets with real interface names on the router nodes. 
```bash
sudo sysctl -w net.ipv6.conf.all.forwarding=1
sudo sysctl -w net.ipv6.conf.all.seg6_enabled=1
sudo sysctl -w net.ipv6.conf.{prage_dualq_interface}.seg6_enabled=1
sudo sysctl -w net.ipv6.conf.{prague_FIFO_interface}.seg6_enabled=1
sudo sysctl -w net.ipv6.conf.{classis_FIFO_interface}.seg6_enabled=1
```

On the L4S Sender node:
```bash
sudo ip route add 12.1.1.128/25 encap seg6 mode encap segs 2001:db8:6::2 dev {Interface to DualQ Node}
```

On the Classic Sender node:
```bash
sudo ip route add 12.1.1.64/26 encap seg6 mode encap segs 2001:db8:5::2 dev {Interface to FIFO Node}
```