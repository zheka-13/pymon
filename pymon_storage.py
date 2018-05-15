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
procs = ['cron', 'apache', 'pgbouncer']
webhook_url = 'https://'
# #---------------------------------------------------------
metric_server = "storage"



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

box = psutil.disk_usage('/srv/box')
metrics.append("host."+metric_server+".disk.used "+str(box.percent))

wavs = 0
for filename in os.listdir("/srv/box/from_lira"):
    if os.path.isdir("/srv/box/from_lira/"+str(filename)):
	lst = os.listdir("/srv/box/from_lira/"+str(filename))
	wavs = wavs + len(lst)

lst = os.listdir("/srv/box/to_drive")
to_drive = len(lst)
lst2 = os.listdir("/srv/box/to_drive_errors")
to_drive_errors = len(lst2)

metrics.append("host."+metric_server+".files.wav "+str(wavs))
metrics.append("host."+metric_server+".files.files_to_upload "+str(to_drive))
metrics.append("host."+metric_server+".files.files_to_upload_errors "+str(to_drive_errors))

#print alert_messages
#print metrics
send_metrics(metrics)
slack()
