import http.server
import threading
import requests
import json
import time
import sys
import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)

token = None

def setup():
    resp = requests.post('https://github.com/login/device/code', headers={
            'accept': 'application/json',
            'editor-version': 'Neovim/0.6.1',
            'editor-plugin-version': 'copilot.vim/1.16.0',
            'content-type': 'application/json',
            'user-agent': 'GithubCopilot/1.155.0',
            'accept-encoding': 'gzip,deflate,br'
        }, data='{"client_id":"Iv1.b507a08c87ecfe98","scope":"read:user"}')


    # Parse the response json, isolating the device_code, user_code, and verification_uri
    resp_json = resp.json()
    device_code = resp_json.get('device_code')
    user_code = resp_json.get('user_code')
    verification_uri = resp_json.get('verification_uri')

    # Print the user code and verification uri
    print(f'Please visit {verification_uri} and enter code {user_code} to authenticate.')


    while True:
        time.sleep(5)
        resp = requests.post('https://github.com/login/oauth/access_token', headers={
            'accept': 'application/json',
            'editor-version': 'Neovim/0.6.1',
            'editor-plugin-version': 'copilot.vim/1.16.0',
            'content-type': 'application/json',
            'user-agent': 'GithubCopilot/1.155.0',
            'accept-encoding': 'gzip,deflate,br'
            }, data=f'{{"client_id":"Iv1.b507a08c87ecfe98","device_code":"{device_code}","grant_type":"urn:ietf:params:oauth:grant-type:device_code"}}')

        # Parse the response json, isolating the access_token
        resp_json = resp.json()
        access_token = resp_json.get('access_token')

        if access_token:
            break

    # Save the access token to a file
    with open('.copilot_token', 'w') as f:
        f.write(access_token)

    print('Authentication success!')

def get_token():
    global token
        # Check if the .copilot_token file exists
    while True:
        try:
            with open('.copilot_token', 'r') as f:
                access_token = f.read()
                break
        except FileNotFoundError:
            setup()
    # Get a session with the access token
    resp = requests.get('https://api.github.com/copilot_internal/v2/token', headers={
        'authorization': f'token {access_token}',
        'editor-version': 'Neovim/0.6.1',
        'editor-plugin-version': 'copilot.vim/1.16.0',
        'user-agent': 'GithubCopilot/1.155.0'
    })

    # Parse the response json, isolating the token
    resp_json = resp.json()
    token = resp_json.get('token')


def token_thread():
    global token
    while True:
        get_token()
        time.sleep(25 * 60)
    
def copilot(model='claude-3.5-sonnet', messages=[], temperature=0, max_tokens=9999999):
    global token
    if token is None or is_token_invalid(token):
        get_token()

    try:
        resp = requests.post(
            'https://api.individual.githubcopilot.com/chat/completions',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Editor-Version': 'vscode/1.95.3',
                'Editor-Plugin-Version': 'copilot-chat/0.22.4',
                'Openai-Intent': 'conversation-panel',
                'X-Github-Api-Version': '2023-07-07'},
            json={
                'messages': messages,
                'model': model,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'stream': True,
                'n': 1
            },
            stream=True,
            timeout=30
        )
        resp.raise_for_status()

        result = ''
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    json_data = json.loads(line[6:])
                    if json_data.get('choices'):
                        completion = json_data['choices'][0].get('delta', {}).get('content', '')
                        if completion:
                            result += completion
            except (json.JSONDecodeError, KeyError) as e:
                continue
        return result

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {str(e)}")
        return None

# Check if the token is invalid through the exp field
def is_token_invalid(token):
    if token is None or 'exp' not in token or extract_exp_value(token) <= time.time():
        return True
    return False

def extract_exp_value(token):
    pairs = token.split(';')
    for pair in pairs:
        key, value = pair.split('=')
        if key.strip() == 'exp':
            return int(value.strip())
    return None

def generate_response(model, messages, temperature, max_tokens):
    return copilot(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)

# OpenAI compatible API endpoint
@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.json
    model = data.get('model')
    messages = data.get('messages')
    temperature = data.get('temperature', 1.0)
    max_tokens = data.get('max_tokens', 1000)

    done = False
    def generate():
        nonlocal done
        response_content = generate_response(model, messages, temperature, max_tokens)
        if response_content is None:
            yield json.dumps({'error': 'API request failed'}).encode('utf-8')
            done = True
        else:
            yield json.dumps({
                'id': str(uuid.uuid4()),
                'object': 'chat.completion',
                'created': int(time.time()),
                'model': model,
                'choices': [
                    {
                        'message': {
                            'role': 'assistant',
                            'content': response_content
                        },
                        'logprobs': None,
                        'finish_reason': 'stop',
                        'index': 0
                    }
                ]
            }).encode('utf-8')
            done = True

    return app.response_class(generate(), mimetype='application/json')

def main():
    # Every 25 minutes, get a new token
    threading.Thread(target=token_thread).start()
    # Get the port to listen on from the command line
    if len(sys.argv) < 2:
        port = 8080
    else:
        port = int(sys.argv[1])
    # Start the http server
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()