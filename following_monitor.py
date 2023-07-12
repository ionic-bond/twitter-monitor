import time
from typing import List, Union, Tuple, Dict

from monitor_base import MonitorBase


class FollowingMonitor(MonitorBase):
    monitor_type = 'Following'
    rate_limit = 1

    def __init__(self, username: str, token_config: dict, cache_dir: str, cookies_dir: str, interval: int,
                 telegram_chat_id_list: List[int], cqhttp_url_list: List[str]):
        super().__init__(monitor_type=self.monitor_type,
                         username=username,
                         token_config=token_config,
                         cache_dir=cache_dir,
                         cookies_dir=cookies_dir,
                         interval=interval,
                         telegram_chat_id_list=telegram_chat_id_list,
                         cqhttp_url_list=cqhttp_url_list)

        self.following_dict = self.get_all_following(self.user_id)
        while self.following_dict is None:
            time.sleep(60)
            self.following_dict = self.get_all_following(self.user_id)

        self.logger.info('Init following monitor succeed.\nUser id: {}\nFollowing {} users: {}'.format(
            self.user_id, len(self.following_dict), [user['screen_name'] for user in self.following_dict.values()]))

    def get_all_following(self, user_id: int) -> Union[Dict[str, dict], None]:
        url = 'https://api.twitter.com/1.1/friends/list.json'
        params = {'user_id': user_id, 'count': 200, 'skip_status': True, 'include_user_entities': False}
        json_response = self.twitter_watcher.query(url, params)
        if not json_response or json_response.get('errors', None):
            return None
        users = json_response.get('users', [])
        next_cursor = json_response.get('next_cursor', 0)
        while next_cursor:
            params['cursor'] = next_cursor
            json_response = self.twitter_watcher.query(url, params)
            if not json_response or json_response.get('errors', None):
                return None
            users.extend(json_response.get('users', []))
            next_cursor = json_response.get('next_cursor', 0)
        result = dict()
        for user in users:
            result[user['id']] = user
        return result

    def get_user_details(self, user_id: int) -> Tuple[str, Union[str, None]]:
        user = self.twitter_watcher.get_user_by_id(user_id)
        if user.get('errors', None):
            return '\n'.join([str(error) for error in user['errors']]), None
        details_str = 'Name: {}'.format(user.get('name', ''))
        details_str += '\nBio: {}'.format(user.get('description', ''))
        details_str += '\nWebsite: {}'.format(user.get('url', ''))
        details_str += '\nJoined at: {}'.format(user.get('created_at', ''))
        details_str += '\nFollowing: {}'.format(user.get('friends_count', -1))
        details_str += '\nFollowers: {}'.format(user.get('followers_count', -1))
        details_str += '\nTweets: {}'.format(user.get('statuses_count', -1))
        return details_str, user.get('profile_image_url', '').replace('_normal', '')

    def detect_changes(self, old_following_dict: set, new_following_dict: set):
        if old_following_dict.keys() == new_following_dict.keys():
            return
        max_changes = max(len(old_following_dict) / 2, 10)
        dec_user_ids = old_following_dict.keys() - new_following_dict.keys()
        inc_user_ids = new_following_dict.keys() - old_following_dict.keys()
        if len(dec_user_ids) > max_changes or len(inc_user_ids) > max_changes:
            return
        if dec_user_ids:
            self.logger.info('Unfollow: {}'.format(dec_user_ids))
            for dec_user_id in dec_user_ids:
                message = 'Unfollow: @{}'.format(old_following_dict[dec_user_id]['screen_name'])
                details_str, profile_image_url = self.get_user_details(dec_user_id)
                if details_str:
                    message += '\n{}'.format(details_str)
                self.send_message(message=message, photo_url_list=[profile_image_url] if profile_image_url else [])
        if inc_user_ids:
            self.logger.info('Follow: {}'.format(inc_user_ids))
            for inc_user_id in inc_user_ids:
                message = 'Follow: @{}'.format(new_following_dict[inc_user_id]['screen_name'])
                details_str, profile_image_url = self.get_user_details(inc_user_id)
                if details_str:
                    message += '\n{}'.format(details_str)
                self.send_message(message=message, photo_url_list=[profile_image_url] if profile_image_url else [])

    def watch(self) -> bool:
        following_dict = self.get_all_following(self.user_id)
        if not following_dict:
            return False
        self.detect_changes(self.following_dict, following_dict)
        self.following_dict = following_dict
        self.update_last_watch_time()
        return True

    def status(self) -> str:
        return 'Last: {}, number: {}'.format(self.last_watch_time, len(self.following_dict))
