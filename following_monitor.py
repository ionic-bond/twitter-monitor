import time
from typing import List, Union, Tuple, Dict

from monitor_base import MonitorBase
from utils import find_all, find_one, get_cursor, get_content


class FollowingMonitor(MonitorBase):
    monitor_type = 'Following'
    rate_limit = 1

    def __init__(self, username: str, token_config: dict, cookies_dir: str, interval: int,
                 telegram_chat_id_list: List[int], cqhttp_url_list: List[str]):
        super().__init__(monitor_type=self.monitor_type,
                         username=username,
                         token_config=token_config,
                         cookies_dir=cookies_dir,
                         interval=interval,
                         telegram_chat_id_list=telegram_chat_id_list,
                         cqhttp_url_list=cqhttp_url_list)

        self.following_dict = self.get_all_following(self.user_id)

        self.logger.info('Init following monitor succeed.\nUser id: {}\nFollowing {} users: {}'.format(
            self.user_id, len(self.following_dict),
            [find_one(following, 'screen_name') for following in self.following_dict.values()]))

    def get_all_following(self, user_id: int) -> Dict[str, dict]:
        api_name = 'Following'
        params = {'userId': user_id, 'includePromotedContent': True, 'count': 1000}
        following_dict = dict()

        while True:
            json_response = self.twitter_watcher.query(api_name, params)
            following_list = find_all(json_response, 'user_results')
            while not following_list:
                import json
                self.logger.error(json.dumps(json_response, indent=2))
                time.sleep(10)
                json_response = self.twitter_watcher.query(api_name, params)
                following_list = find_all(json_response, 'user_results')

            for following in following_list:
                user_id = find_one(following, 'rest_id')
                following_dict[user_id] = following

            cursor = get_cursor(json_response)
            if not cursor or cursor.startswith('-1|') or cursor.startswith('0|'):
                break
            params['cursor'] = cursor

        return following_dict

    def parse_user_details(self, user: int) -> Tuple[str, Union[str, None]]:
        content = get_content(user)
        details_str = 'Name: {}'.format(content.get('name', ''))
        details_str += '\nBio: {}'.format(content.get('description', ''))
        details_str += '\nWebsite: {}'.format(
            content.get('entities', {}).get('url', {}).get('urls', [{}])[0].get('expanded_url', ''))
        details_str += '\nJoined at: {}'.format(content.get('created_at', ''))
        details_str += '\nFollowing: {}'.format(content.get('friends_count', -1))
        details_str += '\nFollowers: {}'.format(content.get('followers_count', -1))
        details_str += '\nTweets: {}'.format(content.get('statuses_count', -1))
        return details_str, content.get('profile_image_url_https', '').replace('_normal', '')

    def detect_changes(self, old_following_dict: set, new_following_dict: set) -> bool:
        if old_following_dict.keys() == new_following_dict.keys():
            return True
        max_changes = max(len(old_following_dict) / 2, 10)
        dec_user_id_list = old_following_dict.keys() - new_following_dict.keys()
        inc_user_id_list = new_following_dict.keys() - old_following_dict.keys()
        if len(dec_user_id_list) > max_changes or len(inc_user_id_list) > max_changes:
            return False
        if dec_user_id_list:
            self.logger.info('Unfollow: {}'.format(dec_user_id_list))
            for dec_user_id in dec_user_id_list:
                message = 'Unfollow: @{}'.format(find_one(old_following_dict[dec_user_id], 'screen_name'))
                details_str, profile_image_url = self.parse_user_details(old_following_dict[dec_user_id])
                if details_str:
                    message += '\n{}'.format(details_str)
                self.send_message(message=message, photo_url_list=[profile_image_url] if profile_image_url else [])
        if inc_user_id_list:
            self.logger.info('Follow: {}'.format(inc_user_id_list))
            for inc_user_id in inc_user_id_list:
                message = 'Follow: @{}'.format(find_one(new_following_dict[inc_user_id], 'screen_name'))
                details_str, profile_image_url = self.parse_user_details(new_following_dict[inc_user_id])
                if details_str:
                    message += '\n{}'.format(details_str)
                self.send_message(message=message, photo_url_list=[profile_image_url] if profile_image_url else [])
        return True

    def watch(self) -> bool:
        following_dict = self.get_all_following(self.user_id)
        if not self.detect_changes(self.following_dict, following_dict):
            return False
        self.following_dict = following_dict
        self.update_last_watch_time()
        return True

    def status(self) -> str:
        return 'Last: {}, number: {}'.format(self.last_watch_time, len(self.following_dict))
