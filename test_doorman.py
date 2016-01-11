#
# test_doorman.py
# Created by Hexapetalous on Jan 11, 2016.
#
# This is a part of C0004, a new version of Tenzor's entrance guard.
# For more info, see `doorman.py`.
#
from unittest import TestCase
from doorman import Doorman


class TestDoorman(TestCase):
    def test_redis(self):
        """
        Before this test it is necessary to start redis server:
        $ redis-server
        And after:
        $ redis-cli
        127.0.0.1:6379> flushdb
        OK
        127.0.0.1:6379> shutdown
        127.0.0.1:6379> quit
        """
        d = Doorman()
        d.redis_add_welcomed_people('Apple')
        d.redis_add_forbidden_people('Microsoft')
        self.assertEqual(d.redis_check_people('Apple'), True)
        self.assertEqual(d.redis_check_people('Microsoft'), False)
        self.assertEqual(d.redis_check_people('IBM'), None)
        return

    def test_redis_expire(self):
        """
        Wait patiently...
        """
        import time
        t = Doorman.WELCOMED_EXPIRE
        Doorman.WELCOMED_EXPIRE = 5
        d = Doorman()
        d.redis_add_welcomed_people('China')
        time.sleep(2)
        self.assertEqual(d.redis_check_people('China'), True)
        d.redis_add_welcomed_people('America')
        time.sleep(4)
        self.assertEqual(d.redis_check_people('China'), None)
        self.assertEqual(d.redis_check_people('America'), True)
        Doorman.WELCOMED_EXPIRE = t
        return

    def test_web_validate(self):
        """
        Make sure that you are under Tenzor's Wi-Fi.
        """
        d = Doorman()
        self.assertEqual(d.web_validate_people('Stranger'), False)
        return
