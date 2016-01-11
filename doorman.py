#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# doorman.py
# Created by Hexapetalous on Jan 11, 2016.
#
# This is a part of C0004, a new version of Tenzor's entrance guard.
# This is the whole.
#
# Copyright (c) 2016 Hexapetalous. All rights reserved.
# This code is licensed under MIT License.
#
import logging
import requests
import sys
import redis


class Doorman(object):
    # REDIS PART
    redis_server = None

    WELCOMED_EXPIRE = 60 * 60 * 24 * 2
    FORBIDDEN_EXPIRE = 60 * 2
    WELCOMED_VALUE = 'welcome'
    FORBIDDEN_VALUE = 'get out'
    LOG_LIST_NAME = 'logs'

    def redis_init(self):
        self.redis_server = redis.StrictRedis()
        return

    def redis_add_people(self, name, welcomed):
        if welcomed:
            self.redis_add_welcomed_people(name)
        else:
            self.redis_add_forbidden_people(name)
        return

    def redis_add_welcomed_people(self, name):
        self.redis_server.setex(name, self.WELCOMED_EXPIRE, self.WELCOMED_VALUE)
        self.logger.debug('Added \"' + name + '\" to welcomed people set.')
        return

    def redis_add_forbidden_people(self, name):
        self.redis_server.setex(name, self.FORBIDDEN_EXPIRE,
                                self.FORBIDDEN_VALUE)
        self.logger.debug('Added \"' + name + '\" to forbidden people set.')
        return

    def redis_check_people(self, name):
        if not self.redis_server.exists(name):
            return None
        if self.redis_server.get(name) == self.WELCOMED_VALUE:
            return True
        else:
            return False

    def redis_save_log(self, log):
        self.redis_server.rpush(self.LOG_LIST_NAME, log)

    def redis_get_all_logs(self):
        res = []
        while self.redis_server.llen(self.LOG_LIST_NAME) > 0:
            res.append(self.redis_server.lpop(self.LOG_LIST_NAME))
        return res

    # WEB PART
    API_URL = 'https://op.tiaozhan.com/doorman/Home/Doorman'
    API_KEY = 'Tiaozhan-Work'

    def web_validate_people(self, name):
        url = self.API_URL + '/validate'
        headers = \
            {'X-Doorman': self.API_KEY, 'X-Doorman-Action': 'VALIDATE_CARD_NO'}
        params = {'card_no': name}
        try:
            r = requests.get(url, headers=headers, params=params)
            if r.status_code != requests.codes.ok:
                r.raise_for_status()
            try:
                result = r.json()
                if name in result['valid_card_no']:
                    return True
                elif name in result['invalid_card_no']:
                    return False
                else:
                    self.logger.error(
                            'Did not find result in data from server.')
                    self.logger.error(r.text)
            except ValueError:
                self.logger.error('Can not resolve data from server.')
                self.logger.error(r.text)
        except requests.exceptions.RequestException:
            exception, message, traceback = sys.exc_info()
            self.logger.error('%s %s' % (exception, message))
        return None

    # LOG PART
    logger = None

    def log_logger_init(self, level):
        logger = logging.getLogger('Doorman logger')
        log_format = logging.Formatter(
                '%(asctime)s [%(levelname)s]%(funcName)s %(message)s',
                '%Y-%m-%d %H:%M:%S')
        file_handle = logging.StreamHandler()
        file_handle.setFormatter(log_format)
        file_handle.setLevel(level)
        logger.addHandler(file_handle)
        self.logger = logger
        return

    # MAIN PART
    def __init__(self):
        super(Doorman, self).__init__()
        self.redis_init()
        self.log_logger_init(logging.DEBUG)

    def main_loop(self):
        try:
            while True:
                name = raw_input('Your name, please:')
                if self.main_validate(name):
                    self.main_open_door()
        except KeyboardInterrupt:
            self.logger.info('Keyboard interrupted.')
            self.logger.info('Exit.')
            return

    def main_validate(self, name):
        try:
            res = self.redis_check_people(name)
        except redis.RedisError:
            exception, message, traceback = sys.exc_info()
            self.logger.error('%s %s' % (exception, message))
            return None
        if res is not None:
            # TODO: Add to log.
            return res
        else:
            res = self.web_validate_people(name)
            if res is None:
                return None
            # Try to write to cache first.
            try:
                self.redis_add_people(name, res)
            except redis.RedisError:
                exception, message, traceback = sys.exc_info()
                self.logger.error('%s %s' % (exception, message))
            return res

    @staticmethod
    def main_open_door():
        print 'The door is opened.'
        return


if __name__ == '__main__':
    d = Doorman()
    d.main_loop()