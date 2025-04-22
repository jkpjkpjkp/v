import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI
from docstring_parser import parse
import math

model = 'gpt-4.1'
format = 'png'

def to_base64(image: Image.Image):
    buffered = BytesIO()
    image.save(buffered, format='PNG')
    return base64.b64encode(buffered.getvalue()).decode()

class Agent:
    def __init__(self, image, bbox=None):
        self.image = image
        self.bbox = bbox or (0, 0, image.width, image.height)
    
    @property
    def width(self):
        return self.bbox[2] - self.bbox[0]
    @property
    def height(self):
        return self.bbox[3] - self.bbox[1]
    @property
    def display(self):
        return self.image.crop(self.bbox)

    def __call__(self, text):
        tools = []
        for attr in dir(self):
            if attr.startswith('_'):
                continue
            func = getattr(self, attr)
            if not callable(func) or isinstance(func, property):
                continue

            docstring = parse(func.__doc__)
            properties = {}
            required = []
            for param in docstring.params:
                properties[param.arg_name] = {
                    'type': {
                        'str': 'string',
                        'int': 'integer',
                        'bool': 'boolean',
                        'list': 'array',
                        'tuple': 'array',
                    }[param.type_name.lower()],
                    'description': param.description
                }
                if param.default is None:
                    required.append(param.arg_name)

            tools.append({
                'type': 'function',
                'function': {
                    'name': attr,
                    'description': docstring.short_description,
                    'parameters': {
                        'type': 'object',
                        'properties': properties,
                        'required': required,
                    }
                }
            })

        messages = [{'role': 'user', 'content': text}]
        messages.append(OpenAI.chat.completions.create(
            model=model,
            input=messages,
            tools=tools
        ).choices[0].message)
        while messages[-1].tool_calls:
            for x in messages[-1].tool_calls:
                if x.type == 'function':
                    func = getattr(self, x.function.name)
                    messages.append({
                        'role': 'tool',
                        'name': x.function.name,
                        'content': func(**x.function.arguments),
                    })
            messages.append(OpenAI.chat.completions.create(
                model=model,
                input=messages + [{'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': f'data:image/{format};base64,' + to_base64(self.display)}}]}],
                tools=tools
            ).choices[0].message)

    def _translate_bbox(self, bbox: tuple[int, int, int, int]) -> Image.Image:
        scale = (self.width/1000, self.height/1000, self.width/1000, self.height/1000)
        offset = (self.bbox[0], self.bbox[1], self.bbox[0], self.bbox[1])
        return tuple(p * s + o for p, s, o in zip(bbox, scale, offset))

    def spawn(self, bbox: tuple[int, int, int, int], text: str) -> str:
        """Spawn a subagent for a specific region of the image.
        
        Args:
            bbox: x y x y bounding box coordinates, x,y in [0,1000]
            text: instruction for the subagent
        """
        return Agent(self.image, self._translate_bbox(bbox))(text)

