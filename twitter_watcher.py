import json
import logging
import os
import random
import time
from typing import List, Union

import requests

from utils import load_auth_handler


def _get_headers(bearer_token: str):
    return {'Authorization': 'Bearer {}'.format(bearer_token)}


class TwitterWatcher:

    def __init__(self, bearer_token_list: List[str], auth_username_list: List[str], cookies_dir: str):
        assert bearer_token_list or auth_username_list
        self.token_number = len(bearer_token_list) + len(auth_username_list)
        self.bearer_token_list = bearer_token_list
        self.auth_handler_list = []
        for auth_username in auth_username_list:
            auth_cookie = os.path.join(cookies_dir, '{}.json'.format(auth_username))
            self.auth_handler_list.append(load_auth_handler(auth_cookie))
            self.auth_handler_list[-1].screen_name = auth_username
        self.current_token_index = random.randrange(self.token_number)
        self.logger = logging.getLogger('twitter')

    def query(self, url: str, params: dict) -> Union[dict, list, None]:
        for _ in range(self.token_number):
            self.current_token_index = (self.current_token_index + 1) % self.token_number
            try:
                if self.current_token_index < len(self.bearer_token_list):
                    headers = _get_headers(self.bearer_token_list[self.current_token_index])
                    response = requests.request('GET', url, headers=headers, params=params, timeout=300)
                else:
                    auth = self.auth_handler_list[self.current_token_index - len(self.bearer_token_list)].apply_auth()
                    response = requests.request('GET', url, auth=auth, params=params, timeout=300)
            except requests.exceptions.ConnectionError as e:
                self.logger.error('Request error: {}, try next token.'.format(e))
                continue
            if response.status_code in [200, 404, 403]:
                # 404 NOT_FOUND
                # 403 CURRENT_USER_SUSPENDED
                return response.json()
            if response.status_code != 429:
                # 429 TWEET_RATE_LIMIT_EXCEEDED
                self.logger.error('Request returned an error: {} {}, try next token.'.format(
                    response.status_code, response.text))
        self.logger.error('All tokens are unavailable, query fails. {}'.format(url))
        return None

    def get_user_by_username(self, username: str, params: dict = {}) -> dict:
        url = 'https://api.twitter.com/1.1/users/show.json'
        params['screen_name'] = username
        user = self.query(url, params)
        while user is None:
            time.sleep(60)
            user = self.query(url, params)
        return user

    def get_user_by_id(self, id: int, params: dict = {}) -> dict:
        url = 'https://api.twitter.com/1.1/users/show.json'
        params['user_id'] = id
        user = self.query(url, params)
        while user is None:
            time.sleep(60)
            user = self.query(url, params)
        return user

    def get_id_by_username(self, username: str):
        user = self.get_user_by_username(username, {})
        while user.get('errors', None):
            self.logger.error('Initialization error, please check if username {} exists'.format(username))
            print('\n'.join([str(error) for error in user['errors']]))
            time.sleep(60)
            user = self.get_user_by_username(username, {})
        return user['id']

    def check_tokens(self, test_username: str = 'X', output_response: bool = False):
        result = dict()
        url = 'https://api.twitter.com/1.1/users/lookup.json'
        params = {'screen_name': test_username}
        for bearer_token in self.bearer_token_list:
            headers = _get_headers(bearer_token)
            try:
                response = requests.request('GET', url, headers=headers, params=params)
            except requests.exceptions.ConnectionError as e:
                result[bearer_token] = False
                print(e)
                continue
            result[bearer_token] = (response.status_code == 200)
            if output_response:
                print(json.dumps(response.json(), indent=2))
        for auth_handler in self.auth_handler_list:
            try:
                response = requests.request('GET', url, params=params, auth=auth_handler.apply_auth())
            except requests.exceptions.ConnectionError as e:
                result[auth_handler.screen_name] = False
                print(e)
                continue
            result[auth_handler.screen_name] = (response.status_code == 200)
            if output_response:
                print(json.dumps(response.json(), indent=2))
        return result
