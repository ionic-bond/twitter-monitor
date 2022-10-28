import logging
import random
import requests
from typing import List, Union


def _get_headers(bearer_token: str):
    return {'Authorization': 'Bearer {}'.format(bearer_token)}


class TwitterWatcher:

    def __init__(self, bearer_token_list: List[str]):
        assert bearer_token_list
        self.bearer_token_list = bearer_token_list
        self.current_token_index = random.randrange(len(bearer_token_list))
        self.logger = logging.getLogger('twitter')

    def query(self, url: str, params: dict) -> Union[dict, list, None]:
        for _ in range(len(self.bearer_token_list)):
            self.current_token_index = (self.current_token_index + 1) % len(self.bearer_token_list)
            headers = _get_headers(self.bearer_token_list[self.current_token_index])
            try:
                response = requests.request('GET', url, headers=headers, params=params, timeout=300)
            except requests.exceptions.ConnectionError as e:
                self.logger.error('Request error: {}, try next token.'.format(e))
                continue
            if response.status_code == 200:
                return response.json()
            if response.status_code != 429:
                self.logger.error('Request returned an error: {} {}, try next token.'.format(
                    response.status_code, response.text))
        self.logger.error('All tokens are unavailable, query fails. {}'.format(url))
        return None

    def get_user_by_username(self, username: str, params: dict) -> dict:
        url = 'https://api.twitter.com/2/users/by/username/{}'.format(username)
        user = None
        while user is None:
            user = self.query(url, params)
        return user

    def get_user_by_id(self, id: str, params: dict) -> dict:
        url = 'https://api.twitter.com/2/users/{}'.format(id)
        user = None
        while user is None:
            user = self.query(url, params)
        return user

    def get_id_by_username(self, username: str):
        user = self.get_user_by_username(username, {})
        if user.get('errors', None):
            logging.error('Initialization error, please check if username {} exists'.format(username))
            raise ValueError('\n'.join([error['detail'] for error in user['errors']]))
        return user['data']['id']

    def check_token(self):
        result = dict()
        for bearer_token in self.bearer_token_list:
            headers = _get_headers(bearer_token)
            url = 'https://api.twitter.com/2/users/by/username/Twitter'
            try:
                response = requests.request('GET', url, headers=headers)
            except requests.exceptions.ConnectionError as e:
                result[bearer_token] = False
                print(e)
                continue
            result[bearer_token] = (response.status_code == 200)
            print(response.json())
        return result
