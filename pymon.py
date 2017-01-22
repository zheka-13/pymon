#!/usr/bin/python
import psutil
alert_messages = []
cpus = psutil.cpu_percent(interval=1, percpu=True)
for cpu in cpus:
    if cpu > 90:
        alert_messages.append("One of CPU cores usage is " + str(cpu))

print alert_messages
