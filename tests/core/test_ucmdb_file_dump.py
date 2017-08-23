from unittest import TestCase

from utils.ucmdb.ucmdb_file_dump import UcmdbDumpStructure, UcmdbFileDump

class TestUcmdbFileDump(TestCase):

    def test_empty_folder(self):
        structure = UcmdbDumpStructure.load("tests/core/fixtures/ucmdb/dump/empty")
        file_dump = UcmdbFileDump(structure)
        self.assertEquals(len(file_dump.get_components()), 0)
        self.assertEquals(len(file_dump.get_relations()), 0)

    def test_load_only_snapshot(self):
        None

    def test_load_only_increments(self):
        None

    def test_load_and_update(self):
        None
