# Copilot Chat API

Provides a simple HTTP API to interface with GitHub Copilot, including native GitHub authentication.

Forked from [Copilot API](https://github.com/B00TK1D/copilot-api).

## Installing dependencies

`pip install -r requirements.txt`

## Run

`python3 api.py [port]`

## Usage

Send a POST request to `http://localhost:8080/api` with the following JSON body:

### Request payload

```json
{
  "messages": [
    {
      "role": "user",
      "content": "what's up?"
    }
  ],
  "model": "claude-3.5-sonnet"
}
```

### Response

```json
{
  "completion": "Hey! I'm doing well, just here to chat and help out. How are you?"
}
```
