#!/usr/bin/python3

import logging
import os
import requests


def get_headers():
    token = os.environ.get("BEARER_TOKEN")
    return {"Authorization": "Bearer {}".format(token)}

def send_get_request(url: str, params: dict={}):
    headers = get_headers()
    response = requests.request("GET", url, headers=headers, params=params)
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
