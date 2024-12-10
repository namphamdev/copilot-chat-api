import http.server
import threading
import requests
import json
import time
import sys

token = None

def setup():
    resp = requests.post('https://github.com/login/device/code', headers={
            'accept': 'application/json',
            'editor-version': 'Neovim/0.6.1',
            'editor-plugin-version': 'copilot.vim/1.16.0',
            'content-type': 'application/json',
            'user-agent': 'GithubCopilot/1.155.0',
            'accept-encoding': 'gzip,deflate,br'
        })


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
            }, data=f'{{"device_code":"{device_code}","grant_type":"urn:ietf:params:oauth:grant-type:device_code"}}')

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
    
def copilot(messages, model='claude-3.5-sonnet', language='python'):
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
                'X-Github-Api-Version': '2023-07-07'
            },
            json={
                'messages': messages,
                'model': model,
                'temperature': 0,
                'max_tokens': 9999999,
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

class HTTPRequestHandler(http.server.BaseHTTPRequestHandler):
   def do_POST(self):
    # Read and parse JSON request body
    content_length = int(self.headers['Content-Length'])
    request_body = self.rfile.read(content_length).decode('utf-8')
    try:
        request_data = json.loads(request_body)
        
        # Extract messages and model from request
        messages = request_data.get('messages', [])
        model = request_data.get('model', 'claude-3.5-sonnet')
        
        # Call copilot with correct parameters
        completion = copilot(messages=messages, model=model)
        
        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            'completion': completion if completion else 'No response generated'
        }
        self.wfile.write(json.dumps(response).encode())
        
    except json.JSONDecodeError:
        self.send_error(400, "Invalid JSON")
    except ValueError as e:
        self.send_error(400, str(e))


def main():
    # Every 25 minutes, get a new token
    threading.Thread(target=token_thread).start()
    # Get the port to listen on from the command line
    if len(sys.argv) < 2:
        port = 8080
    else:
        port = int(sys.argv[1])
    # Start the http server
    httpd = http.server.HTTPServer(('0.0.0.0', port), HTTPRequestHandler)
    print(f'Listening on port 0.0.0.0:{port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    main()