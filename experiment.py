import threading
import time

# fabric ssh setup
from fabric import Connection


classic_sender = Connection(
    host='pc538.emulab.net',
    user = 'PeterYao',
    port=22,
)




prague_sender = Connection(
    host='pc549.emulab.net',
    user = 'PeterYao',
    port=22,
)


dualq = Connection(
    host='pc557.emulab.net',
    user='PeterYao',
    port=22,
)

fifo_deep = Connection(
    host='pc524.emulab.net',
    user
    = 'PeterYao',  
    port=22,
)

rx = Connection(
    host='pc760.emulab.net',
    user = 'PeterYao',
    port=22,
)

classic_receiver = Connection(
    host='pc536.emulab.net',
    user = 'PeterYao',
    port = 25674,
)

prague_receiver = Connection(
    host='pc536.emulab.net',
    user =  'PeterYao',
    port= 25675,
)

connections = [classic_sender, classic_receiver, prague_sender, dualq, fifo_deep, rx, prague_receiver]

def upload_files():
    classic_sender.put("exp_cubic.sh")
    prague_sender.put("exp_prague.sh")
    dualq.put("monitor_dual.sh")
    fifo_deep.put("monitor_fifo.sh")


def run_prague(idx):
    prague_sender.run(f"./exp_prague.sh {idx}")
    print("Prague script completed")

def run_classic(idx):
    classic_sender.run(f"./exp_cubic.sh {idx}")
    print("Classic script completed")

def run_experiment(iterations, begin_idx=1):
    for i in range(begin_idx, begin_idx + iterations):
        print(f"Running experiment {i}")

        # Kill any existing iperf3 processes on the receiver
        rx.sudo("killall iperf3", warn=True)
        rx.sudo("docker exec rfsim5g-oai-nr-ue1 killall iperf3", pty=False, warn=True)
        rx.sudo("docker exec rfsim5g-oai-nr-ue2 killall iperf3", pty=False, warn=True)
        rx.sudo("docker exec rfsim5g-oai-nr-ue3 killall iperf3", pty=False, warn=True)
        rx.sudo("docker exec rfsim5g-oai-nr-ue4 killall iperf3", pty=False, warn=True)

        prague_receiver.sudo("killall iperf3", warn=True)
        classic_receiver.sudo("killall iperf3", warn=True)

        # Start iperf3 servers in the network namespaces for UE1 and UE2
        rx.sudo("docker exec rfsim5g-oai-nr-ue1 iperf3 -s -1 -p 4008 -D")
        rx.sudo("docker exec rfsim5g-oai-nr-ue2 iperf3 -s -1 -p 4008 -D")
        rx.sudo("docker exec rfsim5g-oai-nr-ue3 iperf3 -s -1 -p 4008 -D")
        rx.sudo("docker exec rfsim5g-oai-nr-ue4 iperf3 -s -1 -p 4008 -D")


        classic_receiver.sudo("iperf3 -s -1 -p 4008 -D")
        prague_receiver.sudo("iperf3 -s -1 -p 4008 -D")

        # Run the iperf command script on the sender side
        prague_sender.sudo("rm -f *json *txt")
        classic_sender.sudo("rm -f *json *txt")

        prague_sender.run("chmod +x exp_prague.sh")
        classic_sender.run("chmod +x exp_cubic.sh")

        # Start cat command on the remote node rx and save to gnb_log_{i}.log
        remote_gnb_log = f"/tmp/gnb_log_{i}.log"
        rx.run(f"nohup cat /tmp/gnb_pipe > {remote_gnb_log} 2>&1 &", pty=False)
        # print(f"Started remote logging for experiment {i} on {remote_gnb_log}")


        # Start the monitoring scripts on dualq and fifo routers
        dualq.run(f"nohup bash ./monitor_dual.sh br0 300 0.002 > dualq_monitor_{i}.txt 2>&1 &")
        fifo_deep.run(f"nohup bash ./monitor_fifo.sh br0 300 0.002 > fifo_monitor_{i}.txt 2>&1 &")
        # Create threads for prague and classic scripts
        thread1 = threading.Thread(target=run_prague, args=(i,))
        thread2 = threading.Thread(target=run_classic, args=(i,))

        # Start both threads
        thread1.start()
        thread2.start()

        # Wait for both threads to complete
        thread1.join()
        thread2.join()

        print("Both scripts completed")
        
        # Stop the cat process on the remote node
        rx.sudo("pkill -f 'cat /tmp/gnb_pipe'", warn=True)
        print(f"Stopped remote logging for experiment {i}")

        # Retrieve the results from the prague sender
        prague_sender.get(f"{i}-ss-prague-cross-traffic.txt")
        prague_sender.get(f"{i}-ss-prague.txt")
        prague_sender.get(f"{i}-iperf-prague-cross-traffic.json")
        prague_sender.get(f"{i}-iperf-prague.json")


        # Retrieve the results from the classic sender
        classic_sender.get(f"{i}-ss-cubic-cross-traffic.txt")
        classic_sender.get(f"{i}-ss-cubic.txt")
        classic_sender.get(f"{i}-ss-cubic-2.txt")
        classic_sender.get(f"{i}-ss-cubic-3.txt")

        classic_sender.get(f"{i}-iperf-cubic-cross-traffic.json")
        classic_sender.get(f"{i}-iperf-cubic.json")
        classic_sender.get(f"{i}-iperf-cubic-2.json")
        classic_sender.get(f"{i}-iperf-cubic-3.json")



        # Retrieve the results from the dualpi queue and fifo queue
        dualq.get(f"dualq_monitor_{i}.txt")
        fifo_deep.get(f"fifo_monitor_{i}.txt")


        # Download the remote gnb log to local
        local_gnb_log = f"gnb_log_{i}.log"
        rx.get(remote_gnb_log, local_gnb_log)
        print(f"Downloaded gNB log to local: {local_gnb_log}")

        print(f"Experiment {i} completed")

upload_files()
run_experiment(5, 47)
