
class UcmdbComponentTrees(object):
    def __init__(self, components_dict, relations_dict, tree_parent_to_label = dict()):
        self.components = components_dict
        self.relations = relations_dict
        self.tree_parent_to_label = tree_parent_to_label
        self.component_id_to_label = dict()
        self.graph = dict()

    def label_trees(self):
        self._build_graph()
        self._find_root_ids()
        self._label_trees()

    def _build_graph(self):
        for id, relation in self.relations.items():
            if relation['operation'] == 'delete':
                continue
            source_id = relation['source_id']
            if source_id not in self.graph.keys():
                self.graph[source_id] = [relation]
            else:
                self.graph[source_id].append(relation)

    def _find_root_ids(self):
        for id, component in self.components.items():
            component_name = component['data'].get("name", None)
            if component['operation'] != 'delete' and component_name is not None and component_name in self.tree_parent_to_label.keys():
                self.component_id_to_label[component['ucmdb_id']] = self.tree_parent_to_label[component_name]

    def _label_trees(self):
        for id, label in self.component_id_to_label.items():
            self._label_from_root(id, label)

    def _label_from_root(self, root_id, label):
        root = self.components[root_id]
        visited = set()
        queue = [root]

        self._bfs(queue, visited, lambda comp: self._append_label(comp['data'], label))

    def _bfs(self, queue, visited, label_func):
        while len(queue) > 0:
            current = queue[0]
            queue = queue[1:] if len(queue) > 1 else []
            visited.add(current['ucmdb_id'])

            if current['operation'] == 'deleted':
                continue

            label_func(current)

            # there are no relations
            if self.graph.get(current['ucmdb_id'], None) is None:
                continue

            for outgoing_relation in self.graph[current['ucmdb_id']]:
                target_id = outgoing_relation['target_id']
                if target_id not in visited:
                    adjacent_comp = self.components.get(target_id, None)
                    if adjacent_comp is not None:
                        queue.append(adjacent_comp)

    def _append_label(self, data, label):
        data['label.tree'] = label

    def get_components(self):
        return self.components

    def get_relations(self):
        return self.relations
