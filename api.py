import http.server
import threading
import requests
import json
import time
import sys
import uuid
from flask import Flask, request, jsonify, Response, stream_with_context
import logging
import os
from dotenv import load_dotenv

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

app = Flask(__name__)

token = None


def make_copilot_request(
    token, messages, model, temperature=0, max_tokens=9999999, timeout=30
):
    """
    Make a POST request to GitHub Copilot's API for chat completions.

    Args:
        token (str): Authentication token
        messages (list): List of conversation messages
        model (str): Model to use for completion
        temperature (float): Temperature for response randomness
        max_tokens (int): Maximum tokens for completion
        timeout (int): Request timeout in seconds

    Returns:
        requests.Response: The response object from the request
    """
    return requests.post(
        "https://api.individual.githubcopilot.com/chat/completions",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Editor-Version": "vscode/1.95.3",
            "Editor-Plugin-Version": "copilot-chat/0.22.4",
            "Openai-Intent": "conversation-panel",
            "X-Github-Api-Version": "2023-07-07",
        },
        json={
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "n": 1,
        },
        stream=True,
        timeout=timeout,
    )


def setup():
    resp = requests.post(
        "https://github.com/login/device/code",
        headers={
            "accept": "application/json",
            "editor-version": "Neovim/0.6.1",
            "editor-plugin-version": "copilot.vim/1.16.0",
            "content-type": "application/json",
            "user-agent": "GithubCopilot/1.155.0",
            "accept-encoding": "gzip,deflate,br",
        },
        data='{"client_id":"Iv1.b507a08c87ecfe98","scope":"read:user"}',
    )

    # Parse the response json, isolating the device_code, user_code, and verification_uri
    resp_json = resp.json()
    device_code = resp_json.get("device_code")
    user_code = resp_json.get("user_code")
    verification_uri = resp_json.get("verification_uri")

    # Print the user code and verification uri
    print(
        f"Please visit {verification_uri} and enter code {user_code} to authenticate."
    )

    while True:
        time.sleep(5)
        resp = requests.post(
            "https://github.com/login/oauth/access_token",
            headers={
                "accept": "application/json",
                "editor-version": "Neovim/0.6.1",
                "editor-plugin-version": "copilot.vim/1.16.0",
                "content-type": "application/json",
                "user-agent": "GithubCopilot/1.155.0",
                "accept-encoding": "gzip,deflate,br",
            },
            data=f'{{"client_id":"Iv1.b507a08c87ecfe98","device_code":"{device_code}","grant_type":"urn:ietf:params:oauth:grant-type:device_code"}}',
        )

        # Parse the response json, isolating the access_token
        resp_json = resp.json()
        access_token = resp_json.get("access_token")

        if access_token:
            break

    # Save the access token to a file
    with open("data/.copilot_token", "w") as f:
        f.write(access_token)

    print(f"Access token: {access_token}")
    print("Authentication success!")


def get_local_token():
    if os.getenv("COPILOT_TOKEN"):
        access_token = os.getenv("COPILOT_TOKEN")
        return access_token
    # Check if the .copilot_token file exists
    with open("data/.copilot_token", "r") as f:
        access_token = f.read()
        return access_token


def get_token():
    global token
    access_token = get_local_token()
    if not access_token:
        setup()
        access_token = get_local_token()

    # Get a session with the access token
    resp = requests.get(
        "https://api.github.com/copilot_internal/v2/token",
        headers={
            "authorization": f"token {access_token}",
            "editor-version": "Neovim/0.6.1",
            "editor-plugin-version": "copilot.vim/1.16.0",
            "user-agent": "GithubCopilot/1.155.0",
        },
    )

    # Parse the response json, isolating the token
    resp_json = resp.json()
    token = resp_json.get("token")


def token_thread():
    global token
    while True:
        get_token()
        time.sleep(25 * 60)


def convert_messages_format(input_messages):
    if isinstance(input_messages, list):
        converted_messages = []
        for message in input_messages:
            if isinstance(message, dict) and "role" in message and "content" in message:
                role = message["role"]
                content = message["content"]
                # Check if content is a list
                if isinstance(content, list):
                    combined_text = "".join(
                        item["text"]
                        for item in content
                        if isinstance(item, dict) and "text" in item
                    )
                elif isinstance(content, str):
                    combined_text = content
                else:
                    combined_text = str(
                        content
                    )  # Convert to string if not a list or string
                converted_messages.append({"role": role, "content": combined_text})
        return converted_messages
    return input_messages


