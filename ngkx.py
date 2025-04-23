import numpy as np

class LoggingAgent(Agent):
    def __getattribute__(self, name):
        attr = super().__getattribute__(name)
        if callable(attr) and not name.startswith('_'):
            return log_method_call(attr)
        return attr

def log_method_call(method):
    def wrapper(*args, **kwargs):
        print(f"Calling {method.__name__} with args={args}, kwargs={kwargs}")
        result = method(*args, **kwargs)
        print(f"{method.__name__} returned {result}")
        return result
    return wrapper


