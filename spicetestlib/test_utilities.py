from PyLTSpice import LTSpiceLogReader, RawRead

from spicetestlib.base import NetList
from spicetestlib.errors import *

NMOS_MODEL = 'BSS123'
PMOS_MODEL = 'BSS84'

# timing for injection pulse (delay, rise time, fall time, duration)
INJECTION_TIMING = "10n 10n 10n 1u"
# trigger time in float
TRIGGER_TIME = 10e-9

class TestUtility:
    """
    General Test Utility which is able to be inserted into a netlist,
    activated, deactivated and ejected from the netlist.
    """

    STATE_NOT_INJECTED = 0
    STATE_INJECTED = 1
    STATE_ACTIVE = 2

    def __init__(self, netlist : NetList):
        self.netlist = netlist
        self._state = TestUtility.STATE_NOT_INJECTED

    def get_state(self) -> int:
        return self._state
    
    def is_injected(self) -> bool:
        return self._state == TestUtility.STATE_INJECTED or self._state == TestUtility.STATE_ACTIVE
    
    def is_active(self) -> bool:
        return self._state == TestUtility.STATE_ACTIVE

    def inject(self) -> None:
        """
        Inject the utility into the netlist. (add transistors, add source, ...)
        Overwrite this in derived classes AND call this at the beginning.
        """
        if self._state != TestUtility.STATE_NOT_INJECTED:
            raise AlreadyInjectedError()
        self._state = TestUtility.STATE_INJECTED

    def activate(self) -> None:
        """
        Activate the utility. (e.g. apply pulse, insert .meas directive, ...)
        Overwrite this in derived classes AND call this at the beginning.
        """
        if self._state == TestUtility.STATE_NOT_INJECTED:
            raise NotInjectedError()
        if self._state == TestUtility.STATE_ACTIVE:
            raise AlreadyActiveError()
        self._state = TestUtility.STATE_ACTIVE

    def deactivate(self) -> None:
        """
        Deactivate the utility. (e.g. remove pulse, remove .meas directive, ...)
        Overwrite this in derived classes AND call this at the beginning.
        """
        if self._state == TestUtility.STATE_NOT_INJECTED:
            raise NotInjectedError()
        if self._state == TestUtility.STATE_INJECTED:
            raise NotActiveError()
        self._state = TestUtility.STATE_INJECTED

    def eject(self) -> None:
        """
        Eject the utility from the netlist. (remove transistors, remove source, ...)
        Overwrite this in derived classes AND call this at the end.
        """
        if self._state == TestUtility.STATE_NOT_INJECTED:
            raise NotInjectedError()
        if self._state == TestUtility.STATE_ACTIVE:
            self.deactivate()
        self._state = TestUtility.STATE_NOT_INJECTED
    
    def str_state(self):
        if self._state == TestUtility.STATE_NOT_INJECTED:
            return f"not injected"
        elif self._state == TestUtility.STATE_INJECTED:
            return f"injected"
        elif self._state == TestUtility.STATE_ACTIVE:
            return f"active"
        else:
            return "unknown state"

    def __str__(self):
        return f"TestUtility ({self.str_state()})"


class Observer(TestUtility):
    """
    An observer is able to observe a certain node in a circuit and
    evaluate whether the results of a certain simulation differ from
    the expected results.
    """

    def __init__(self, netlist : NetList):
        super().__init__(netlist)

    def observe_expected(self, log : LTSpiceLogReader = None, raw : RawRead = None, raw_op : RawRead = None) -> None:
        """
        Observe the expected value of the observer node.
        """
        raise NotImplementedError()
    
    def observe(self, log : LTSpiceLogReader = None, raw : RawRead = None, raw_op : RawRead = None) -> tuple[bool,list[float]]:
        """
        Observe the value of the observer node and compare it against the expected value.
        Returns True if the observed value is as expected, False otherwise. Additionally,
        returns a list of floats representing the observed values.
        """
        raise NotImplementedError()
    
    def __str__(self):
        return f"Observer ({self.str_state()})"


