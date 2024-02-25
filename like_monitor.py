import time

from typing import List, Union, Set

from monitor_base import MonitorBase
from utils import parse_media_from_tweet, parse_text_from_tweet, find_all, find_one


def _get_like_id(like: dict) -> str:
    return find_one(like, 'rest_id')


def _get_like_id_set(like_list: list) -> Set[str]:
    return set(_get_like_id(like) for like in like_list)


def _filter_advertisers(like_list: list) -> list:
    result = []
    for like in like_list:
        if not find_one(like, 'card'):
            result.append(like)
    return result


class LikeMonitor(MonitorBase):
    monitor_type = 'Like'
    like_id_set_max_size = 1000

    def __init__(self, username: str, token_config: dict, cookies_dir: str, telegram_chat_id_list: List[int],
                 cqhttp_url_list: List[str]):
        super().__init__(monitor_type=self.monitor_type,
                         username=username,
                         token_config=token_config,
                         cookies_dir=cookies_dir,
                         telegram_chat_id_list=telegram_chat_id_list,
                         cqhttp_url_list=cqhttp_url_list)

        like_list = self.get_like_list()
        while like_list is None:
            time.sleep(60)
            like_list = self.get_like_list()
        self.existing_like_id_set = _get_like_id_set(like_list)

        self.logger.info('Init like monitor succeed.\nUser id: {}\nExisting {} likes: {}'.format(
            self.user_id, len(self.existing_like_id_set), self.existing_like_id_set))

    def get_like_list(self) -> Union[list, None]:
        api_name = 'Likes'
        params = {'userId': self.user_id, 'includePromotedContent': True, 'count': 1000}
        json_response = self.twitter_watcher.query(api_name, params)
        if json_response is None:
            return None
        return _filter_advertisers(find_all(json_response, 'tweet_results'))

    def watch(self) -> bool:
        like_list = self.get_like_list()
        if like_list is None:
            return False

        new_like_list = []
        for like in like_list:
            like_id = _get_like_id(like)
            if like_id in self.existing_like_id_set:
                break
            self.existing_like_id_set.add(like_id)
            new_like_list.append(like)

        for like in reversed(new_like_list):
            photo_url_list, video_url_list = parse_media_from_tweet(like)
            text = parse_text_from_tweet(like)
            user = find_one(like, 'user_results')
            username = find_one(user, 'screen_name')
            self.send_message('@{}: {}'.format(username, text), photo_url_list, video_url_list)

        self.update_last_watch_time()
        return True

    def status(self) -> str:
        return 'Last: {}, num: {}'.format(self.last_watch_time, len(self.existing_like_id_set))
