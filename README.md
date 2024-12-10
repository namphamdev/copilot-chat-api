# OpenAI Compatible - Copilot Chat API

Provides a simple HTTP API to interface with GitHub Copilot, including native GitHub authentication.

Forked from [Copilot API](https://github.com/B00TK1D/copilot-api).

## Installing dependencies

`pip install -r requirements.txt`

## Run

`python3 api.py [port]`

## Usage

Send a POST request to `http://localhost:8080/api` with the following JSON body

### Request Payload

```json
{
  "model": "claude-3.5-sonnet",
  "messages": [{ "role": "user", "content": "Hello, how are you?" }],
  "temperature": 0.7
}
```

### Response

```json
{
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "message": "Hi! I'm doing well, thanks for asking. How are you today?"
    }
  ],
  "created": 1733830720,
  "id": "4e3c06e8-0783-4b3e-9dbf-06ed72211bb2",
  "object": "chat.completion"
}
```
