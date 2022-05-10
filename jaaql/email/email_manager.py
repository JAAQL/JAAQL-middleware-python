from jaaql.email.email_manager_service import Email, PORT__ems
import requests


class EmailManager:

    def send_email(self, email: Email):
        requests.post("http://127.0.0.1:" + str(PORT__ems) + "/send-email", json=email.repr_json())
