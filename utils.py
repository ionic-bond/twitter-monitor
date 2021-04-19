#!/usr/bin/python3

import json
import logging
import os
import requests
import sys


def get_token(token_name: str) -> str:
    with open(os.path.join(sys.path[0], 'token.json'), 'r') as token_file:
        data = json.load(token_file)
        token = data.get(token_name, None)
        return token


def get_headers():
    token = get_token('BEARER_TOKEN')
    if not token:
        raise ValueError('BEARER_TOKEN is null, please fill in it.')
    return {'Authorization': 'Bearer {}'.format(token)}


def send_get_request(url: str, params: dict = {}):
    headers = get_headers()
    try:
        response = requests.request('GET', url, headers=headers, params=params)
    except requests.exceptions.ConnectionError as e:
        logging.error('Request error: {}'.format(e))
        return None
    if response.status_code != 200:
        logging.error('Request returned an error: {} {}'.format(response.status_code,
                                                                response.text))
        return None
    return response.json()


def get_user_id(username: str) -> str:
    url = 'https://api.twitter.com/2/users/by/username/{}'.format(username)
    user = send_get_request(url)
    while not user:
        user = send_get_request(url)
    return user['data']['id']


def get_like_id_set(likes: list) -> set:
    return set([like['id'] for like in likes])


def init_logging(log_path):
    logging.basicConfig(filename=log_path, format='%(asctime)s - %(message)s', level=logging.INFO)
