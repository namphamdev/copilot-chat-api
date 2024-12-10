# Copilot Chat API (OpenAI Compatible)

Provides a simple HTTP API to interface with GitHub Copilot, including native GitHub authentication.

Forked from [Copilot API](https://github.com/B00TK1D/copilot-api) to include chat endpoint.

## Supports Cline

Set your API provider to OpenAI Compatible and the Base URL to this server.

Your API key can be anything. Change your model to any model supported by Copilot.

![cline](/images/cline.png)

## Dependencies

```
pip install -r requirements.txt
```

## Run

```
python3 api.py [port]
```

## Usage

Send a POST request to `http://localhost:8080/v1/chat/completions` with the following JSON body

### Payload

```json
{
  "model": "claude-3.5-sonnet",
  "messages": [{ "role": "user", "content": "Hello, how are you?" }],
  "temperature": 0.7, // default: 1.0
  "max_tokens": 1000 // default: 9999999
  "stream": true, // default: false
}
```

### Response

#### Stream

![Streamed Responses](/images/stream.png)

#### Non-Stream

![Non-Streamed Responses](/images/no-stream.png)
