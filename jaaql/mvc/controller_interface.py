from jaaql.mvc.base_controller import BaseJAAQLController
from abc import abstractmethod, ABC


class JAAQLControllerInterface(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def route(self, base_controller: BaseJAAQLController):
        pass
