from PyLTSpice import SpiceEditor
from spicelib.editor.base_editor import Component

class NetList:

    def __init__(self, netlist_path : str, *, ground_node : str = '0', supply_node : str = 'VDD', vdd : float = 3.3, vss : float = 0):
        self.net = SpiceEditor(netlist_path)

        # store the ground and supply nodes
        self.ground_node = ground_node
        self.supply_node = supply_node
        self.vdd = vdd
        self.vss = vss

        # counters to ensure unique names
        self._fet_descriptor_index = -1
        self._source_descriptor_index = -1
        self._resistor_descriptor_index = -1

    def get_next_fet_descriptor_index(self):
        if self._fet_descriptor_index == -1:
            self._fet_descriptor_index = 1
            while f'M{self._fet_descriptor_index}' in self.net.get_components():
                self._fet_descriptor_index += 1
        else:
            self._fet_descriptor_index += 1
        return self._fet_descriptor_index

    def get_next_source_descriptor_index(self):
        if self._source_descriptor_index == -1:
            self._source_descriptor_index = 1
            while f'V{self._source_descriptor_index}' in self.net.get_components():
                self._source_descriptor_index += 1
        else:
            self._source_descriptor_index += 1
        return self._source_descriptor_index
    
    def get_next_resistor_descriptor_index(self):
        if self._resistor_descriptor_index == -1:
            self._resistor_descriptor_index = 1
            while f'R{self._resistor_descriptor_index}' in self.net.get_components():
                self._resistor_descriptor_index += 1
        else:
            self._resistor_descriptor_index += 1
        return self._resistor_descriptor_index

    def insert_fet(self, drain_node : str, gate_node : str, source_node : str, model : str) -> str:
        """
        Insert a FET into the netlist
        Returns the assigned reference descriptor of the FET
        """
        fet = Component(None, "")
        fet.reference = f'M{self.get_next_fet_descriptor_index()}'
        fet.ports = [drain_node, gate_node, source_node, source_node]
        fet.attributes['model'] = model
        self.net.add_component(fet)
        return fet.reference
    
    def update_fet_ports(self, reference : str, drain_node : str, gate_node : str, source_node : str, bulk_node : str):
        """
        Update the ports of a FET in the netlist
        """
        if not reference.startswith('M'):
            raise ValueError("Reference must be a FET")
        
        old_fet = self.net.get_component(reference)

        # create deep copy of the old fet and set new ports
        new_fet = Component(None, "")
        new_fet.reference = old_fet.reference
        new_fet.attributes['model'] = old_fet.attributes['value']
        new_fet.ports = [drain_node, gate_node, source_node, bulk_node]

        # replace in netlist
        self.net.remove_component(reference)
        self.net.add_component(new_fet)

    def insert_source(self, plus_node : str, minus_node : str, value : str) -> str:
        """
        Insert a voltage source into the netlist
        Returns the assigned reference descriptor of the source
        """
        source = Component(None, "")
        source.reference = f'V{self.get_next_source_descriptor_index()}'
        source.ports = [plus_node, minus_node]
        source.attributes['model'] = value
        self.net.add_component(source)
        return source.reference
    
    def insert_resistor(self, node1 : str, node2 : str, value : str) -> str:
        """
        Insert a resistor into the netlist
        Returns the assigned reference descriptor of the resistor
        """
        resistor = Component(None, "")
        resistor.reference = f'R{self.get_next_resistor_descriptor_index()}'
        resistor.ports = [node1, node2]
        resistor.attributes['model'] = value
        self.net.add_component(resistor)
        return resistor.reference

    def remove_component(self, reference : str):
        """
        Remove a component from the netlist
        """
        self.net.remove_component(reference)

    def set_component_value(self, reference : str, value : str):
        """
        Set the value of a component in the netlist
        """
        self.net.set_component_value(reference, value)
