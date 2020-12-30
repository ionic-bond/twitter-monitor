import click
import json
import logging
import os
import requests
import time

MIN_SLEEP_SECOND = 60


class Sleeper:

    def __init__(self):
        self.sleep_second = MIN_SLEEP_SECOND
        self.normal_count = 0


    def sleep(self, normal: bool):
        if normal:
            self.normal_count += 1
            if self.normal_count > 20 and self.sleep_second > MIN_SLEEP_SECOND:
                self.sleep_second /= 2
                logging.info('Changed sleep second to {}'.format(self.sleep_secnod))
        else:
            self.normal_count = 0
            self.sleep_second *= 2
            logging.info('Changed sleep second to {}'.format(self.sleep_secnod))
        time.sleep(self.sleep_second)


class Monitor:

    def __init__(self, username: str):
        self.sleeper = Sleeper()
        self.user_id = self.get_user_id(username)
        self.following_users = self.get_all_following_users()
        logging.info('Init monitor succeed.\nUsername: {}\nUser id: {}\nFollowing users: {}'.format(
            username, self.user_id, self.following_users))


    @staticmethod
    def get_headers():
        token = os.environ.get("BEARER_TOKEN")
        return {"Authorization": "Bearer {}".format(token)}


    def send_get_request(self, url: str, params: dict={}):
        headers = self.get_headers()
        response = requests.request("GET", url, headers=headers, params=params)
        while response.status_code != 200:
            logging.error("Request returned an error: {} {}".format(
                response.status_code, response.text))
            self.sleeper.sleep(normal=False)
            response = requests.request("GET", url, headers=headers, params=params)
        return response.json()


    def get_user_id(self, username: str) -> str:
        url = url = "https://api.twitter.com/2/users/by/username/{}".format(username)
        user = self.send_get_request(url)
        return user['data']['id']


    def get_all_following_users(self) -> set:
        url = 'https://api.twitter.com/2/users/{}/following'.format(self.user_id)
        params = {'max_results': 1000}
        json_response = self.send_get_request(url, params)
        results = json_response.get('data', [])
        next_token = json_response.get('meta', {}).get('next_token', '')
        while next_token:
            params['pagination_token'] = next_token
            json_response = self.send_get_request(url, params)
            results.extend(json_response.get('data', []))
            next_token = json_response.get('meta', {}).get('next_token', '')
        return set([result.get('username', '') for result in results])


    @staticmethod
    def detect_changes(old_following_users: set, new_following_users: set):
        if old_following_users == new_following_users:
            return
        max_changes = max(len(old_following_users) / 2, 10)
        if abs(len(old_following_users) - len(new_following_users)) > max_changes:
            return
        inc_users = new_following_users - old_following_users
        if inc_users:
            logging.error('New followed users detected: {}'.format(inc_users))
        dec_users = old_following_users - new_following_users
        if dec_users:
            logging.error('Unfollowed user detected: {}'.format(dec_users))


    def run(self):
        count = 0
        while True:
            self.sleeper.sleep(normal=True)
            following_users = self.get_all_following_users()
            count += 1
            if count % 10 == 0:
                logging.info('Number of following users: {}'.format(len(following_users)))
            self.detect_changes(self.following_users, following_users)
            self.following_users = following_users


@click.group()
def cli():
    pass


@cli.command()
@click.option('--username', required=True, help="Monitoring username.")
@click.option('--log_path',
              default='/tmp/twitter_following_monitor.log',
              help="Path to output logging's log.")
def run(username, log_path):
    logging.basicConfig(filename=log_path, format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    monitor = Monitor(username)
    monitor.run()


if __name__ == "__main__":
    cli()
