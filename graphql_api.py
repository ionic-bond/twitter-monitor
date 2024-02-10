import logging
import time

import requests


class GraphqlAPI():
    initialized = False

    def __new__(cls):
        raise Exception('Do not instantiate this class!')

    @classmethod
    def init(cls) -> None:
        cls.logger = logging.getLogger('api')
        while not cls.update_api_data():
            time.sleep(10)
        cls.initialized = True

    @classmethod
    def update_api_data(cls):
        response = requests.get('https://github.com/fa0311/TwitterInternalAPIDocument/raw/master/docs/json/API.json',
                                timeout=300)
        if response.status_code != 200:
            cls.logger.error('Request returned an error: {} {}.'.format(response.status_code, response.text))
            return False
        json_data = response.json()

        if not json_data.get('graphql', {}):
            cls.logger.error('Can not get Graphql API data from json')
            return False
        if not json_data.get('header', {}):
            cls.logger.error('Can not get header data from json')
            return False

        cls.graphql_api_data = json_data['graphql']
        cls.headers = json_data['header']
        return True

    @classmethod
    def get_api_data(cls, api_name):
        if not cls.initialized:
            raise RuntimeError('Class has not initialized!')
        if api_name not in cls.graphql_api_data:
            raise ValueError('Unkonw API name: {}'.format(api_name))

        api_data = cls.graphql_api_data[api_name]
        return api_data['url'], api_data['method'], cls.headers, api_data['features']
