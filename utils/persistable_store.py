
from checks.check_status import CheckData

class PersistableStore(object):
    def __init__(self, persistable_check_name, instance_id):
        self.persistable_check_name = persistable_check_name
        self.instance_id = instance_id
        self.status = None
        self.load_status()

    def clear_status(self):
        CheckData.remove_latest_status(self.persistable_check_name)
        self.load_status()

    def load_status(self):
        self.status = CheckData.load_latest_status(self.persistable_check_name)
        if self.status is None:
            self.status = CheckData()

    def commit_status(self):
        self.status.persist(self.persistable_check_name)

    def __setitem__(self, key, item):
        self.status.data[key] = item

    def __getitem__(self, key):
        return self.status.data.get(key, None)
