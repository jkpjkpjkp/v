from openai import OpenAI
import inspect
import os

os.environ['OPENAI_API_KEY'] = os.environ['OPENROUTER_API_KEY']
os.environ['OPENAI_BASE_URL'] = 'https://openrouter.ai/api/v1'
model = 'google/gemini-2.5-flash-preview:thinking'

def has_model_param(func):
    """
    Check if a function accepts a 'model' parameter.
    """
    try:
        sig = inspect.signature(func)
        return 'model' in sig.parameters
    except (TypeError, ValueError):
        return False

class ModelWrapper:
    """
    A wrapper that injects a default 'model' parameter into callable attributes
    if the method accepts it and it is not already provided.
    """
    def __init__(self, obj, default_model):
        self._obj = obj
        self.default_model = default_model

    def __getattr__(self, name):
        attr = getattr(self._obj, name)
        if callable(attr):
            def wrapper(*args, **kwargs):
                if has_model_param(attr) and 'model' not in kwargs:
                    kwargs['model'] = self.default_model
                return attr(*args, **kwargs)
            return wrapper
        else:
            return ModelWrapper(attr, self.default_model)

class OpenAIWrapper:
    """
    A wrapper around the OpenAI client that sets a default model for API calls.
    """
    def __init__(self, default_model, **kwargs):
        self._client = ModelWrapper(OpenAI(**kwargs), default_model)

    def __getattr__(self, name):
        return getattr(self._client, name)

client = OpenAIWrapper(model)
format = 'png'