class MeasureObserver(Observer):
    """
    Observer utilizing a .meas directive and categorizes results in low, uncertain and high.
    Note that while effective this does NOT account for
    input impedance contributed by an actual observer.
    """

    RESULT_NAME_POSTFIX = "_OBSERVE"

    LOW_VALUE = -1
    UNCERTAIN_VALUE = 0
    HIGH_VALUE = 1

    def _get_measurement(log : LTSpiceLogReader, variable : str, default : float | None = None) -> float | None:
        try:
            return log[variable.lower()][0]
        except IndexError:
            return default

    def __init__(self, netlist, observer_node, low_threshold : float, high_threshold: float):
        super().__init__(netlist)
        self.meas_node = observer_node
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold
        self.low_result_variable = f"{self.meas_node}{MeasureObserver.RESULT_NAME_POSTFIX}_LOW"
        self.high_result_variable = f"{self.meas_node}{MeasureObserver.RESULT_NAME_POSTFIX}_HIGH"

        # tuple with first entry value and second time from trigger
        # value: -1 = LOW, 0 = MID, 1 = HIGH
        self.expectation = None

    def activate(self):
        super().activate()

        # insert .meas directives
        self.netlist.net.add_instructions(
                # low directives
                f".meas TRAN {self.low_result_variable}_FALL "
                f"FIND V({self.meas_node}) "
                f"WHEN V({self.meas_node})={self.low_threshold} "
                f"FALL=last TD={TRIGGER_TIME:.3e}",
                f".meas TRAN {self.low_result_variable}_RISE "
                f"FIND V({self.meas_node}) "
                f"WHEN V({self.meas_node})={self.low_threshold} "
                f"RISE=last TD={TRIGGER_TIME:.3e}",
                # high directives
                f".meas TRAN {self.high_result_variable}_FALL "
                f"FIND V({self.meas_node}) "
                f"WHEN V({self.meas_node})={self.high_threshold} "
                f"FALL=last TD={TRIGGER_TIME:.3e}",
                f".meas TRAN {self.high_result_variable}_RISE "
                f"FIND V({self.meas_node}) "
                f"WHEN V({self.meas_node})={self.high_threshold} "
                f"RISE=last TD={TRIGGER_TIME:.3e}"
        )

    def deactivate(self):
        super().deactivate()

        # remove both directives
        self.netlist.net.remove_Xinstruction(f"\.meas TRAN {self.meas_node}{MeasureObserver.RESULT_NAME_POSTFIX}.*")

    def _observe(self, log : LTSpiceLogReader = None, raw : RawRead = None, raw_op : RawRead = None) -> tuple[int, float]:
        """
        Sets and returns last_observation
        """

        last_observation = None
        # acquire trigger times
        low_fall = MeasureObserver._get_measurement(log, f"{self.low_result_variable}_FALL_at", -1)
        low_rise = MeasureObserver._get_measurement(log, f"{self.low_result_variable}_RISE_at", -1)
        high_fall = MeasureObserver._get_measurement(log, f"{self.high_result_variable}_FALL_at", -1)
        high_rise = MeasureObserver._get_measurement(log, f"{self.high_result_variable}_RISE_at", -1)

        if low_fall > low_rise:
            # last transition was falling below low threshold
            last_observation = (MeasureObserver.LOW_VALUE, low_fall - TRIGGER_TIME)
        elif high_rise > high_fall:
            # last transition was rising above high threshold
            last_observation = (MeasureObserver.HIGH_VALUE, high_rise - TRIGGER_TIME)
        else:
            # not triggered
            if not raw_op is None:
                # gather initial value from automatic .op simulation
                initial_value = raw_op.get_trace(f'V({self.meas_node})').data[0]
                if initial_value < self.low_threshold:
                    last_observation = (MeasureObserver.LOW_VALUE, -1)
                elif initial_value > self.high_threshold:
                    last_observation = (MeasureObserver.HIGH_VALUE, -1)
                else:
                    last_observation = (MeasureObserver.UNCERTAIN_VALUE, -1)
            # assume uncertain
            else:
                last_observation = (MeasureObserver.UNCERTAIN_VALUE, -1)

        #print(f"  Observer {self.meas_node}: {last_observation[0]} after {last_observation[1]:.3e}")

        return last_observation
    
    def observe_expected(self, log : LTSpiceLogReader = None, raw : RawRead = None, raw_op : RawRead = None):
        self.expectation = self._observe(log, raw, raw_op)

        print(f"  Observer Expectation {self.meas_node}: {self.expectation[0]} after {self.expectation[1]:.3e}")
        
        if self.expectation[0] == MeasureObserver.UNCERTAIN_VALUE:
            print(f"PANIC: {self.meas_node} is expected to be in UNCERTAIN")

    def observe(self, log : LTSpiceLogReader = None, raw : RawRead = None, raw_op : RawRead = None) -> tuple[bool,list[float]]:
        if self.expectation is None:
            raise ObserverExpectationUnknown()

        # for now only value comparison
        observation = self._observe(log, raw, raw_op)
        return (observation[0] == self.expectation[0], [observation[1]-self.expectation[1]])
    
    def __str__(self):
        return f"MeasureObserver @ {self.meas_node} ({self.str_state()})"
    

