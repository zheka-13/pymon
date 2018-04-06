#!/usr/bin/python
import psutil
import requests
import socket
import time
import sys
import os
import psycopg2
from datetime import datetime

#------------------------alert settings-------------------------
CARBON_SERVER = ''
CARBON_PORT = 2003
server_name = socket.gethostname()
free_mem = 10  # percents
free_cpu = 10  # percents
free_space = 5  # percents
procs = ['postmaster']
webhook_url = 'https://hooks.slack.com'
# #---------------------------------------------------------
metric_server = "db"


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
conn = psycopg2.connect("host=127.0.0.1 port=5432 dbname=postgres user=postgres")

cpu_data =  psutil.cpu_times_percent(interval=1)
metrics.append("host."+metric_server+".cpu.user "+str(cpu_data.user))
metrics.append("host."+metric_server+".cpu.system "+str(cpu_data.system))
metrics.append("host."+metric_server+".cpu.iowait "+str(cpu_data.iowait))

cpus = psutil.cpu_percent(interval=1, percpu=True)
for cpu in cpus:
    if cpu >= (100 - free_cpu):
        alert_messages.append("One of CPU cores usage is " + str(cpu) + "%")
    if cpu>80:
	cur2 = conn.cursor()
	cur2.execute("select query_start, waiting, query, pid, state, now()-query_start from pg_stat_activity where state='active' order by query_start asc")
	row2 = cur2.fetchone()
	fname = time.strftime("procs_%d_%b_%Y_%H_%M_%S.log", time.gmtime())
	_file_stat = "";
	while row2 is not None:
	    _file_stat = _file_stat + str(row2[5]) + ' ' + str(row2[3]) +' '+str(row2[4])+' '+str(row2[1])+' ' +str(row2[2])+"\n"
	    row2 = cur2.fetchone()
	f = open('/tmp/'+fname, 'w')
	f.write(_file_stat+"\n")
	f.close()
	cur2.close()

mem = psutil.virtual_memory()
metrics.append("host."+metric_server+".memory.used "+str(mem.percent))

if mem.available*100/mem.total <= free_mem:
    alert_messages.append("Free memory is less than " + str(free_mem) + "%")

disks = psutil.disk_partitions()
for disk in disks:
    disk_usage = psutil.disk_usage(disk.mountpoint)
    if (disk.mountpoint=="/usr"):
	metrics.append("host."+metric_server+".disk.usr.used "+str(disk_usage.percent))
    if (disk.mountpoint=="/var"):
	metrics.append("host."+metric_server+".disk.var.used "+str(disk_usage.percent))
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

cur = conn.cursor()
cur.execute("SELECT count(*) as cnt, state FROM pg_stat_activity group by state")
row = cur.fetchone()
while row is not None:
    if row[1] is not None:
	metrics.append("host."+metric_server+".conns."+row[1].replace(" ", "_")+" "+str(row[0]))
    if row[0]>50 and row[1] == "active" :
	cur2 = conn.cursor()
	cur2.execute("select query_start, waiting, query, pid, state, now()-query_start from pg_stat_activity where state='active' order by query_start asc")
	row2 = cur2.fetchone()
	fname = time.strftime("procs_%d_%b_%Y_%H_%M_%S.log", time.gmtime())
	_file_stat = "";
	_stat = time.strftime("[%a, %d %b %Y %H:%M:%S +0000]", time.gmtime())+" =================================================\n"
	while row2 is not None:
	    _stat = _stat + str(row2[0]) + ' ' +str(row2[1])+' ' +str(row2[2])+"\n"
	    _file_stat = _file_stat + str(row2[5]) + ' ' + str(row2[3]) +' '+str(row2[4])+' '+str(row2[1])+' ' +str(row2[2])+"\n"
	    row2 = cur2.fetchone()
	f = open('/srv/procs.log', 'a')
	f.write(_stat+"\n")
	f.close()
	f = open('/tmp/'+fname, 'w')
	f.write(_file_stat+"\n")
	f.close()
	cur2.close()
    row = cur.fetchone()
cur.execute("SELECT pg_xlog_location_diff(sent_location, replay_location) AS byte_lag FROM pg_stat_replication")
row = cur.fetchone()
metrics.append("host."+metric_server+".lag "+str(row[0]))
timestamp = int(time.time())
cur.execute("select sum(xact_commit + xact_rollback), sum(tup_inserted), sum(tup_updated), sum(tup_deleted), sum(tup_fetched), sum(tup_returned) from pg_stat_database")
row = cur.fetchone()
if os.path.isfile("/srv/data.json"):
    f = open('/srv/data.json', 'r')
    s = f.read();
    data  = s.split(":")
    f.close()
    if ((timestamp - int(data[0]))<120):
	metrics.append("host."+metric_server+".transactions "+str(row[0]-int(data[1])))
	metrics.append("host."+metric_server+".inserts "+str(row[1]-int(data[2])))
	metrics.append("host."+metric_server+".updates "+str(row[2]-int(data[3])))
	metrics.append("host."+metric_server+".deletes "+str(row[3]-int(data[4])))
	metrics.append("host."+metric_server+".selects "+str(row[4]-int(data[5])))
	metrics.append("host."+metric_server+".returned "+str(row[5]-int(data[6])))
f = open('/srv/data.json', 'w')
f.write(str(timestamp)+":"+str(row[0])+":"+str(row[1])+":"+str(row[2])+":"+str(row[3])+":"+str(row[4])+":"+str(row[5]))
f.close() 

cur.close()
conn.close()

#print metrics
send_metrics(metrics)
slack()
