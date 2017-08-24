import os
import operator
from os.path import isfile, join, getmtime
from utils.ucmdb.ucmdb_parser import UcmdbCIParser

class UcmdbDumpStructure(object):
    FULL_DIRECTORY = "full"
    INCREMENT_DIRECTORY = "increment"

    def __init__(self, snapshot_dates, increment_dates):
        self.snapshot_dates = snapshot_dates
        self.increment_dates = increment_dates

    def has_changes(self, previous_dump):
        diff_snapshot_added = set(self.snapshot_dates.items()) - set(previous_dump.snapshot_dates.items())
        diff_snapshot_removed = set(previous_dump.snapshot_dates.items()) - set(self.snapshot_dates.items())
        diff_increment_added = set(self.increment_dates.items()) - set(previous_dump.increment_dates.items())
        diff_increment_removed = set(previous_dump.increment_dates.items()) - set(self.increment_dates.items())
        return len(diff_snapshot_added) > 0 or len(diff_snapshot_removed) > 0 or len(diff_increment_added) > 0 or len(diff_increment_removed) > 0

    def get_snapshots(self):
        return [key for key, value in sorted(self.snapshot_dates.items(), key=operator.itemgetter(1))]

    def get_increments(self):
        return [key for key, value in sorted(self.increment_dates.items(), key=operator.itemgetter(1))]

    @staticmethod
    def load(root_directory):
        snapshots = dict()
        increments = dict()

        snapshot_dir = os.path.join(root_directory, UcmdbDumpStructure.FULL_DIRECTORY)
        increment_dir = os.path.join(root_directory, UcmdbDumpStructure.INCREMENT_DIRECTORY)

        if os.path.exists(snapshot_dir):
            snapshot_files = [f for f in os.listdir(snapshot_dir) if isfile(join(snapshot_dir, f)) and f.endswith(".xml")]
            for snapshot_file in snapshot_files:
                snapshot_file_path = join(snapshot_dir, snapshot_file)
                snapshots[snapshot_file_path] = int(getmtime(snapshot_file_path))

        if os.path.exists(increment_dir):
            increment_files = [f for f in os.listdir(increment_dir) if isfile(join(increment_dir, f)) and f.endswith(".xml")]
            for increment_file in increment_files:
                increment_file_path = join(increment_dir, increment_file)
                increments[increment_file_path] = int(getmtime(increment_file_path))
        return UcmdbDumpStructure(snapshots, increments)


class UcmdbFileDump(object):
    def __init__(self, structure):
        self.structure = structure
        self.components = dict()
        self.relations = dict()

    def load(self):
        for snapshot in self.structure.get_snapshots():
            parser = UcmdbCIParser(snapshot)
            parser.parse()
            for id, component in parser.get_components().iteritems():
                self.handle_element(self.components, id, component)
            for id, relation in parser.get_relations().iteritems():
                self.handle_element(self.relations, id, relation)

        for increment in self.structure.get_increments():
            parser = UcmdbCIParser(increment)
            parser.parse()
            for id, component in parser.get_components().iteritems():
                self.handle_element(self.components, id, component)
            for id, relation in parser.get_relations().iteritems():
                self.handle_element(self.relations, id, relation)

    def handle_element(self, final_elements, id, element):
        if element['operation'] == "add" or element['operation'] == "update":
            final_elements[id] = element
        elif element['operation'] == "delete":
            if id in final_elements:
                del final_elements[id]
        else:
            raise Exception("Unknown operation %s" % element['operation'])

    def get_components(self):
        return self.components

    def get_relations(self):
        return self.relations
