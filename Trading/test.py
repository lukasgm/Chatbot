import requests
import json

url = 'https://api.openai.com/v1/chat/completions'

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer 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",  # replace with your key
}

data = {
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Say this is a test!"}],
    "temperature": 0.7
}

response = requests.post(url, headers=headers, data=json.dumps(data))

print(response.json())
