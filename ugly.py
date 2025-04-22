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
