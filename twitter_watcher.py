import json
import logging
import os
import random
import time
from typing import List, Union

import requests

from graphql_api import GraphqlAPI
from utils import find_one


def _get_auth_headers(headers, cookies) -> dict:

    authed_headers = headers | {
        'cookie': '; '.join(f'{k}={v}' for k, v in cookies.items()),
        'referer': 'https://twitter.com/',
        'x-csrf-token': cookies.get('ct0', ''),
        'x-guest-token': cookies.get('guest_token', ''),
        'x-twitter-auth-type': 'OAuth2Session' if cookies.get('auth_token') else '',
        'x-twitter-active-user': 'yes',
        'x-twitter-client-language': 'en',
    }
    return dict(sorted({k.lower(): v for k, v in authed_headers.items()}.items()))


def _build_params(params: dict) -> dict:
    return {k: json.dumps(v) for k, v in params.items()}


class TwitterWatcher:

    def __init__(self, auth_username_list: List[str], cookies_dir: str):
        assert auth_username_list
        self.token_number = len(auth_username_list)
        self.auth_cookie_list = []
        for auth_username in auth_username_list:
            auth_cookie_file = os.path.join(cookies_dir, '{}.json'.format(auth_username))
            with open(auth_cookie_file, 'r') as f:
                self.auth_cookie_list.append(json.load(f))
                self.auth_cookie_list[-1]['username'] = auth_username
        self.current_token_index = random.randrange(self.token_number)
        self.logger = logging.getLogger('api')

    def query(self, api_name: str, params: dict) -> Union[dict, list, None]:
        url, method, headers, features = GraphqlAPI.get_api_data(api_name)
        params = _build_params({"variables": params, "features": features})
        for _ in range(self.token_number):
            self.current_token_index = (self.current_token_index + 1) % self.token_number
            auth_headers = _get_auth_headers(headers, self.auth_cookie_list[self.current_token_index])
            try:
                response = requests.request(method=method, url=url, headers=auth_headers, params=params, timeout=300)
            except requests.exceptions.ConnectionError as e:
                self.logger.error('{} request error: {}, try next token.'.format(url, e))
                continue
            if response.status_code in [200, 404, 403]:
                # 404 NOT_FOUND
                # 403 CURRENT_USER_SUSPENDED
                if not response.text:
                    self.logger.error('{} response empty {}, try next token.'.format(url, response.status_code))
                    continue
                json_response = response.json()
                if 'errors' in json_response:
                    self.logger.error('{} request error: {} {}, try next token.'.format(
                        url, response.status_code, json_response['errors']))
                    continue
                return json_response
            if response.status_code != 429:
                # 429 TWEET_RATE_LIMIT_EXCEEDED
                self.logger.error('{} request returned an error: {} {}, try next token.'.format(
                    url, response.status_code, response.text))
                continue
        self.logger.error('All tokens are unavailable, query fails: {}\n{}\n{}'.format(
            url, json.dumps(auth_headers, indent=2), json.dumps(params, indent=2)))
        return None

    def get_user_by_username(self, username: str, params: dict = {}) -> dict:
        api_name = 'UserByScreenName'
        params['screen_name'] = username
        json_response = self.query(api_name, params)
        while json_response is None:
            time.sleep(60)
            json_response = self.query(api_name, params)
        return json_response

    def get_user_by_id(self, id: int, params: dict = {}) -> dict:
        api_name = 'UserByRestId'
        params['userId'] = id
        json_response = self.query(api_name, params)
        while json_response is None:
            time.sleep(60)
            json_response = self.query(api_name, params)
        return json_response

    def get_id_by_username(self, username: str):
        json_response = self.get_user_by_username(username, {})
        return find_one(json_response, 'rest_id')

    def check_tokens(self, test_username: str = 'X', output_response: bool = False):
        result = dict()
        for auth_cookie in self.auth_cookie_list:
            try:
                url, method, headers, features = GraphqlAPI.get_api_data('UserByScreenName')
                params = _build_params({"variables": {'screen_name': test_username}, "features": features})
                auth_headers = _get_auth_headers(headers, auth_cookie)
                response = requests.request(method=method, url=url, headers=auth_headers, params=params, timeout=300)
            except requests.exceptions.ConnectionError as e:
                result[auth_cookie['username']] = False
                print(e)
                continue
            result[auth_cookie['username']] = (response.status_code == 200)
            if output_response:
                print(json.dumps(response.json(), indent=2))
        return result
