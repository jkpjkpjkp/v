import base64
from io import BytesIO
from PIL import Image, ImageDraw
import openai
from docstring_parser import parse
import math
import inspect
from typing import get_args, get_origin

model = 'gemini-2.0-flash'
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
                        'description': docstring.short_description or '',
                        'parameters': {
                            'type': 'object',
                            'properties': properties,
                            'required': required,
                        }
                    }
                })
        messages = [{'role': 'user', 'content': text}]
        messages.append(openai.chat.completions.create(
            model=model,
            messages=messages + [{'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': f'data:image/{format};base64,' + to_base64(self.display)}}]}],
            tools=tools,
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
            messages.append(openai.chat.completions.create(
                model=model,
                messages=messages + [{'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': f'data:image/{format};base64,' + to_base64(self.display)}}]}],
                tools=tools,
            ).choices[0].message)
        
        return messages[-1].content
    
    def _translate_coord(self, coord: tuple[int, int]) -> Image.Image:
        return tuple(p * s + o for p, s, o in zip(coord, (self.width, self.height) / 1000, (self.bbox[0], self.bbox[1])))

    def _translate_bbox(self, bbox: tuple[int, int, int, int]) -> Image.Image:
        return (*self._translate_coord(bbox[:2]), *self._translate_coord(bbox[2:]))

    def spawn(self, bbox: tuple[int, int, int, int], text: str) -> str:
        """Spawn a subagent. It will be given a crop of the image and a task to finish.
        
        Args:
            bbox: x y x y bounding box, coordinates in [0,1000]
            text: instruction for the subagent
        """
        return Agent(self.image, self._translate_bbox(bbox))(text)

    def _draw(self, points: list[tuple[int, int]], color: str = 'red', width: int = 1):
        """Draw line segments on the image.
        
        Args:
            points: list of x y coordinates, x,y in [0,1000]
            color: color of the line
            width: width of the line
        """
        points = [self._translate_coord(p) for p in points]
        width = math.ceil(width * self.width / self.image.width)
        ImageDraw.Draw(self.image).line(points, fill=color, width=width)
    
    def _mark(self, prompt):
        pass

from data.data import get_task_data
if __name__ == '__main__':
    task = get_task_data('37_3')
    agent = Agent(task['image'])
    print(agent(task['question']))
