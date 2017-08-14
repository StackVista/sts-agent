from utils.persistable_store import PersistableStore
from unittest import TestCase
import uuid

class TestPersistableStore(TestCase):

    def test_create_store(self):
        check_name = str(uuid.uuid4())
        test_object = {'test': 42.0}
        store = PersistableStore(check_name, "instanceid")
        store.load_status()
        self.assertEqual(store['test_field'], None)
        store['test_field'] = test_object
        store.commit_status()

        store.load_status()
        self.assertEqual(store['test_field'], test_object)

    def test_load_existing_store(self):
        check_name = str(uuid.uuid4())
        test_object = {'test': 42.0}
        store = PersistableStore(check_name, "instanceid")
        store.load_status()
        self.assertEqual(store['test_field'], None)
        store['test_field'] = test_object
        store.commit_status()

        store = PersistableStore(check_name, "instanceid")
        store.load_status()
        self.assertEqual(store['test_field'], test_object)

    def test_clear_store(self):
        check_name = str(uuid.uuid4())
        test_object = {'test': 42.0}
        store = PersistableStore(check_name, "instanceid")
        store.load_status()
        self.assertEqual(store['test_field'], None)
        store['test_field'] = test_object
        store.commit_status()
        store.clear_status()

        store = PersistableStore(check_name, "instanceid")
        store.load_status()
        self.assertEqual(store['test_field'], None)
