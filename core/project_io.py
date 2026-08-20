from abc import ABC, abstractmethod


class Model(ABC):

    name = "BaseModel"
    description = ""
    inputs = []
    outputs = []
    version = "0.1"

    def __init__(self):
        pass

    @abstractmethod
    def execute(self, state):
        pass

    def validate(self, state):
        return True

    def reset(self):
        pass

    def __str__(self):
        return f"{self.name} (v{self.version})"
