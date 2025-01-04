This document is about what to install, compile, and how to start some software to reproduce the wireless network. 

This [Blog](https://witestlab.poly.edu/blog/p/a3237270-ea93-4c13-bdac-8ae174fe5446/) is a helpful supplement. But it is on an older version of Ubuntu, while we are using Ubunut22. So some operations like installing gcc-9 is not needed here. 

## Get Extra Space on POWDER
Due to the volume of space we are going to take up, it is recommended to ressarve extra space on POWDER tested. 

```bash
cd /
sudo mkdir mydata
sudo /usr/local/etc/emulab/mkextrafs.pl -f /mydata

# change the ownership of this new space
username=$(whoami)
groupname=$(id -gn)

sudo chown $username:$groupname mydata
chmod 775 mydata
# verify the result
ls -ld mydata
```
## CMake and Misc

You also need newer cmake.
```bash
cd /mydata
wget https://github.com/Kitware/CMake/releases/download/v3.27.0/cmake-3.27.0.tar.gz
tar -xzvf cmake-3.27.0.tar.gz
cd cmake-3.27.0
./bootstrap

make -j 8
sudo make install

export PATH=/users/PeterYao/cmake-3.27.0/bin:$PATH

cmake --version
```

verify that you have cmake version 27.

You need to install the libpcre2-dev

```bash
sudo apt-get install -y libpcre2-dev
```

## OpenAirInterface & FlexRIC Installation
We use a slighlty modified version of OpenAirInterface that has slicing enabled and a smaller RLC buffer size (2MB) than the default for better latency in general, available at this [Repository](https://github.com/PeterYaoNYU/OAI_Modified). You may clone it. Also, we use a slightly modified flexric that enforeces fair slicing. Check git log for information of what changes we make. It is less than 100 LoC.  

```bash
# you are at /mydata
cd /mydata
git clone https://github.com/PeterYaoNYU/modified-flexric.git
cd flexric/
git checkout rc_slice_xapp

# for oai, first git clone the latest version
cd /mydata
git clone https://github.com/PeterYaoNYU/OAI_Modified.git
cd openairinterface5g
cd cmake_targets
```

And you should compile OAI with the commands:
```bash
cd /mydata/openairinterface5g  
cd cmake_targets  
./build_oai -I -w SIMU --gNB --nrUE --build-e2 --ninja
```

Before compiling flexric, because of SWIG, also need to install python dev header
```bash
sudo apt update
sudo apt install python3-dev
```

To compile FlexRIC:
```bash
cd /mydata
git clone https://github.com/swig/swig.git
cd swig
git checkout release-4.1
./autogen.sh
./configure --prefix=/usr/
make -j8
sudo make install

cd /mydata/flexric && mkdir build && cd build && cmake .. && make -j8 
sudo make install
```

## 5G Core Network
Because we work with TCP Prague, we would have to use Ubuntu22. This requires us to install a specific docker engine so that OAI core can run, and it is not the latest version.

```bash
sudo apt-get remove docker docker-engine docker.io containerd runc
sudo apt-get purge docker-ce docker-ce-cli containerd.io

sudo apt-get update
sudo apt-get install ca-certificates curl gnupg lsb-release

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update

sudo apt-get install docker-ce=5:20.10.13~3-0~ubuntu-jammy docker-ce-cli=5:20.10.13~3-0~ubuntu-jammy containerd.io

sudo rm /usr/local/bin/docker-compose


sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

sudo chmod +x /usr/local/bin/docker-compose

docker-compose --version

```
it may happen that this version does not exist, check the available version for your distribution:

```bash
apt-cache madison docker-ce
```

Here are several things that we would need to get the containerized version runnning:

They are all in the repo: https://github.com/PeterYaoNYU/core-network-5g. You just need to copy paste them to the correct folder. 

1. A docker compose file for running the container: note that you should use this version specifically: oaisoftwarealliance/oai-nr-ue:2024.w30. Later version has issues with the ran-configuration. 

```yaml
version: '3.8'
services:
    oai-nr-ue1:
        image: oaisoftwarealliance/oai-nr-ue:2024.w30
        privileged: true
        container_name: rfsim5g-oai-nr-ue1
        environment: 
            RFSIMULATOR: 10.201.1.100
            USE_ADDITIONAL_OPTIONS: --sa --rfsim -r 106 --numerology 1 -C 3619200000 
        volumes:
            - ./ran-conf/ue1.conf:/opt/oai-nr-ue/etc/nr-ue.conf
        networks:
            - ue1_net
        healthcheck:
            test: /bin/bash -c "pgrep nr-uesoftmodem"
            interval: 10s
            timeout: 5s
            retries: 5

    oai-nr-ue2:
        image: oaisoftwarealliance/oai-nr-ue:2024.w30
        privileged: true
        container_name: rfsim5g-oai-nr-ue2
        environment: 
            RFSIMULATOR: 10.203.1.100
            USE_ADDITIONAL_OPTIONS: --sa --rfsim -r 106 --numerology 1 -C 3619200000 
        volumes:
            - ./ran-conf/ue2.conf:/opt/oai-nr-ue/etc/nr-ue.conf
        networks:
            - ue1_net
        healthcheck:
            test: /bin/bash -c "pgrep nr-uesoftmodem"
            interval: 10s
            timeout: 5s
            retries: 5

    oai-nr-ue3:
        image: oaisoftwarealliance/oai-nr-ue:2024.w30
        privileged: true
        container_name: rfsim5g-oai-nr-ue3
        environment: 
            RFSIMULATOR: 10.203.1.100
            USE_ADDITIONAL_OPTIONS: --sa --rfsim -r 106 --numerology 1 -C 3619200000 
        volumes:
            - ./ran-conf/ue3.conf:/opt/oai-nr-ue/etc/nr-ue.conf
        networks:
            - ue1_net
        healthcheck:
            test: /bin/bash -c "pgrep nr-uesoftmodem"
            interval: 10s
            timeout: 5s
            retries: 5

    oai-nr-ue4:
        image: oaisoftwarealliance/oai-nr-ue:2024.w30
        privileged: true
        container_name: rfsim5g-oai-nr-ue4
        environment: 
            RFSIMULATOR: 10.203.1.100
            USE_ADDITIONAL_OPTIONS: --sa --rfsim -r 106 --numerology 1 -C 3619200000 
        volumes:
            - ./ran-conf/ue4.conf:/opt/oai-nr-ue/etc/nr-ue.conf
        networks:
            - ue1_net
        healthcheck:
            test: /bin/bash -c "pgrep nr-uesoftmodem"
            interval: 10s
            timeout: 5s
            retries: 5
networks:
    ue1_net:
        driver: bridge

```

2. Specific UE configurations

UE4 configuration
```
uicc0 = {
imsi = "208950000000034";
key = "0C0A34601D4F07677303652C0462535B";
opc= "63bfa50ee6523365ff14c1f45f88737d";
dnn= "oai.ipv4";
nssai_sst=1;
nssai_sd=5;
}
```


UE3 configuration
```
uicc0 = {
imsi = "208950000000033";
key = "0C0A34601D4F07677303652C0462535B";
opc= "63bfa50ee6523365ff14c1f45f88737d";
dnn= "oai.ipv4";
nssai_sst=1;
nssai_sd=5;
}
```


UE2 configuration
```
uicc0 = {
imsi = "208950000000032";
key = "0C0A34601D4F07677303652C0462535B";
opc= "63bfa50ee6523365ff14c1f45f88737d";
dnn= "oai.ipv4";
nssai_sst=1;
nssai_sd=5;
}
```

UE1 conf

```
uicc0 = {
imsi = "208950000000031";
key = "0C0A34601D4F07677303652C0462535B";
opc= "63bfa50ee6523365ff14c1f45f88737d";
dnn= "oai";
nssai_sst=1;
nssai_sd=1;
}
```

No need for manual file creating. Clone my repo to /mydata, and execute. 

```bash
cd /mydata

git clone https://github.com/PeterYaoNYU/core-network-5g.git

cp /mydata/core-network-5g/*.conf /mydata/oai-cn5g-fed/docker-compose/ran-conf/

cp /mydata/core-network-5g/etc/core-slice-conf/basic* /mydata/oai-cn5g-fed/docker-compose/conf

cp /mydata/core-network-5g/etc/new_core_network.py /mydata/oai-cn5g-fed/docker-compose  
```


To bring up the core network:
```bash
cd /mydata/oai-cn5g-fed/docker-compose
sudo python3 ./new_core_network.py --type stop-basic --scenario 1
sudo python3 ./new_core_network.py --type start-basic --scenario 1
```

After bringing up the core network, do this in the main network namespace:

```bash
sudo ip route add 12.1.1.64/26 via 192.168.70.140

sudo ip route add 12.1.1.128/25 via 192.168.70.134

sudo iptables -P FORWARD ACCEPT
```

For correct routing to the UEs throuugh UPF. 

## Bring up GNodeB. 
I suggest running the GNb and UE in tmux. 

To enable RFSimulator, We need 2 separate network namespaces. 

```bash

cd /mydata  
git clone https://gitlab.eurecom.fr/oaiworkshop/summerworkshop2023.git  
sudo /mydata/summerworkshop2023/ran/multi-ue.sh -c1 -e  
# default route back to the main namespace. Necessary for 2 way communication. Missing from the workshop script. 
sudo ip route add default via 10.201.1.100
```

Ctrl D back to the main namespace and add another one:

```bash
sudo /mydata/summerworkshop2023/ran/multi-ue.sh -c3 -e 

sudo ip route add default via 10.203.1.100
```


The namespaces go away eveytime you reboot. It does not persist.

Copy the gnb configuration. Modified to enable MAC Layer debug level logging, which enabled us to monitor the RLC buffer. 
```
cp -r /mydata/core-network-5g/etc -r /local/repository/
```



We are ready to bring up the GNodeB.



```bash
cd /mydata/openairinterface5g/cmake_targets  
sudo RFSIMULATOR=server ./ran_build/build/nr-softmodem -O /local/repository/etc/gnb.conf --sa --rfsim  
```

Bring UP 4UEs. 

And finally we bring up the conainerized UE, recommended to bring up in 4 separate tmux tabs. 

```bash
cd /mydata/oai-cn5g-fed/docker-compose/
sudo docker-compose -f docker-compose-ue-slice1.yaml up oai-nr-ue1

cd /mydata/oai-cn5g-fed/docker-compose/
sudo docker-compose -f docker-compose-ue-slice1.yaml up oai-nr-ue2

cd /mydata/oai-cn5g-fed/docker-compose/
sudo docker-compose -f docker-compose-ue-slice1.yaml up oai-nr-ue3

cd /mydata/oai-cn5g-fed/docker-compose/
sudo docker-compose -f docker-compose-ue-slice1.yaml up oai-nr-ue4
```

For sanity check, ping on the 5g node:
```
ping 12.1.1.130
ping 12.1.1.66
```

It shoud work. 

Bring up the flexric:
```bash
cd /mydata/flexric/  
./build/examples/ric/nearRT-RIC
```

## Install L4S

We have prepared a separate [jupyter notebook](./l4s_setup.ipynb) that talks about how to do L4S setup and installation. To install L4S on all necessary nodes, just execute the whole notebook. 

> the first code block needs to be setup using your own POWDER SSH connection. Nothing else needs to be customized.  