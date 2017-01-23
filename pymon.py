#!/usr/bin/python
import psutil
import requests


#------------------------alert settings-------------------------
server_name = "server"
free_mem = 10  # percents
free_cpu = 10  # percents
free_space = 5  # percents
procs = []
webhook_url = 'https://hooks.slack.com/services/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
# #---------------------------------------------------------


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


alert_messages = []
cpus = psutil.cpu_percent(interval=1, percpu=True)
for cpu in cpus:
    if cpu >= (100 - free_cpu):
        alert_messages.append("One of CPU cores usage is " + str(cpu) + "%")

mem = psutil.virtual_memory()
if mem.available*100/mem.total <= free_mem:
    alert_messages.append("Free memory is less than " + str(free_mem) + "%")

disks = psutil.disk_partitions()
for disk in disks:
    disk_usage = psutil.disk_usage(disk.mountpoint)
    if (100 - disk_usage.percent) <= free_space:
        alert_messages.append("Partition " + str(disk.mountpoint) + " has " +
            str(100 - disk_usage.percent) + "% free space left")

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

