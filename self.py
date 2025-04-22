from PIL import Image
from openai import OpenAI
from func_metadata import func_metadata

model = 'gpt-4.1'

class Agent:
    def __init__(self, image):
        self.image = image
    
    def __call__(self, text):
        tools = [{
            'type': 'function',
            'name': 'spawn',
            'description': 'spawn a subagent',
            'parameters': {
                'type': 'object',
                'properties': {
                    'bbox': {
                        'type': 'array',
                        'items': {
                            'type': 'integer'
                        },
                        'description': 'x y x y bounding box',
                    },
                    'text': {
                        'type': 'string',
                    },
                }
            },
            'required': [],
        }]
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
                    meta = func_metadata(func)
                    args = meta.arg_model.model_validate(x.function.arguments)
                    messages.append({
                        'role': 'tool',
                        'name': x.function.name,
                        'content': meta.call_fn_with_arg_validation(func, False, args, None)
                    })
            messages.append(OpenAI.chat.completions.create(
                model=model,
                input=messages,
                tools=tools
            ).choices[0].message)


    def spawn(self, bbox: tuple[int, int, int, int], text: str):
        return Agent(self.image.crop(bbox))(text)

Agent(image=None)