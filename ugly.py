import functools
import numpy as np
from loguru import logger
import json
from PIL import Image
import re
from typing import Dict, Any

def log_method_call(func):
    """Decorator to log method calls, arguments, and return values."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Calling method {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"Method {func.__name__} returned: {result}")
            return result
        except Exception as e:
            logger.error(f"Method {func.__name__} raised an exception: {e}")
            raise
    return wrapper


def compute_probabilities(scores, alpha=0.2, lambda_=0.3):
    scores = np.array(scores, dtype=np.float64)
    n = len(scores)
    uniform_prob = np.full(n, 1.0 / n, dtype=np.float64)
    max_score = np.max(scores)
    shifted_scores = scores - max_score
    exp_weights = np.exp(alpha * shifted_scores)
    sum_exp_weights = np.sum(exp_weights)
    if sum_exp_weights == 0:
        raise ValueError("Sum of exponential weights is 0, cannot normalize.")
    score_prob = exp_weights / sum_exp_weights
    mixed_prob = lambda_ * uniform_prob + (1 - lambda_) * score_prob
    total_prob = np.sum(mixed_prob)
    if not np.isclose(total_prob, 1.0):
        mixed_prob = mixed_prob / total_prob
    return mixed_prob

from gkx import db_session
@db_session
def format_experience(graph):
    failures = [x for x in graph.children if x.score <= graph.score]
    successes = [x for x in graph.children if x.score > graph.score]
    experience = f"Original Score: {graph.score}\n"
    experience += "These are some conclusions drawn from experience:\n\n"
    for failure in failures:
        experience += f"-Absolutely prohibit {failure.modification} (Score: {failure.score})\n"
    for success in successes:
        experience += f"-Absolutely prohibit {success.modification} \n"
    experience += "\n\nNote: Take into account past failures and avoid repeating the same mistakes, as these failures indicate that these approaches are ineffective. You must fundamentally change your way of thinking, rather than simply using more advanced Python syntax like for, if, else, etc., or modifying the prompt."
    return experience


def format_log(obj):
    if isinstance(obj, dict):
        if "choices" in obj and isinstance(obj["choices"], list) and len(obj["choices"]) > 0 and isinstance(obj["choices"][0], dict):
            choice = obj["choices"][0]
            if "text" in choice:
                return choice["text"]
            elif "message" in choice and isinstance(choice["message"], dict) and "content" in choice["message"]:
                return choice["message"]["content"]
            else:
                return "Unknown response format"
        else:
            return {k: format_log(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [format_log(elem) for elem in obj]
    else:
        return obj



async def xml_extract(self, content: str, pydantic_model) -> Dict[str, Any]:
    field_names = pydantic_model.get_field_names()
    field_types = pydantic_model.get_field_types()
    extracted_data = {}
    for field_name in field_names:
        pattern = rf"<{field_name}>((?:(?!<{field_name}>).)*?)</{field_name}>"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            raw_value = match.group(1).strip()
            field_type = field_types.get(field_name)

            if field_type == str:
                pattern = r"```python(.*?)```"
                match = re.search(pattern, raw_value, re.DOTALL)
                if match:
                    raw_value = '\n'.join(match.groups())
                extracted_data[field_name] = raw_value
            elif field_type == int:
                try:
                    extracted_data[field_name] = int(raw_value)
                except ValueError:
                    extracted_data[field_name] = 0
            elif field_type == bool:
                extracted_data[field_name] = raw_value.lower() in ("true", "yes", "1", "on", "True")
            elif field_type == list:
                try:
                    extracted_data[field_name] = eval(raw_value)
                    if not isinstance(extracted_data[field_name], list):
                        raise ValueError
                except:
                    extracted_data[field_name] = []
            elif field_type == dict:
                try:
                    extracted_data[field_name] = eval(raw_value)
                    if not isinstance(extracted_data[field_name], dict):
                        raise ValueError
                except:
                    extracted_data[field_name] = {}
            else:
                extracted_data[field_name] = raw_value
        else:
            pattern = rf"^(.*?)</{field_name}>"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                raw_value = match.group(1).strip()
                extracted_data[field_name] = raw_value
            else:
                print(content)
                print(field_names)
                print(field_types)

    return extracted_data