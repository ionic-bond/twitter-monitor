import json
import logging
import os
import requests
import time


class AquaMonitor:

    def __init__(self):
        self.sleep_second = 30
        self.following_users = self.get_all_following_users()
        logging.info('Now following users number: {}'.format(len(self.following_users)))
        logging.info(self.following_users)

    def auth(self):
        return os.environ.get("BEARER_TOKEN")
    
    def create_url(self):
        # user_id = 1024528894940987392
        user_id = 2894395322
        return "https://api.twitter.com/2/users/{}/following".format(user_id)
    
    def create_headers(self, bearer_token):
        headers = {"Authorization": "Bearer {}".format(bearer_token)}
        return headers
    
    def connect_to_endpoint(self, url, headers, params):
        response = requests.request("GET", url, headers=headers, params=params)
        while response.status_code != 200:
            logging.error(
                    "Request returned an error: {} {}".format(
                        response.status_code, response.text
                        )
                    )
            time.sleep(self.sleep_second)
            response = requests.request("GET", url, headers=headers, params=params)
            if response.status_code != 200:
                self.sleep_second *= 2
                logging.info('Changed sleep second to {}'.format(self.sleep_second))
        return response.json()
    
    def get_all_following_users(self):
        bearer_token = self.auth()
        url = self.create_url()
        headers = self.create_headers(bearer_token)
        finished = False
        params = dict()
        result = list()
        while not finished:
            json_response = self.connect_to_endpoint(url, headers, params)
            if 'data' in json_response:
                result.extend(json_response['data'])
            if 'meta' in json_response and 'next_token' in json_response['meta']:
                params = { "pagination_token": json_response['meta']['next_token'] }
            else:
                finished = True
        return set([user['username'] for user in result])
    
    def work(self):
        while True:
            following_users = self.get_all_following_users()
            logging.info('Now following users number: {}'.format(len(following_users)))
            if following_users != self.following_users and abs(len(following_users) - len(self.following_users)) < 20:
                new_follow = following_users - self.following_users
                if new_follow:
                    logging.error('Detected new following: {}'.format(new_follow))
                unfollow = self.following_users - following_users
                if unfollow:
                    logging.error('Detected unfollowing: {}'.format(unfollow))
                self.following_users = following_users

            time.sleep(self.sleep_second)


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    aqua = AquaMonitor()
    aqua.work()
