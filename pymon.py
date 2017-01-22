#!/usr/bin/python
import psutil

#------------------------alert settings-------------------------
free_mem = 10  # percents
free_cpu = 10  # percents
free_space = 5  # percents
# #---------------------------------------------------------

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
print alert_messages
