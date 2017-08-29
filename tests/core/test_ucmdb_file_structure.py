from unittest import TestCase

import tempfile
import os
import time
from utils.ucmdb.ucmdb_file_dump import UcmdbDumpStructure

class TestUcmdbDumpStructure(TestCase):

    def test_empty_folder(self):
        structure = UcmdbDumpStructure.load("tests/core/fixtures/ucmdb/dump/empty")
        snapshots = structure.get_snapshots()
        increments = structure.get_increments()

        self.assertEquals(len(snapshots), 0)
        self.assertEquals(len(increments), 0)

    def test_one_snapshot_one_increment(self):
        structure = UcmdbDumpStructure.load("tests/core/fixtures/ucmdb/dump/one")
        snapshots = structure.get_snapshots()
        increments = structure.get_increments()

        self.assertEquals(len(snapshots), 1)
        self.assertEquals(len(increments), 1)

    def test_several_files(self):
        tmp_dump_root = tempfile.mkdtemp()
        tmp_full_dir = os.path.join(tmp_dump_root, UcmdbDumpStructure.FULL_DIRECTORY)
        tmp_increment_dir = os.path.join(tmp_dump_root, UcmdbDumpStructure.INCREMENT_DIRECTORY)
        os.mkdir(tmp_full_dir)
        os.mkdir(tmp_increment_dir)
        now = time.time()
        self.make_file(os.path.join(tmp_full_dir, "3.xml"), now + 1)
        self.make_file(os.path.join(tmp_full_dir, "2.xml"), now + 2)
        self.make_file(os.path.join(tmp_full_dir, "1.xml"), now + 3)

        self.make_file(os.path.join(tmp_increment_dir, "3.xml"), now + 1)
        self.make_file(os.path.join(tmp_increment_dir, "2.xml"), now + 2)
        self.make_file(os.path.join(tmp_increment_dir, "1.xml"), now + 3)

        structure = UcmdbDumpStructure.load(tmp_dump_root)
        snapshots = structure.get_snapshots()
        increments = structure.get_increments()

        self.assertEquals(len(snapshots), 3)
        self.assertEquals(snapshots, [
            os.path.join(tmp_full_dir,"3.xml"),
            os.path.join(tmp_full_dir,"2.xml"),
            os.path.join(tmp_full_dir,"1.xml")])
        self.assertEquals(len(increments), 3)
        self.assertEquals(increments, [
            os.path.join(tmp_increment_dir,"3.xml"),
            os.path.join(tmp_increment_dir,"2.xml"),
            os.path.join(tmp_increment_dir,"1.xml")])

    def make_file(self, path, modification_time):
        file = open(path, "w")
        file.write("placeholder")
        file.close()
        os.utime(path, (modification_time, modification_time))

    def test_has_changes_new_file(self):
        old = UcmdbDumpStructure({"snapshot1":1}, {"increment1":1})
        new = UcmdbDumpStructure({"snapshot1":1, "snapshot2":2}, {"increment1":1})

        self.assertFalse(old.has_changes(old))
        self.assertFalse(new.has_changes(new))
        self.assertTrue(new.has_changes(old))

        old = UcmdbDumpStructure({"snapshot1":1}, {"increment1":1})
        new = UcmdbDumpStructure({"snapshot1":1}, {"increment1":1,"increment2":2})

        self.assertFalse(old.has_changes(old))
        self.assertFalse(new.has_changes(new))
        self.assertTrue(new.has_changes(old))

    def test_has_changes_modification_timechanged(self):
        old = UcmdbDumpStructure({"snapshot1":1, "snapshot2":2}, {"increment1":1})
        new = UcmdbDumpStructure({"snapshot1":1, "snapshot2":3}, {"increment1":1})

        self.assertFalse(old.has_changes(old))
        self.assertFalse(new.has_changes(new))
        self.assertTrue(new.has_changes(old))

        old = UcmdbDumpStructure({"snapshot1":1}, {"increment1":1,"increment2":2})
        new = UcmdbDumpStructure({"snapshot1":1}, {"increment1":1,"increment2":3})

        self.assertFalse(old.has_changes(old))
        self.assertFalse(new.has_changes(new))
        self.assertTrue(new.has_changes(old))

    def test_has_changes_delete_file(self):
        old = UcmdbDumpStructure({"snapshot1":1, "snapshot2":2}, {"increment1":1})
        new = UcmdbDumpStructure({"snapshot1":1}, {"increment1":1})

        self.assertFalse(old.has_changes(old))
        self.assertFalse(new.has_changes(new))
        self.assertTrue(new.has_changes(old))

        old = UcmdbDumpStructure({"snapshot1":1}, {"increment1":1,"increment2":2})
        new = UcmdbDumpStructure({"snapshot1":1}, {"increment1":1})

        self.assertFalse(old.has_changes(old))
        self.assertFalse(new.has_changes(new))
        self.assertTrue(new.has_changes(old))
