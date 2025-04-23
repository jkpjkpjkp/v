import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI
from docstring_parser import parse
import math
import inspect
from typing import get_args, get_origin
import os
import itertools
os.environ['OPENAI_API_KEY'] = os.environ['OPENROUTER_API_KEY']
os.environ['OPENAI_BASE_URL'] = 'https://openrouter.ai/api/v1'
model = 'google/gemini-2.5-flash-preview:thinking'


format = 'png'

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


def to_base64(image: Image.Image):
    buffered = BytesIO()
    image.save(buffered, format=format.upper())
    return base64.b64encode(buffered.getvalue()).decode()

class PrepareToolClass:

    def _prepare_tools(self):
        """all functions in the current class will be treated as a tool, unless it is a property or func name starts with '_'

        doc string, parameter type hint and arg description will be converted into tool description. 
        """
        tools = []
        type_mapping = {
            str: 'string',
            int: 'integer',
            float: 'number',
            bool: 'boolean',
            list: 'array',
            tuple: 'array',
        }
        for attr in dir(self):
            if attr.startswith('_'):
                continue
            func = getattr(self, attr)
            if not callable(func) or isinstance(func, property):
                continue

            docstring = parse(func.__doc__ or '')
            sig = inspect.signature(func)
            properties = {}
            required = []
            for name, param in sig.parameters.items():
                if name == 'self':
                    continue
                annotation = param.annotation
                if annotation == inspect.Parameter.empty:
                    continue
                origin = get_origin(annotation)
                args = get_args(annotation)
                if origin in (list, tuple):
                    param_type = 'array'
                else:
                    param_type = type_mapping[annotation]
                
                param_desc = next((p.description for p in docstring.params if p.arg_name == name))
                
                properties[name] = {
                    'type': param_type,
                    'description': param_desc
                }
                
                if param_type == 'array' and args:
                    element_type = args[0]
                    if element_type in type_mapping:
                        properties[name]['items'] = {'type': type_mapping[element_type]}
                
                if param.default == inspect.Parameter.empty:
                    required.append(name)

            if properties:  # Only add functions with parameters
                tools.append({
                    'type': 'function',
                    'function': {
                        'name': attr,
                        'description': docstring.short_description + ('\n' + docstring.long_description if docstring.long_description else ''),
                        'parameters': {
                            'type': 'object',
                            'properties': properties,
                            'required': required,
                        }
                    }
                })
        return tools


    def _translate_coord(self, coord: tuple[int, int]) -> tuple:
        return tuple(int(p * s + o) for p, s, o in zip(coord, (self.width / 1000, self.height / 1000), (self.bbox[0], self.bbox[1])))

    def _translate_bbox(self, bbox: tuple[int, int, int, int]) -> tuple:
        return tuple(itertools.chain(
            (int(p * s + o) for p, s, o in zip(bbox[:2], (self.width / 1000, self.height / 1000), (self.bbox[0], self.bbox[1]))),
            (math.ceil(p * s + o) for p, s, o in zip(bbox[2:], (self.width / 1000, self.height / 1000), (self.bbox[0], self.bbox[1])))
        ))
    
        
    @property
    def width(self):
        return self.bbox[2] - self.bbox[0]
    @property
    def height(self):
        return self.bbox[3] - self.bbox[1]
    @property
    def display(self):
        return self.image.crop(self.bbox)
    @property
    def openai_image(self):
        return [{'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': f'data:image/{format};base64,' + to_base64(self.display)}}]}]

