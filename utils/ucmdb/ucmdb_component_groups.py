
from python_algorithms.basic.union_find import UF

class UcmdbComponentGroups(object):
    def __init__(self, components_dict, relations_dict, component_name_to_label = dict(), label_min_group_size=1):
        self.components = components_dict
        self.relations = relations_dict
        self.component_name_to_label = component_name_to_label
        self.label_min_group_size = label_min_group_size
        self.group_counts = dict()
        self.component_id_to_label = dict()
        self.component_number = dict()
        counter = 0
        for id, component in self.components.items():
            if component["operation"] == "delete" or id in self.component_number.keys():
                continue
            self.component_number[id] = counter
            component_name = component['data'].get("name", None)
            if component_name in self.component_name_to_label.keys():
                self.component_id_to_label[id] = self.component_name_to_label[component_name]
            counter += 1
        self.unionfind = UF(counter)

    def label_groups(self):
        self._union_groups()
        self._calculate_group_counts()
        self._label_components()

    def _union_groups(self):
        for id, relation in self.relations.items():
            if 'source_id' in relation and 'target_id' in relation:
                source_number = self.component_number.get(relation['source_id'], None)
                target_number = self.component_number.get(relation['target_id'], None)
                if source_number is not None and target_number is not None and not self.unionfind.connected(source_number, target_number):
                    self.unionfind.union(source_number, target_number)

    def _calculate_group_counts(self):
        for id, component in self.components.items():
            component_number = self.component_number.get(id, None)
            if component_number is None:
                continue
            group_id = self.unionfind.find(component_number)
            if group_id in self.group_counts.keys():
                self.group_counts[group_id] += 1
            else:
                self.group_counts[group_id] = 1

    def _label_components(self):
        group_number_to_label = dict()
        for id, label in self.component_id_to_label.items():
            component_number = self.component_number[id]
            group = self.unionfind.find(component_number)
            group_number_to_label[group] = label

        for id, component in self.components.items():
            component_number = self.component_number.get(id, None)
            if component_number is None:
                continue
            group_id = self.unionfind.find(component_number)
            label = group_number_to_label.get(group_id, None)
            if label is None:
                group_size = self.group_counts.get(group_id, None)
                if group_size is not None and group_size >= self.label_min_group_size:
                    self._append_label(component['data'], "group_of_size_%s" % group_size)
            else:
                self._append_label(component['data'], label)

    def _append_label(self, data, label):
        data['label.connected_group'] = label

    def get_components(self):
        return self.components

    def get_relations(self):
        return self.relations
