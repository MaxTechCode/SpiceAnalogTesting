from spicetestlib.base import NetList
from spicetestlib.errors import *

class Fault:
    """
    General Fault which is able to be inserted into a netlist,
    and ejected from the netlist.
    """

    STATE_NOT_INJECTED = 0
    STATE_INJECTED = 1

    def __init__(self, netlist : NetList, component : str):
        self.netlist = netlist
        self.component = component
        self._state = Fault.STATE_NOT_INJECTED

    def get_state(self) -> int:
        return self._state
    
    def is_injected(self) -> bool:
        return self._state == Fault.STATE_INJECTED

    def inject(self) -> None:
        """
        Inject the fault into the netlist. (add resistors, bridge nodes, ...)
        Overwrite this in derived classes AND call this at the beginning.
        """
        if self._state != Fault.STATE_NOT_INJECTED:
            raise AlreadyInjectedError()
        self._state = Fault.STATE_INJECTED



    def eject(self) -> None:
        """
        Eject the fault from the netlist. (remove resistor, recreate nodes, ...)
        Overwrite this in derived classes AND call this at the end.
        """
        if self._state == Fault.STATE_NOT_INJECTED:
            raise NotInjectedError()
        self._state = Fault.STATE_NOT_INJECTED
    
    def str_state(self):
        if self._state == Fault.STATE_NOT_INJECTED:
            return f"not injected"
        elif self._state == Fault.STATE_INJECTED:
            return f"injected"
        else:
            return "unknown state"

    def __str__(self):
        return f"Fault @ {self.component} ({self.str_state()})"


class DrainOpenFault(Fault):
    """
    Represents a drain open fault which can be injected into a circuit.
    """

    OPEN_RESISTANCE = 1e11
    
    def __init__(self, netlist, component):
        super().__init__(netlist, component)

        if not component.startswith('M'):
            raise FaultDoesNotSupportComponent()

        self.open_resistor = None
        self.fault_free_ports = self.netlist.net.get_component_nodes(component)

    def inject(self):
        super().inject()
        new_ports = self.fault_free_ports.copy()
        new_ports[0] = f'{new_ports[0]}_{self.component}_open'
        self.netlist.update_fet_ports(self.component, *new_ports)
        self.open_resistor = self.netlist.insert_resistor(
            new_ports[0], self.fault_free_ports[0], DrainOpenFault.OPEN_RESISTANCE
        )

    def eject(self):
        self.netlist.update_fet_ports(self.component, *self.fault_free_ports)
        self.netlist.remove_component(self.open_resistor)
        super().eject()

    def __str__(self):
        return f"DrainOpenFault @ {self.component} ({self.str_state()})"
    
class SourceOpenFault(Fault):
    """
    Represents a source open fault which can be injected into a circuit.
    """

    OPEN_RESISTANCE = 1e11
    
    def __init__(self, netlist, component):
        super().__init__(netlist, component)

        if not component.startswith('M'):
            raise FaultDoesNotSupportComponent()

        self.open_resistor = None
        self.fault_free_ports = self.netlist.net.get_component_nodes(component)

    def inject(self):
        super().inject()
        new_ports = self.fault_free_ports.copy()
        new_ports[2] = f'{new_ports[2]}_{self.component}_open'
        new_ports[3] = new_ports[2]
        self.netlist.update_fet_ports(self.component, *new_ports)
        self.open_resistor = self.netlist.insert_resistor(
            new_ports[2], self.fault_free_ports[2], SourceOpenFault.OPEN_RESISTANCE
        )

    def eject(self):
        self.netlist.update_fet_ports(self.component, *self.fault_free_ports)
        self.netlist.remove_component(self.open_resistor)
        super().eject()

    def __str__(self):
        return f"SourceOpenFault @ {self.component} ({self.str_state()})"

class GateOpenFault(Fault):
    """
    Represents a gate open fault which can be injected into a circuit.
    """

    COUPLING_RESISTANCE = 5e11
    GATE_RESISTANCE = 1e12

    def __init__(self, netlist, component):
        super().__init__(netlist, component)

        if not component.startswith('M'):
            raise FaultDoesNotSupportComponent()

        self.open_resistor = None
        self.drain_coupling_resistor = None
        self.source_coupling_resistor = None
        self.fault_free_ports = self.netlist.net.get_component_nodes(component)

    def inject(self):
        super().inject()
        new_ports = self.fault_free_ports.copy()
        new_ports[1] = f'{new_ports[1]}_{self.component}_open'
        couple_port = f'{new_ports[1]}_couple'
        self.netlist.update_fet_ports(self.component, *new_ports)
        self.open_resistor = self.netlist.insert_resistor(
            new_ports[1], couple_port, GateOpenFault.GATE_RESISTANCE
        )
        self.drain_coupling_resistor = self.netlist.insert_resistor(
            new_ports[0], couple_port, GateOpenFault.COUPLING_RESISTANCE
        )
        self.source_coupling_resistor = self.netlist.insert_resistor(
            new_ports[2], couple_port, GateOpenFault.COUPLING_RESISTANCE
        )

    def eject(self):
        self.netlist.update_fet_ports(self.component, *self.fault_free_ports)
        self.netlist.remove_component(self.open_resistor)
        self.netlist.remove_component(self.drain_coupling_resistor)
        self.netlist.remove_component(self.source_coupling_resistor)
        super().eject()
    
    def __str__(self):
        return f"GateOpenFault @ {self.component} ({self.str_state()})"

