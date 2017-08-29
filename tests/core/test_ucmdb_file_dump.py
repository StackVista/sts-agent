from unittest import TestCase

from utils.ucmdb.ucmdb_file_dump import UcmdbDumpStructure, UcmdbFileDump

class TestUcmdbFileDump(TestCase):

    def test_empty_folder(self):
        structure = UcmdbDumpStructure.load("tests/core/fixtures/ucmdb/dump/empty")
        file_dump = UcmdbFileDump(structure)
        file_dump.load()
        self.assertEquals(len(file_dump.get_components()), 0)
        self.assertEquals(len(file_dump.get_relations()), 0)

    def test_load_only_snapshot(self):
        structure = UcmdbDumpStructure.load("tests/core/fixtures/ucmdb/dump/only_snapshot")
        file_dump = UcmdbFileDump(structure)
        file_dump.load()
        self.assertEquals(len(file_dump.get_components()), 2)
        self.assertEquals(file_dump.get_components().keys(), ['dab1c91cdc7a6d808b0642cb02ea22f0', 'ba21d9dfb1c2ebf4ee951589a3b4ec62'])
        self.assertEquals(file_dump.get_relations().keys(), ['a9247f4296601c507064ae599bec177e'])

    def test_load_only_increments(self):
        structure = UcmdbDumpStructure.load("tests/core/fixtures/ucmdb/dump/only_increments")
        file_dump = UcmdbFileDump(structure)
        file_dump.load()
        self.assertEquals(len(file_dump.get_components()), 2)
        self.assertEquals(file_dump.get_components().keys(), ['dab1c91cdc7a6d808b0642cb02ea22f0', 'ba21d9dfb1c2ebf4ee951589a3b4ec62'])
        self.assertEquals(file_dump.get_relations().keys(), ['a9247f4296601c507064ae599bec177e'])

    def test_load_and_update(self):
        structure = UcmdbDumpStructure.load("tests/core/fixtures/ucmdb/dump/increment_updates_snapshots")
        file_dump = UcmdbFileDump(structure)
        file_dump.load()
        self.assertEquals(len(file_dump.get_components()), 3)
        self.assertEquals(len(file_dump.get_relations()), 1)
        self.assertEquals(file_dump.get_components().keys(), ['ba21d9dfb1c2ebf4ee951589a3b4ec63', 'dab1c91cdc7a6d808b0642cb02ea22f0', 'dab1c91cdc7a6d808b0642cb02ea22f1'])
        self.assertEquals(file_dump.get_relations().keys(), ['a9247f4296601c507064ae599bec177e'])

        self.assertEquals(file_dump.get_components()['ba21d9dfb1c2ebf4ee951589a3b4ec63']['data']['display_label'], 'UPDATED')
        self.assertEquals(file_dump.get_relations()['a9247f4296601c507064ae599bec177e']['data']['display_label'], 'UPDATED')

    def test_load_exclude_types(self):
        structure = UcmdbDumpStructure.load("tests/core/fixtures/ucmdb/dump/exclude_types")
        file_dump = UcmdbFileDump(structure)
        file_dump.load(set(["to_be_excluded", "business_application"]))
        self.assertEquals(len(file_dump.get_components()), 0)
        self.assertEquals(file_dump.get_components().keys(), [])
        self.assertEquals(file_dump.get_relations().keys(), [])
