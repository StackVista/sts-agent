# 3rd party
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

class UcmdbCIParser:
    # SAX style parser for UCMDB TQL query result xml
    #
    # <object operation="add" name="business_application" ucmdb_id="dab1c91cdc7a6d808b0642cb02ea22f0" id="UCMDB%0Abusiness_application%0A1%0Ainternal_id%3DSTRING%3Ddab1c91cdc7a6d808b0642cb02ea22f0%0A">
    #   <attribute name="display_label" datatype="STRING">CRMI (MQCODE)</attribute>
    #   <attribute name="name" datatype="STRING">CRMI (MQCODE)</attribute>
    #   <attribute name="global_id" datatype="STRING">dab1c91cdc7a6d808b0642cb02ea22f0</attribute>
    #   <attribute name="root_class" datatype="STRING">business_application</attribute>
    # </object>

    # <link name="usage" operation="add" ucmdb_id="b5ae9a13b50f4c9cee6851afc085497f">
    #   <attribute name="DiscoveryID1">35f8a6275733c84fae827b2e7a3998fd</attribute>
    #   <attribute name="DiscoveryID2">282fbea52182451a03cf7f707ec3a597</attribute>
    #   <attribute name="end1Id">UCMDB%0ARB_ApplicationService%0A1%0Ainternal_id%3DSTRING%3D35f8a6275733c84fae827b2e7a3998fd%0A</attribute>
    #   <attribute name="end2Id">UCMDB%0Abusiness_application%0A1%0Ainternal_id%3DSTRING%3D282fbea52182451a03cf7f707ec3a597%0A</attribute>
    #   <attribute name="display_label" datatype="STRING">Usage</attribute>
    # </link>

    def __init__(self, file):
        self.file = file
        self.components = []
        self.relations = []

    def parse(self):
        tree = ET.iterparse(self.file)
        current_element = dict()
        current_element['data'] = dict()
        for event, elem in tree:
            if event == 'end':
                if elem.tag == 'attribute':
                    if 'name' in elem.attrib:
                        attribute_name = elem.attrib['name']
                        attribute_value = elem.text
                        current_element['data'][attribute_name] = attribute_value
                elif elem.tag == 'object':
                    if 'operation' in elem.attrib and elem.attrib['operation'] == 'add':
                        if 'name' in elem.attrib and 'ucmdb_id' in elem.attrib:
                            current_element['type'] = elem.attrib['name']
                            current_element['external_id'] = elem.attrib['ucmdb_id']
                            self.components.append(current_element)
                    current_element = dict()
                    current_element['data'] = dict()
                elif elem.tag == 'link':
                    if 'operation' in elem.attrib and elem.attrib['operation'] == 'add':
                        if 'name' in elem.attrib and 'ucmdb_id' in elem.attrib:
                            current_element['type'] = elem.attrib['name']
                            current_element['external_id'] = elem.attrib['ucmdb_id']
                            if 'DiscoveryID1' in current_element['data']:
                                current_element['source_id'] = current_element['data']['DiscoveryID1']
                            if 'DiscoveryID2' in current_element['data']:
                                current_element['target_id'] = current_element['data']['DiscoveryID2']
                            self.relations.append(current_element)
                    current_element = dict()
                    current_element['data'] = dict()
            elem.clear()

    def get_components(self):
        return self.components

    def get_relations(self):
        return self.relations
