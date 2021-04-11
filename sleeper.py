#!/usr/bin/python3

import logging
import time

class Sleeper:

    def __init__(self, original_sleep_second):
        self.original_sleep_second = original_sleep_second
        self.sleep_second = original_sleep_second
        self.normal_count = 0


    def sleep(self, normal: bool):
        if normal:
            self.normal_count += 1
            if self.normal_count > 20 and self.sleep_second > self.original_sleep_second:
                self.sleep_second /= 2
                logging.info('Changed sleep second to {}'.format(self.sleep_second))
        else:
            self.normal_count = 0
            self.sleep_second *= 2
            logging.info('Changed sleep second to {}'.format(self.sleep_second))
        time.sleep(self.sleep_second)
