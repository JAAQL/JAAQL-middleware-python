from jaaql.mvc.base_model import BaseJAAQLModel
from abc import ABC


class JAAQLModelInterface(ABC):
    def __init__(self):
        self.base_model: BaseJAAQLModel = None

    def set_model(self, base_model: BaseJAAQLModel):
        self.base_model = base_model
