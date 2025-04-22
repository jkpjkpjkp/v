import base64
import logging
import os
import re
import threading
import tenacity
from fastapi.responses import Response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for budgeting
client_budgets = {}
budget_lock = threading.Lock()
a = 1.0  # Cost per input token
b = 1.0  # Cost per output token
initial_budget = 10000.0

# Assume providers and IMAGE_FOLDER are defined elsewhere
providers = []  # Should be populated with provider dicts
IMAGE_FOLDER = "images"  # Adjust as needed

for provider in providers:
    provider['ema'] = 1.0
    provider['lock'] = threading.Lock()

def choose_provider():
    return max(providers, key=lambda p: p['ema'])

async def update_ema(provider, success):
    alpha = 0.1
    with provider['lock']:
        current_ema = provider['ema']
        new_ema = alpha * success + (1 - alpha) * current_ema
        provider['ema'] = new_ema
        logger.debug(f'Updated EMA for {provider["base_url"]}: {new_ema}')

def save_image_if_not_exists(image_id, base64_str, extension):
    filename = os.path.join(IMAGE_FOLDER, f'{image_id}{extension}')
    base64_str = re.sub(r'^data:image/.*?;base64,', '', base64_str)
    if os.path.exists(filename):
        return
    try:
        image_data = base64.b64decode(base64_str)
        with open(filename, 'wb') as f:
            f.write(image_data)
    except Exception as e:
        logger.error(f'Failed to save image {image_id}: {str(e)}')

@tenacity.retry(stop=tenacity.stop_after_attempt(10), wait=tenacity.wait_exponential(multiplier=1.2, min=4, max=150))
async def forward_request(request):
    # Extract client API key from Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return Response(content='Missing or invalid Authorization header', status_code=401)
    client_api_key = auth_header.split(' ')[1]
    
    provider = choose_provider()
    logger.info(f'Sending request to {provider["base_url"]}')
    