class InverterObserver(MeasureObserver):
    """
    Simple observer which deploys a inverter and checks
    whether its output is low or high
    """

    LOGIC_MARGIN = 0.1
    NODE_POSTFIX = "_INVERTER"

    def __init__(self, netlist : NetList, observer_node : str):
        super().__init__(
            netlist=netlist, observer_node=f"{observer_node}{InverterObserver.NODE_POSTFIX}",
            low_threshold=netlist.vss + InverterObserver.LOGIC_MARGIN,
            high_threshold=netlist.vdd - InverterObserver.LOGIC_MARGIN
        )
        self.observer_node = observer_node
        self.pmos = None
        self.nmos = None

    def inject(self):
        super().inject()
        # inject pmos
        self.pmos = self.netlist.insert_fet(
            f"{self.observer_node}{InverterObserver.NODE_POSTFIX}", self.observer_node, self.netlist.supply_node,
            PMOS_MODEL
        )
        # inject nmos
        self.nmos = self.netlist.insert_fet(
            f"{self.observer_node}{InverterObserver.NODE_POSTFIX}", self.observer_node, self.netlist.ground_node,
            NMOS_MODEL
        )

    def eject(self):
        # remove both transistors
        self.netlist.remove_component(self.pmos)
        self.netlist.remove_component(self.nmos)
        super().eject()

    def __str__(self):
        return f"InverterObserver @ {self.observer_node} ({self.str_state()})"
    

class InjectionPoint(TestUtility):
    """
    An injection point is a able to inject a perturbation at a certain node
    by pulling it up or down to a certain voltage.
    """

    NMOS_GATE_NODE_POSTFIX = '_INJ_TRIG_DOWN'
    PMOS_GATE_NODE_POSTFIX = '_INJ_TRIG_UP'

    def __init__(self, netlist : NetList, node : str, pull_up : bool):
        super().__init__(netlist)
        self.node = node
        self.pull_up = pull_up

        # attributes for components injected into the netlist
        self.fet = None
        self.source = None

    def inject(self):
        super().inject()
        if self.pull_up:
            # PMOS
            self.source = self.netlist.insert_source(
                f'{self.node}{InjectionPoint.PMOS_GATE_NODE_POSTFIX}', self.netlist.ground_node,
                self.netlist.vdd
            )
            self.fet = self.netlist.insert_fet(
                self.node, f'{self.node}{InjectionPoint.PMOS_GATE_NODE_POSTFIX}', self.netlist.supply_node,
                PMOS_MODEL
            )
        else:
            # NMOS
            self.source = self.netlist.insert_source(
                f'{self.node}{InjectionPoint.NMOS_GATE_NODE_POSTFIX}', self.netlist.ground_node,
                self.netlist.vss
            )
            self.fet = self.netlist.insert_fet(
                self.node, f'{self.node}{InjectionPoint.NMOS_GATE_NODE_POSTFIX}', self.netlist.ground_node,
                NMOS_MODEL
            )

    def activate(self):
        super().activate()
        if self.pull_up:
            self.netlist.set_component_value(self.source, f'PULSE({self.netlist.vdd} {self.netlist.vss} {INJECTION_TIMING})')
        else:
            self.netlist.set_component_value(self.source, f'PULSE({self.netlist.vss} {self.netlist.vdd} {INJECTION_TIMING})')

    def deactivate(self):
        super().deactivate()
        if self.pull_up:
            self.netlist.set_component_value(self.source, self.netlist.vdd)
        else:
            self.netlist.set_component_value(self.source, self.netlist.vss)

    def eject(self):
        self.netlist.remove_component(self.fet)
        self.netlist.remove_component(self.source)
        super().eject()

    def __str__(self):
        if self.pull_up:
            return f"InjectionPoint PullUp @ {self.node} ({self.str_state()})"
        else:
            return f"InjectionPoint PullDown @ {self.node} ({self.str_state()})"
