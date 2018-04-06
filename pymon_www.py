#!/usr/bin/python
import psutil
import requests
import socket
import time
import sys
import os
#------------------------alert settings-------------------------
CARBON_SERVER = ''
CARBON_PORT = 2003
server_name = socket.gethostname()
free_mem = 10  # percents
free_cpu = 10  # percents
free_space = 5  # percents
procs = ['cron', 'apache2', 'pgbouncer', 'redis']
webhook_url = 'https://hooks.slack.com/services/'
# #---------------------------------------------------------
metric_server = "www1"



def slack():
    txt = ""
    if (len(alert_messages)>0):
	for alert in alert_messages:
    	    txt = txt + alert + " on "+server_name+". \n"
	slack_data = '{"text":"'+txt+'", "channel":"#alerts"}'
	r = requests.post(
    	    webhook_url, data=slack_data, timeout=2,
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
    if (disk.mountpoint=="/"):
	metrics.append("host."+metric_server+".root.used "+str(disk_usage.percent))
    else:
	metrics.append("host."+metric_server+"."+ disk.mountpoint.replace("/", "") +".used "+str(disk_usage.percent))
    if (100 - disk_usage.percent) <= free_space:
        alert_messages.append("Partition " + str(disk.mountpoint) + " has " +
            str(100 - disk_usage.percent) + "% free space left")

r = requests.get("http://localhost/server-status?auto")
tmp = r.text.split("\n")
for line in tmp:
    ln = line.split(":")
    if (ln[0].strip() == "ReqPerSec" or ln[0].strip() == "BytesPerSec" or ln[0].strip() == "BusyWorkers" or ln[0].strip() == "IdleWorkers"):
	metrics.append("host."+metric_server+".apache."+ln[0].strip()+" "+str(ln[1].strip()))

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


#print alert_messages
#print metrics
send_metrics(metrics)
slack()