class GateDrainShort(Fault):
    """
    Represents a gate-drain short fault which can be injected into a circuit.
    """

    SHORT_RESISTANCE = 1

    def __init__(self, netlist, component):
        super().__init__(netlist, component)

        if not component.startswith('M'):
            raise FaultDoesNotSupportComponent()

        self.short_resistor = None
        self.fault_free_ports = self.netlist.net.get_component_nodes(component)

    def inject(self):
        super().inject()
        self.short_resistor = self.netlist.insert_resistor(
            self.fault_free_ports[1], self.fault_free_ports[0], GateDrainShort.SHORT_RESISTANCE
        )

    def eject(self):
        self.netlist.remove_component(self.short_resistor)
        super().eject()

    def __str__(self):
        return f"GateDrainShort @ {self.component} ({self.str_state()})"

class GateSourceShort(Fault):
    """
    Represents a gate-source short fault which can be injected into a circuit.
    """

    SHORT_RESISTANCE = 1

    def __init__(self, netlist, component):
        super().__init__(netlist, component)

        if not component.startswith('M'):
            raise FaultDoesNotSupportComponent()

        self.short_resistor = None
        self.fault_free_ports = self.netlist.net.get_component_nodes(component)

    def inject(self):
        super().inject()
        self.short_resistor = self.netlist.insert_resistor(
            self.fault_free_ports[1], self.fault_free_ports[2], GateSourceShort.SHORT_RESISTANCE
        )

    def eject(self):
        self.netlist.remove_component(self.short_resistor)
        super().eject()
    
    def __str__(self):
        return f"GateSourceShort @ {self.component} ({self.str_state()})"

class DrainSourceShort(Fault):
    """
    Represents a drain-source short fault which can be injected into a circuit.
    """

    SHORT_RESISTANCE = 1

    def __init__(self, netlist, component):
        super().__init__(netlist, component)

        if not component.startswith('M'):
            raise FaultDoesNotSupportComponent()

        self.short_resistor = None
        self.fault_free_ports = self.netlist.net.get_component_nodes(component)

    def inject(self):
        super().inject()
        self.short_resistor = self.netlist.insert_resistor(
            self.fault_free_ports[0], self.fault_free_ports[2], DrainSourceShort.SHORT_RESISTANCE
        )

    def eject(self):
        self.netlist.remove_component(self.short_resistor)
        super().eject()
    
    def __str__(self):
        return f"DrainSourceShort @ {self.component} ({self.str_state()})"

def fet_fault_factory(netlist : NetList, component : str) -> list[Fault]:
    """
    Creates all six faults for a given fet component.
    """
    return [
        DrainOpenFault(netlist, component),
        SourceOpenFault(netlist, component),
        GateOpenFault(netlist, component),
        GateDrainShort(netlist, component),
        GateSourceShort(netlist, component),
        DrainSourceShort(netlist, component)
    ]

class ResistorOpen(Fault):
    """
    Represents a resistor open fault which can be injected into a circuit.
    """

    OPEN_RESISTANCE = 1e11

    def __init__(self, netlist, component):
        super().__init__(netlist, component)

        if not component.startswith('R'):
            raise FaultDoesNotSupportComponent()

        self.fault_free_value = self.netlist.net.get_component_value(component)

    def inject(self):
        super().inject()
        self.netlist.net.set_component_value(self.component, ResistorOpen.OPEN_RESISTANCE)

    def eject(self):
        self.netlist.net.set_component_value(self.component, self.fault_free_value)
        super().eject()
    
    def __str__(self):
        return f"ResistorOpen @ {self.component} ({self.str_state()})"
    
class ResistorShort(Fault):
    """
    Represents a resistor short fault which can be injected into a circuit.
    """

    SHORT_RESISTANCE = 1

    def __init__(self, netlist, component):
        super().__init__(netlist, component)

        if not component.startswith('R'):
            raise FaultDoesNotSupportComponent()
        
        self.fault_free_value = self.netlist.net.get_component_value(component)

    def inject(self):
        super().inject()
        self.netlist.net.set_component_value(self.component, ResistorShort.SHORT_RESISTANCE)

    def eject(self):
        self.netlist.net.set_component_value(self.component, self.fault_free_value)
        super().eject()
    
    def __str__(self):
        return f"ResistorShort @ {self.component} ({self.str_state()})"

def resistor_fault_factory(netlist : NetList, component : str) -> list[Fault]:
    """
    Creates both faults (open and short) for a given resistor component.
    """
    return [
        ResistorOpen(netlist, component),
        ResistorShort(netlist, component)
    ]

class CapacitorShort(Fault):
    """
    Capacitor short fault which can be injected into a circuit.
    """

    SHORT_RESISTANCE = 1

    def __init__(self, netlist, component):
        super().__init__(netlist, component)

        if not component.startswith('C'):
            raise FaultDoesNotSupportComponent()

        self.short_resistor = None
        self.fault_free_ports = self.netlist.net.get_component_nodes(component)

    def inject(self):
        super().inject()
        self.short_resistor = self.netlist.insert_resistor(
            self.fault_free_ports[0], self.fault_free_ports[1], CapacitorShort.SHORT_RESISTANCE
        )

    def eject(self):
        self.netlist.remove_component(self.short_resistor)
        super().eject()
    
    def __str__(self):
        return f"CapacitorShort @ {self.component} ({self.str_state()})"

def capacitor_fault_factory(netlist : NetList, component : str) -> list[Fault]:
    """
    Creates a short fault for a given capacitor component.
    """
    return [CapacitorShort(netlist, component)]
