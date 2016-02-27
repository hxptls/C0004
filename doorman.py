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
import time
import json
import thread


# For info: function used to open the door is around line #292.
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
        self.logger.debug('Added \"%s\" to welcomed people set.' % name)
        return

    def redis_add_forbidden_people(self, name):
        self.redis_server.setex(name, self.FORBIDDEN_EXPIRE,
                                self.FORBIDDEN_VALUE)
        self.logger.debug('Added \"%s\" to forbidden people set.' % name)
        return

    def redis_check_people(self, name):
        if not self.redis_server.exists(name):
            return None
        if self.redis_server.get(name) == self.WELCOMED_VALUE:
            return True
        else:
            return False

    def redis_get_old_records(self):
        old = []
        for name in self.redis_server.keys():
            if self.redis_server.ttl(name) < 60 * 60:
                old.append(name)
        return old

    def redis_delete_people(self, name):
        self.redis_server.delete(name)

    def redis_save_log(self, log):
        self.redis_server.rpush(self.LOG_LIST_NAME, log)

    def redis_get_all_logs(self):
        res = []
        while self.redis_server.llen(self.LOG_LIST_NAME) > 0:
            res.append(self.redis_server.lpop(self.LOG_LIST_NAME))
        return res

    def redis_get_log_count(self):
        return self.redis_server.llen(self.LOG_LIST_NAME)

    # VALIDATING LOG PART
    validating_log_id = 0

    def validating_log_create(self, name, passed):
        log = {'log_id': self.validating_log_id,
               'card_no': name,
               'time': str(time.time())}
        self.validating_log_id += 1
        if passed:
            log['status'] = 'PASS_CACHE_HIT'
        else:
            log['status'] = 'PASS_CACHE_FORBIDDEN'
        return log

    # WEB PART
    API_URL = 'https://op.tiaozhan.com/doorman/Home/Doorman'
    API_KEY = 'Tiaozhan-Work'

    # This is a new version of web API.
    # For some stupid man who changed the logic of the server.
    def web_validate_people_20160227(self, name):
        url = self.API_URL + '/validate'
        headers = {'X-Doorman': self.API_KEY,
                   'X-Doorman-Action': 'VALIDATE_CARD_NO'}
        params = {'card_no': name}
        try:
            r = requests.get(url, headers=headers, params=params)
            if r.status_code != requests.codes.ok:
                r.raise_for_status()
            try:
                result = r.json()
                if result['status'] == 0:
                    return True
                else:
                    return False
            except ValueError:
                self.logger.error('Can not resolve data from server.')
                self.logger.error(r.text)
            except KeyError:
                self.logger.error(
                        'Do not have necessary key in data from server.')
                self.logger.error(r.text)
        except requests.exceptions.RequestException:
            exception, message, traceback = sys.exc_info()
            self.logger.error('%s %s' % (exception, message))
        return None

    def web_validate_people(self, name):
        url = self.API_URL + '/validate'
        headers = {'X-Doorman': self.API_KEY,
                   'X-Doorman-Action': 'VALIDATE_CARD_NO'}
        params = {'card_no': name}
        try:
            r = requests.get(url, headers=headers, params=params)
            if r.status_code != requests.codes.ok:
                r.raise_for_status()
            try:
                result = r.json()
                # FOR TEST
                # result['valid_card_no'] = ['Someone not in cache']
                # END TEST
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
            except KeyError:
                self.logger.error(
                        'Do not have necessary key in data from server.')
                self.logger.error(r.text)
        except requests.exceptions.RequestException:
            exception, message, traceback = sys.exc_info()
            self.logger.error('%s %s' % (exception, message))
        return None

    # Don't do anything with exceptions here.
    # TODO: Maybe I should handle some errors here. The error is so bother me!
    def web_validate_old_records(self, names):
        url = self.API_URL + '/validate'
        headers = {'X-Doorman': self.API_KEY,
                   'X-Doorman-Action': 'VALIDATE_CARD_NO'}
        params = {'card_no': ','.join(names)}
        r = requests.get(url, headers=headers, params=params)
        if r.status_code != requests.codes.ok:
            return None
        return r.json()['valid_card_no']

    def web_post_log(self):
        try:
            logs = self.redis_get_all_logs()
        except redis.RedisError:
            exception, message, traceback = sys.exc_info()
            self.logger.error('%s %s' % (exception, message))
            return
        url = self.API_URL + '/log'
        headers = {'content-type': 'application/json',
                   'X-Doorman': self.API_KEY,
                   'X-Doorman-Action': 'POST_LOG'}
        data = {'count': len(logs), 'log': logs}
        try:
            r = requests.post(url, headers=headers, data=json.dumps(data))
            if r.status_code != requests.codes.ok:
                r.raise_for_status()
            res = None
            try:
                res = r.json()
            except ValueError:
                self.logger.error('Can not resolve data from server.')
                self.logger.error(r.text)
            try:
                if res['status'] != 0:
                    self.logger.error(
                            'Server returned status %d.' % res['status'])
                    self.logger.error('Succeed logs: %s' % res['success_log'])
                    for log in logs:
                        if log['log_id'] not in res['success_log']:
                            self.logger.error('Failed log: %s' % log)
                    # If a log is not accepted by server, it's probably that it
                    # contains some errors and will never be accepted.
                    # So I just write it in log and ignore it, return success.
                    return True
                else:
                    self.logger.info('Log posted successful.')
                    return True
            except KeyError:
                exception, msg, traceback = sys.exc_info()
                self.logger.error('%s: %s' % (exception, msg))
                return False
        except requests.exceptions.RequestException:
            exception, msg, traceback = sys.exc_info()
            self.logger.error('%s: %s' % (exception, msg))
            return False

    def web_send_heart_beat(self):
        url = self.API_URL + '/sys'
        headers = {'X-Doorman': self.API_KEY, 'X-Doorman-Action': 'HEART_BEAT'}
        data = {'client_time': str(time.time()),
                'client_redis_status': 'OK',
                'client_log_queue': self.redis_get_log_count()}
        try:
            r = requests.put(url, headers=headers, data=data)
            result = None
            try:
                result = r.json()
            except ValueError:
                exception, msg, traceback = sys.exc_info()
                self.logger.info('%s: %s' % (exception, msg))
            try:
                if result['status'] != 0:
                    self.logger.error(
                            'Server returned status: %d' % result['status'])
                    self.logger.error('Server returned: %s' % r.text)
                # Send a little earlier than expected doesn't hurt~
                # And the net is slow, the daemon needs to sleep.
                self.next_heart_beat = result['next_heart_beat'] - 2
                # The server's time fix logic is unbelievable.
                # TODO: Fix it.
                # self.delta_time += result['time_fix']
            except KeyError:
                exception, msg, traceback = sys.exc_info()
                self.logger.info('%s: %s' % (exception, msg))
        except requests.exceptions.RequestException:
            exception, msg, traceback = sys.exc_info()
            self.logger.info('%s: %s' % (exception, msg))
        # If something goes wrong, `next_heart_beat` will not be changed and
        # thus next heart beat will be sent immediately until one is succeed.
        return

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
        # Multi-thread working
        thread.start_new_thread(self.heart_beat_daemon, ())
        thread.start_new_thread(self.expire_update_daemon, ())

    def main_loop(self):
        try:
            while True:
                name = raw_input('Your name, please:')
                if self.main_validate(name):
                    self.main_open_door()
                if self.redis_get_log_count() > 0:
                    # The server logic has been changed and I don't know what it
                    #  is.
                    # TODO: Fix it.
                    # self.web_post_log()
                    pass
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
            log = self.validating_log_create(name, res)
            try:
                self.redis_save_log(log)
            except redis.RedisError:
                exception, message, traceback = sys.exc_info()
                self.logger.error('%s %s' % (exception, message))
            return res
        else:
            res = self.web_validate_people_20160227(name)
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

    # HEART BEAT PART
    # I still considered that the system time is difficult to change and change
    # correctly. So the program will keep another timer based on system's.
    delta_time = 0
    next_heart_beat = time.time()

    def heart_beat_daemon(self):
        while True:
            now = time.time() + self.delta_time
            if now >= self.next_heart_beat:
                self.web_send_heart_beat()
            time.sleep(1)

    # EXPIRE UPDATE PART
    def expire_update_daemon(self):
        while True:
            time.sleep(60 * 60)
            # noinspection PyBroadException
            try:
                old_records = self.redis_get_old_records()
                if not old_records:
                    continue
                still_valid = self.web_validate_old_records(old_records)
                if still_valid is None:
                    continue
                for name in old_records:
                    if name in still_valid:
                        self.redis_add_welcomed_people(name)
                    else:
                        self.redis_delete_people(name)
                        # It is almost impossible that this guy came to here in
                        # 2 minutes after this action. So it's needless to add
                        # it to forbidden.
            except:
                exception, message, traceback = sys.exc_info()
                self.logger.error('%s %s' % (exception, message))


if __name__ == '__main__':
    d = Doorman()
    d.main_loop()
