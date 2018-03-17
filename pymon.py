#!/usr/bin/python
import psutil
import requests
import socket
import time
import sys

#------------------------alert settings-------------------------
CARBON_SERVER = 'carbon.example.net'
CARBON_PORT = 2003
server_name = socket.gethostname()
free_mem = 10  # percents
free_cpu = 10  # percents
free_space = 5  # percents
procs = ['lvp', 'cron', 'apache', 'pgbouncer', 'redis', 'stun']
webhook_url = 'https://hooks.slack.com/XXXXXXXXXXXXXXXXXXXXXXXXXXXX'
# #---------------------------------------------------------
metric_server = "db"



def slack():
    txt = ""
    for alert in alert_messages:
        txt = txt + alert + " on "+server_name+". \n"
    slack_data = '{"text":"'+txt+'", "channel":"#alerts"}'
    requests.post(
        webhook_url, data=slack_data,
        headers={'Content-Type': 'application/json'}
    )
    return

def send_metrics(m):
    if (len(m)>0):
	timestamp = int(time.time())
	message = "";
	for mes in m:
	    message = message + mes + " "+ str(timestamp) + "\n"
	sock = socket.socket()
	sock.connect((CARBON_SERVER, CARBON_PORT))
	sock.sendall(message)
	sock.close()



metrics = []
alert_messages = []

cpu_data =  psutil.cpu_times_percent(interval=1)
metrics.append("host."+metric_server+".cpu.user "+str(cpu_data.user))
metrics.append("host."+metric_server+".cpu.system "+str(cpu_data.system))
metrics.append("host."+metric_server+".cpu.iowait "+str(cpu_data.iowait))

cpus = psutil.cpu_percent(interval=1, percpu=True)
for cpu in cpus:
    if cpu >= (100 - free_cpu):
        alert_messages.append("One of CPU cores usage is " + str(cpu) + "%")

mem = psutil.virtual_memory()
metrics.append("host."+metric_server+".memory.used "+str(mem.percent))

if mem.available*100/mem.total <= free_mem:
    alert_messages.append("Free memory is less than " + str(free_mem) + "%")

disks = psutil.disk_partitions()
for disk in disks:
    disk_usage = psutil.disk_usage(disk.mountpoint)
    if (100 - disk_usage.percent) <= free_space:
        alert_messages.append("Partition " + str(disk.mountpoint) + " has " +
            str(100 - disk_usage.percent) + "% free space left")


lvp_procs = {'total' : 0, 'op' : 0, 'dlr' : 0, 'calls' : 0}
for proc in psutil.process_iter(attrs=['cmdline', 'name']):
    if proc.info['name'] == 'lvp':
	if (len(proc.info['cmdline'])==1):
	    cmd = proc.info['cmdline'][0]
	elif (len(proc.info['cmdline'])==2):
	    cmd = proc.info['cmdline'][1]
	else:
	    cmd = proc.info['cmdline'][0]
	lvp_procs['total'] +=1
	if "WM_Conn" in cmd:
	    lvp_procs['op'] +=1
	elif "#comp" in cmd:
	    lvp_procs['dlr'] +=1
	elif "lvp_" in cmd:
	    continue 
	else:
	    lvp_procs['calls'] +=1

metrics.append("host."+metric_server+".procs.total "+str(lvp_procs['total']))
metrics.append("host."+metric_server+".procs.calls "+str(lvp_procs['calls']))


for proc in psutil.process_iter():
    try:
        pinfo = proc.as_dict(attrs=['pid', 'name'])
    except psutil.NoSuchProcess:
        pass
    else:
        for p in procs:
            if (p == pinfo["name"] or p in pinfo["name"]) and p in procs:
                procs.remove(p)
for p in procs:
    alert_messages.append("Process " + p + " is dead")

print alert_messages
slack()
send_metrics(metrics)
