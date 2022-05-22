import os

from .base_component import *
import imaplib
import email
import ssl

MAX_EMAIL_TIME_MS = 300000
EMAIL_HOST_URL = "web119.shared.hosting-login.net"
EMAIL_USERNAME = "jaaql-component-receive@sqmi.nl"
EMAIL_ENV_PASSWORD = "COMPONENT_EMAIL_PASSWORD"
EMAIL_IMAP_PORT = 993
EMAIL_FROM = "jaaql-component-send@sqmi.nl"


class SignupComponent(BaseComponent):

    def test_signup(self):
        self.create_email_template()

    def create_email_template(self):
        pass
        # requests.post(BASE_INTERNAL_URL + "/internal/emails/templates", json={
        #     "name": "signup",
        #     "account": "Notification account",
        #     "description": "The signup email template",
        #     "app_relative_path": "my_template",
        #     "subject": "Welcome to JAAQL",
        #     "allow_signup": True,
        #     "allow_confirm_signup_attempt": False,
        #     "data_validation_table": "ctp_data_validation_table"
        # })

    def perform_signup_tests(self):
        pass
#         auth_token = self.get_jaaql_auth_header()
#
#         replacement_data = "replaced at " + str(datetime.now())
#         resp = requests.post(BASE_URL + "/ctp/send_email", json={
#             "email_data": replacement_data
#         }, headers={HEADER_AUTH: auth_token})
#
#         self.assertEqual(HTTPStatus.OK, resp.status_code, "Response ok")
#
#         expected_subject = "CTP Test Email"
#         expected_body = """<html lang="en">
#     <head><title>CTP Test Email</title></head>
#     <body>
#         This is the CTP test email with data %s
#     </body>
# </html>""" % replacement_data
#         expected_body.replace("\r\n", "\n").replace("\n", "\r\n")  # Not a mistake. Double prevents \r\r\n
#         expected_attachment = "This is the content of the email attachment"
#         expected_attachment_filename = "email_attachment.txt"
#
#         actual_subject, actual_body, actual_attachment, actual_attachment_filename = self.read_email()
#
#         self.assertEqual(expected_subject, actual_subject)
#         self.assertEqual(expected_body, actual_body)
#         self.assertEqual(expected_attachment, actual_attachment)
#         self.assertEqual(expected_attachment_filename, actual_attachment_filename)

    def fetch_imap_conn(self, context: ssl.SSLContext):
        conn = imaplib.IMAP4_SSL(EMAIL_IMAP_URL, EMAIL_IMAP_PORT, ssl_context=context)
        conn.login(EMAIL_USERNAME, os.environ[EMAIL_ENV_PASSWORD])
        conn.select(readonly=0)
        return conn

    def read_email(self):
        context = ssl.SSLContext()
        conn = self.fetch_imap_conn(context)
        start_time = datetime.now()

        email_subject = None
        email_body = None
        email_attachment = None
        email_attachment_filename = None

        while time_delta_ms(start_time, datetime.now()) < MAX_EMAIL_TIME_MS:
            try:
                retcode, messages = conn.search(None, '(UNSEEN)')
                for msg_id in messages[0].split():
                    typ, data = conn.fetch(msg_id, '(RFC822)')
                    msg = email.message_from_bytes(data[0][1])
                    conn.store(msg_id, '+FLAGS', '\\Seen')
                    from_email = msg['From']

                    if '<' in from_email:
                        from_email = from_email.split("<")[1].split(">")[0]

                    if from_email == EMAIL_FROM:
                        email_subject = msg['subject']
                        for part in msg.walk():
                            if part.get_filename() is None:
                                if part.get_content_type() == "text/plain" and email_body is None:
                                    email_body = part.get_payload(decode=True).decode("ASCII")
                                elif part.get_content_type() == "text/html":
                                    email_body = part.get_payload(decode=True).decode("ASCII")
                            else:
                                email_attachment = part.get_payload(decode=True).decode("ASCII")
                                email_attachment_filename = part.get_filename()
                        break
                if email_body is not None:
                    break
            except imaplib.IMAP4.error as ex:
                conn.logout()
                conn = self.fetch_imap_conn(context)
            time.sleep(5)

        return email_subject, email_body, email_attachment, email_attachment_filename