def process_messages(
    model="claude-3.5-sonnet", messages=[], temperature=0, max_tokens=9999999
):
    global token
    if token is None or is_token_invalid(token):
        get_token()

    try:
        resp = make_copilot_request(token, messages, model, temperature, max_tokens)
        resp.raise_for_status()

        result = ""
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    json_data = json.loads(line[6:])
                    if json_data.get("choices"):
                        completion = (
                            json_data["choices"][0].get("delta", {}).get("content", "")
                        )
                        if completion:
                            result += completion
            except (json.JSONDecodeError, KeyError) as e:
                continue
        return result

    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
        return None


def copilot(model, prompt, language="python"):
    global token
    # If the token is None, get a new one
    if token is None or is_token_invalid(token):
        get_token()

    try:
        resp = requests.post(
            "https://copilot-proxy.githubusercontent.com/v1/engines/copilot-codex/completions",
            headers={"authorization": f"Bearer {token}"},
            json={
                "prompt": prompt,
                "model": model,
                "suffix": "",
                "max_tokens": 1000,
                "temperature": 0,
                "top_p": 1,
                "n": 1,
                "stop": ["\n"],
                "nwo": "github/copilot.vim",
                "stream": True,
                "extra": {"language": language},
            },
        )
    except requests.exceptions.ConnectionError:
        return ""

    result = ""

    # Parse the response text, splitting it by newlines
    resp_text = resp.text.split("\n")
    for line in resp_text:
        # If the line contains a completion, print it
        if line.startswith("data: {"):
            # Parse the completion from the line as json
            json_completion = json.loads(line[6:])
            completion = json_completion.get("choices")[0].get("text")
            if completion:
                result += completion
            else:
                result += "\n"

    return result


# Check if the token is invalid through the exp field
def is_token_invalid(token):
    if token is None or "exp" not in token or extract_exp_value(token) <= time.time():
        return True
    return False


def extract_exp_value(token):
    pairs = token.split(";")
    for pair in pairs:
        key, value = pair.split("=")
        if key.strip() == "exp":
            return int(value.strip())
    return None


def generate_response(model, messages, temperature, max_tokens):
    return process_messages(
        model=model, messages=messages, temperature=temperature, max_tokens=max_tokens
    )


# OpenAI compatible API endpoint
@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    data = request.json
    model = data.get("model")
    messages = data.get("messages")
    converted_messages = convert_messages_format(messages)
    temperature = data.get("temperature", 1.0)
    max_tokens = data.get("max_tokens", 9999999)
    stream = data.get("stream", False)

    # Check for required fields
    if model is None or messages is None:
        logging.error("Missing required fields: model or messages")
        return jsonify({"error": "Missing required fields"}), 400

    try:
        if stream == False:
            done = False

            def generate():
                nonlocal done
                response_content = generate_response(
                    model, messages, temperature, max_tokens
                )
                if response_content is None:
                    yield json.dumps({"error": "API request failed"}).encode("utf-8")
                    done = True
                else:
                    yield json.dumps(
                        {
                            "id": str(uuid.uuid4()),
                            "object": "chat.completion",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [
                                {
                                    "message": {
                                        "role": "assistant",
                                        "content": response_content,
                                    },
                                    "logprobs": None,
                                    "finish_reason": "stop",
                                    "index": 0,
                                }
                            ],
                        }
                    ).encode("utf-8")
                    done = True

            return app.response_class(generate(), mimetype="application/json")
        else:
            resp = make_copilot_request(
                token, converted_messages, model, temperature, max_tokens
            )
            resp.raise_for_status()
            return Response(
                resp.iter_content(chunk_size=1024), content_type="text/event-stream"
            )

    except Exception as e:
        logging.error(f"Error in chat_completions: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


@app.route("/v1/code/completions", methods=["POST"])
def code_completions():
    data = request.json
    prompt = data.get("prompt")
    model = data.get("model")
    language = data.get("language", "python")

    completion = copilot(model, prompt, language)
    return app.response_class(completion, mimetype="text/plain")


def main():
    # Every 25 minutes, get a new token
    threading.Thread(target=token_thread).start()
    # Get the port to listen on from the command line
    if len(sys.argv) < 2:
        port = 8080
    else:
        port = int(sys.argv[1])
    # Start the http server
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
