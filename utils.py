#!/usr/bin/python3

import logging
import os
import requests
import sys


def get_headers():
    token = os.environ.get("BEARER_TOKEN")
    return {"Authorization": "Bearer {}".format(token)}

def send_get_request(url: str, params: dict={}):
    headers = get_headers()
    try:
        response = requests.request("GET", url, headers=headers, params=params)
    except requests.exceptions.ConnectionError as e:
        logging.error("Request error: {}".format(e))
        return None
    if response.status_code != 200:
        logging.error("Request returned an error: {} {}".format(
            response.status_code, response.text))
        return None
    return response.json()

def get_user_id(username: str) -> str:
    url = "https://api.twitter.com/2/users/by/username/{}".format(username)
    user = send_get_request(url)
    while not user:
        user = send_get_request(url)
    return user['data']['id']

def get_like_id_set(likes: list) -> set:
    return set([like['id'] for like in likes])

def init_logging(log_path):
    logging.basicConfig(filename=log_path, format='%(asctime)s - %(message)s', level=logging.INFO)

