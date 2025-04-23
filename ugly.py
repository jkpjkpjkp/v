import functools
import numpy as np
from loguru import logger
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

