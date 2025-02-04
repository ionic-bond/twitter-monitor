# Reference: https://github.com/trevorhobenshield/twitter-api-client/blob/main/twitter/login.py
import sys

from httpx import Client

from utils import find_all
from graphql_api import GraphqlAPI


def update_token(client: Client, key: str, url: str, **kwargs) -> Client:
    caller_name = sys._getframe(1).f_code.co_name
    try:
        headers = {
            'x-guest-token': client.cookies.get('guest_token', ''),
            'x-csrf-token': client.cookies.get('ct0', ''),
            'x-twitter-auth-type': 'OAuth2Client' if client.cookies.get('auth_token') else '',
        }
        client.headers.update(headers)
        r = client.post(url, **kwargs)
        if r.status_code != 200:
            print(f'[error] {r.status_code} {r.text}')
        info = r.json()

        for task in info.get('subtasks', []):
            if task.get('enter_text', {}).get('keyboard_type') == 'email':
                print(f"[warning] {' '.join(find_all(task, 'text'))}")
                client.cookies.set('confirm_email', 'true')  # signal that email challenge must be solved

            if task.get('subtask_id') == 'LoginAcid':
                if task['enter_text']['hint_text'].casefold() == 'confirmation code':
                    print(f"[warning] email confirmation code challenge.")
                    client.cookies.set('confirmation_code', 'true')

        client.cookies.set(key, info[key])

    except KeyError as e:
        client.cookies.set('flow_errors', 'true')  # signal that an error occurred somewhere in the flow
        print(f'[error] failed to update token at {caller_name}\n{e}')
    return client


def init_guest_token(client: Client) -> Client:
    return update_token(client, 'guest_token', 'https://api.x.com/1.1/guest/activate.json')


def flow_start(client: Client) -> Client:
    return update_token(client,
                        'flow_token',
                        'https://api.x.com/1.1/onboarding/task.json',
                        params={'flow_name': 'login'},
                        json={
                            "input_flow_data": {
                                "flow_context": {
                                    "debug_overrides": {},
                                    "start_location": {
                                        "location": "splash_screen"
                                    }
                                }
                            },
                            "subtask_versions": {}
                        })


def flow_instrumentation(client: Client) -> Client:
    return update_token(client,
                        'flow_token',
                        'https://api.x.com/1.1/onboarding/task.json',
                        json={
                            "flow_token":
                                client.cookies.get('flow_token'),
                            "subtask_inputs": [{
                                "subtask_id": "LoginJsInstrumentationSubtask",
                                "js_instrumentation": {
                                    "response": "{}",
                                    "link": "next_link"
                                }
                            }],
                        })


def flow_username(client: Client) -> Client:
    return update_token(client,
                        'flow_token',
                        'https://api.x.com/1.1/onboarding/task.json',
                        json={
                            "flow_token":
                                client.cookies.get('flow_token'),
                            "subtask_inputs": [{
                                "subtask_id": "LoginEnterUserIdentifierSSO",
                                "settings_list": {
                                    "setting_responses": [{
                                        "key": "user_identifier",
                                        "response_data": {
                                            "text_data": {
                                                "result": client.cookies.get('username')
                                            }
                                        }
                                    }],
                                    "link": "next_link"
                                }
                            }],
                        })


def flow_password(client: Client) -> Client:
    return update_token(client,
                        'flow_token',
                        'https://api.x.com/1.1/onboarding/task.json',
                        json={
                            "flow_token":
                                client.cookies.get('flow_token'),
                            "subtask_inputs": [{
                                "subtask_id": "LoginEnterPassword",
                                "enter_password": {
                                    "password": client.cookies.get('password'),
                                    "link": "next_link"
                                }
                            }]
                        })


def flow_finish(client: Client) -> Client:
    return update_token(client,
                        'flow_token',
                        'https://api.x.com/1.1/onboarding/task.json',
                        json={
                            "flow_token": client.cookies.get('flow_token'),
                            "subtask_inputs": [],
                        })


def confirm_email(client: Client) -> Client:
    return update_token(client,
                        'flow_token',
                        'https://api.x.com/1.1/onboarding/task.json',
                        json={
                            "flow_token":
                                client.cookies.get('flow_token'),
                            "subtask_inputs": [{
                                "subtask_id": "LoginAcid",
                                "enter_text": {
                                    "text": client.cookies.get('email'),
                                    "link": "next_link"
                                }
                            }]
                        })


def solve_confirmation_challenge(client: Client, **kwargs) -> Client:
    if fn := kwargs.get('proton'):
        confirmation_code = fn()
        return update_token(client,
                            'flow_token',
                            'https://api.x.com/1.1/onboarding/task.json',
                            json={
                                "flow_token":
                                    client.cookies.get('flow_token'),
                                'subtask_inputs': [{
                                    'subtask_id': 'LoginAcid',
                                    'enter_text': {
                                        'text': confirmation_code,
                                        'link': 'next_link',
                                    },
                                },],
                            })


def execute_login_flow(client: Client, **kwargs) -> Client | None:
    client = init_guest_token(client)
    for fn in [flow_start, flow_instrumentation, flow_username, flow_password, flow_finish]:
        client = fn(client)

    # solve email challenge
    if client.cookies.get('confirm_email') == 'true':
        client = confirm_email(client)

    # solve confirmation challenge (Proton Mail only)
    if client.cookies.get('confirmation_code') == 'true':
        if not kwargs.get('proton'):
            print(f'[warning] Please check your email for a confirmation code'
                  f' and log in again using the web app. If you wish to automatically solve'
                  f' email confirmation challenges, add a Proton Mail account in your account settings')
            return
        client = solve_confirmation_challenge(client, **kwargs)
    return client


def login(username: str, password: str, **kwargs) -> Client:
    client = Client(cookies={
        "username": username,
        "password": password,
        "guest_token": None,
        "flow_token": None,
    },
                    headers=GraphqlAPI.headers | {
                        'content-type': 'application/json',
                        'x-twitter-active-user': 'yes',
                        'x-twitter-client-language': 'en',
                        'User-Agent': 'Mozilla/5.0 (platform; rv:geckoversion) Gecko/geckotrail Firefox/firefoxversion',
                    },
                    follow_redirects=True)
    client = execute_login_flow(client, **kwargs)
    if not client or client.cookies.get('flow_errors') == 'true':
        raise Exception(f'[error] {username} login failed')
    return client
