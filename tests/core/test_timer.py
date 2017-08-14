from utils.persistable_store import PersistableStore
from utils.timer import Timer
from unittest import TestCase
import time
import uuid

class TestPersistableStore(TestCase):

    def test_timer_not_expired(self):
        timer = Timer("timer_name", 10)
        timer.reset()
        time.sleep(1)
        self.assertEqual(timer.expired(), False)

    def test_timer_expired(self):
        timer = Timer("timer_name", 1)
        timer.reset()
        time.sleep(1)
        self.assertEqual(timer.expired(), True)

    def test_save_timer(self):
        store = self._new_random_store()
        timer = Timer("timer_name", 1)
        timer.reset()
        timer.persist(store)
        store.commit_status()
        time.sleep(1)

        new_store = self._new_random_store(store.persistable_check_name)
        new_store.load_status()
        timer = Timer("timer_name", 1)
        timer.load(new_store)
        self.assertEqual(timer.expired(), True)

    def _new_random_store(self, check_name = str(uuid.uuid4())):
        store = PersistableStore(check_name, "instanceid")
        return store
