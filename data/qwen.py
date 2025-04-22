pyramid = {
    'qwen-vl-plus-latest': 0.75,
    'qwen-vl-max-latest': 1.5,
    'qwen-vl-ocr-latest': 5,
}

usd2rmb = 7.30

gemini = {
    'gemini-2.0-flash': 0.4 * usd2rmb,
    'gemini-2.5-flash': 0.6 * usd2rmb,
    'gemini-2.5-flash-thinking': 3.5 * usd2rmb,
    'google/gemini-2.5-flash-preview:thinking': 3.5 * usd2rmb,
    'gemini-2.5-pro-exp': 10 * usd2rmb,
}

import os
from openai import OpenAI

try:
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': '你是谁？'}
            ]
    )
    print(completion.choices[0].message.content)
except Exception as e:
    print(f"错误信息：{e}")
    print("请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code")