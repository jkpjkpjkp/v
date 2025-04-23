import json
from util import client, PrepareToolClass


class Agent(PrepareToolClass):
    def __init__(self, image, bbox=None):
        print(bbox)
        self.image = image
        self.bbox = bbox or (0, 0, image.width, image.height)
    
    def __call__(self, text):
        tools = self._prepare_tools()  # defined in PrepareToolClass, reads all method in the current class, parse their type hints and docstringin into openai tool format. 
        messages = [{'role': 'user', 'content': text}]
        messages.append(client.chat.completions.create(
            messages=messages + self.openai_image,
            tools=tools,
        ).choices[0].message)
        if messages[-1].tool_calls:
            for x in messages[-1].tool_calls:
                if x.type == 'function':
                    func = getattr(self, x.function.name)
                    if getattr(json.loads(x.function.arguments), 'bbox', None) == [0, 0, 1000, 1000]:
                        return client.chat.completions.create(
                            messages=[{'role': 'user', 'content': text}] + self.openai_image,
                        ).choices[0].message.content
                    messages.append({
                        'role': 'tool',
                        'name': x.function.name,
                        'content': func(**json.loads(x.function.arguments)),
                    })
            messages.append(client.chat.completions.create(
                messages=messages + self.openai_image,  # defined in PrepareToolClass, current image crop as openai usermessage
            ).choices[0].message)
        
        return messages[-1].content
    

    def spawn(self, bbox: tuple[int, int, int, int], text: str) -> str:
        """Spawn a subagent. It will be given a crop of the image and a task to finish. 

        Use this tool liberally, unless you are absolutely very sure.
        this tool can be used to 
            1. zoom-in to question-related area (1 tool call)
            2. cut the image into pieces and examine each (many tool calls)
        
        DO NOT CALL THIS WITH [0, 0, 1000, 1000]. in which case directly answer. 

        Args:
            bbox: x y x y bounding box, coordinates in [0,1000]
            text: instruction for the subagent
        """
        if bbox == [0, 0, 1000, 1000]:
            raise ValueError('bbox is [0, 0, 1000, 1000]')
        bbox = self._translate_bbox(bbox)  # defined in PrepareToolClass, converts from normalized (0 to 1000) to PIL pixel coordinates
        return type(self)(self.image, bbox)(text)


from data.data import get_task_by_id
if __name__ == '__main__':
    task = get_task_by_id('37_3')
    agent = Agent(task['image'])
    print(task['image'].width, task['image'].height)
    print(agent(task['question']))
