import functools
import numpy as np
from loguru import logger
import json
from PIL import Image

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


