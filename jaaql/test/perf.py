import requests
from datetime import datetime
import threading
import random

API_URL = "http://localhost/api"
ENDPOINT_OAUTH = "/oauth/token"
ENDPOINT_SUBMIT = "/submit"
ENDPOINT_CONFIGS = "/configurations"
ENDPOINT_ARGS = "/configurations/arguments"
CONCURRENT = 1
CREDS = [
    {
        "username": "jaaql",
        "password": "pa55word"
    },
    {
        "username": "superjaaql",
        "password": "passw0rd"
    }
]


def run_perf_tests():
    while True:
        # res = requests.post(API_URL + ENDPOINT_OAUTH, json=CREDS[1 if random.random() > 0.5 else 0])
        res = requests.post(API_URL + ENDPOINT_OAUTH, json=CREDS[0])
        print(datetime.now(), end=" ")
        print(res.status_code)
        if res.status_code != 200:
            continue
        token = res.json()

        auth_headers = {
            "Authentication-Token": token
        }

        res = requests.get(API_URL + ENDPOINT_CONFIGS + "?application=console", headers=auth_headers)
        print(datetime.now(), end=" ")
        print(res.status_code)
        if res.status_code != 200:
            continue
        configuration_name = res.json()[0]["configuration"]

        res = requests.get(API_URL + ENDPOINT_ARGS + "?application=console&configuration=" + configuration_name,
                           headers=auth_headers)
        print(datetime.now(), end=" ")
        print(res.status_code)
        if res.status_code != 200:
            continue
        connection = res.json()[0]["connection"]

        res = requests.post(API_URL + ENDPOINT_SUBMIT, json={
            "query": "SELECT * FROM current_database();",
            "connection": connection,
            "database": "database" + str(random.randint(0, 9))
        }, headers=auth_headers)

        print(datetime.now(), end=" ")
        print(res.status_code)


if __name__ == "__main__":
    for i in range(CONCURRENT):
        threading.Thread(target=run_perf_tests).start()