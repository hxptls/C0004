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
from redisco.containers import Set


class Doorman(object):
    def __init__(self):
        super(Doorman, self).__init__()
        self.redis_init()
        self.log_logger_init(logging.DEBUG)

    # REDIS PART
    welcomed_people = None
    forbidden_people = None

    def redis_init(self):
        self.welcomed_people = Set('Welcomed people')
        self.forbidden_people = Set('Forbidden people')
        return

    def redis_add_welcomed_people(self, name):
        self.welcomed_people.add(name)
        self.logger.debug('Added \"' + name + '\" to welcomed people set.')
        return

    def redis_add_forbidden_people(self, name):
        self.forbidden_people.add(name)
        self.logger.debug('Added \"' + name + '\" to forbidden people set.')
        return

    def redis_check_people(self, name):
        if name in self.welcomed_people:
            return True
        elif name in self.forbidden_people:
            return False
        else:
            return None

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
