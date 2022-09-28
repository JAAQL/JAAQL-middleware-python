from jaaql.utilities.utils_no_project_imports import time_delta_ms
import requests
from datetime import datetime
from threading import Event
import threading

WARMUP_REQS = 25
REQS = 1000
THREAD_COUNT = 20


def do_perf(num_req: int, ev: Event, ret_ev: Event):
    res = requests.post("http://127.0.0.1/api/oauth/token", json={"tenant": "default", "username": "super", "password": "passw0rd"}).json()
    ret_ev.set()
    ev.wait()
    for _ in range(num_req):
        requests.post("http://127.0.0.1/api/submit", json={"query": "SELECT version();"}, headers={"Authentication-Token": res})
    ret_ev.set()


the_ev = Event()
the_ret_ev = Event()
threading.Thread(target=do_perf, args=[WARMUP_REQS, the_ev, the_ret_ev]).start()  # Warmup
the_ret_ev.wait()
the_ret_ev.clear()
the_ev.set()
the_ret_ev.wait()

the_evs = []
the_ret_evs = []
for _ in range(THREAD_COUNT):
    the_ev = Event()
    the_ret_ev = Event()
    the_evs.append(the_ev)
    the_ret_evs.append(the_ret_ev)
    threading.Thread(target=do_perf, args=[REQS, the_ev, the_ret_ev], daemon=True).start()

for i in range(THREAD_COUNT):
    the_ret_evs[i].wait()
    the_ret_evs[i].clear()

start_time = datetime.now()
for i in range(THREAD_COUNT):
    the_evs[i].set()
for i in range(THREAD_COUNT):
    the_ret_evs[i].wait()
finished = datetime.now()

total_requests = REQS * THREAD_COUNT
req_sec = total_requests * 1000 / time_delta_ms(start_time, finished)
req_sec = "{:.2f}".format(req_sec)

print("Completed: " + str(total_requests) + " in " + str(time_delta_ms(start_time, finished)) + "ms. " + req_sec + " reads/second")
