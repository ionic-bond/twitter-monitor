import logging
import time

import requests

from utils import check_initialized
from x_client_transaction.utils import handle_x_migration
from x_client_transaction import ClientTransaction


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
        response = requests.get(
            'https://github.com/ionic-bond/TwitterInternalAPIDocument/raw/master/docs/json/API.json', timeout=300)
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
        cls.init_client_transaction()
        cls.logger.info('Pull GraphQL API data success, API number: {}'.format(len(cls.graphql_api_data)))
        return True

    @classmethod
    def init_client_transaction(cls):
        session = requests.Session()
        session.headers = {
            'Authority': 'x.com',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Referer': 'https://x.com',
            'User-Agent': cls.headers['User-Agent'],
            'X-Twitter-Active-User': 'yes',
            'X-Twitter-Client-Language': 'en'
        }
        response = handle_x_migration(session)
        cls.ct = ClientTransaction(response)

    @classmethod
    def get_clint_transaction_id(cls, method: str, url: str):
        return cls.ct.generate_transaction_id(method=method,
                                              path=url.replace('https://x.com', '').replace('https://twitter.com', ''))

    @classmethod
    @check_initialized
    def get_api_data(cls, api_name):
        if api_name not in cls.graphql_api_data:
            raise ValueError('Unkonw API name: {}'.format(api_name))

        api_data = cls.graphql_api_data[api_name]
        headers = cls.headers.copy()
        transaction_id = cls.get_clint_transaction_id(api_data['method'], api_data['url'])
        headers['x-client-transaction-id'] = transaction_id

        return api_data['url'], api_data['method'], headers, api_data['features']


GraphqlAPI.init()
