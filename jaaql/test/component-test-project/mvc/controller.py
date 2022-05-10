from documentation.documentation_ctp import DOCUMENTATION__hello, DOCUMENTATION__send_email, KEY__email_data
from jaaql.mvc.controller_interface import JAAQLControllerInterface, BaseJAAQLController
from mvc.model import CTPModel


class CTPController(JAAQLControllerInterface):

    def __init__(self, model: CTPModel):
        super().__init__()
        self.model = model

    def route(self, base_controller: BaseJAAQLController):

        @base_controller.cors_route('/ctp/hello', DOCUMENTATION__hello)
        def return_hello():
            return

        @base_controller.cors_route('/ctp/send_email', DOCUMENTATION__send_email)
        def send_email(http_inputs: dict):
            self.model.test_send(http_inputs[KEY__email_data])
