from jaaql.mvc.model_interface import JAAQLModelInterface
from jaaql.email.email_manager_service import Email, EmailAttachment


EMAIL_ACC__ctp = "CTP"
EMAIL_ADDR__receive = "jaaql-component-receive@sqmi.nl"
EMAIL_SUB__welcome = "CTP Test Email"
EMAIL_TEMP__ctp_test = "ctp_test"
EMAIL_REPL__ctp_replace = "CTP_REPLACE"
EMAIL_ATTM__name = "email_attachment.txt"


class CTPModel(JAAQLModelInterface):

    def __init__(self, email_templates: dict):
        super().__init__()
        self.email_templates = email_templates

    def test_send(self, signup_data: str):
        replacements = {
            EMAIL_REPL__ctp_replace: signup_data
        }
        attachment_content_handle = open(EMAIL_ATTM__name, "rb")
        attachment_content = attachment_content_handle.read()
        attachment_content_handle.close()
        self.base_model.email_manager.send_email(Email(EMAIL_ACC__ctp, EMAIL_ADDR__receive, EMAIL_SUB__welcome,
                                                       self.email_templates[EMAIL_TEMP__ctp_test],
                                                       html_replacements=replacements,
                                                       attachments=EmailAttachment(attachment_content,
                                                                                   EMAIL_ATTM__name)))
