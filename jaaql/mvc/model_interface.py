from jaaql.mvc.model import JAAQLModel
from abc import ABC


class JAAQLModelInterface(ABC):
    def __init__(self):
        self.base_model: JAAQLModel = None

    def set_model(self, base_model: JAAQLModel):
        self.base_model = base_model
