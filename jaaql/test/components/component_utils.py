from datetime import datetime
import requests
from jaaql.utilities.utils import time_delta_ms
import time

MAX_STARTUP_TIME_MS = 120000
BASE_URL = "http://127.0.0.1/api"


def wait_for_service():
    service_started = False
    start_time = datetime.now()
    finish_time = None
    while not service_started:
        try:
            print("Awaiting CTP bootup")
            status = requests.get(BASE_URL + "/ctp/hello").status_code
            if status == 200:
                service_started = True
                finish_time = datetime.now()
        except:
            pass
        if time_delta_ms(start_time, datetime.now()) > MAX_STARTUP_TIME_MS:
            raise Exception("CTP did not boot in the required time")
        time.sleep(5)

    print("CTP booted in " + str(time_delta_ms(start_time, finish_time)) + "ms")
