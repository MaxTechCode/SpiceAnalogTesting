from PyLTSpice import SimRunner, LTspice, LTSpiceLogReader, RawRead
import os
from spicetestlib.base import NetList
from spicetestlib.test_utilities import Observer

class LTSpiceSimulator:

    def __init__(self, output_folder, simulator = LTspice):
        self.runner = SimRunner(output_folder=output_folder, simulator=simulator)
        self.output_folder = output_folder

    def run_now(self, netlist : NetList, simulation_name : str) -> tuple[LTSpiceLogReader, RawRead, RawRead]:
        raw, log = self.runner.run_now(
            netlist.net,
            run_filename=os.path.join(self.output_folder,simulation_name)
        )
        if os.path.exists(raw.with_suffix('.op.raw')):
            raw_op = RawRead(raw.with_suffix('.op.raw'))
        else:
            raw_op = None
        raw = RawRead(raw)
        log = LTSpiceLogReader(log)
        return (log, raw, raw_op)

    def run_now_n_eval(self, netlist : NetList, simulation_name : str, observers : list[Observer]) -> tuple[list[bool],list[list[float]]]:
        """
        Runs the simulation and returns a list of booleans representing the results of the observers and
        a list of lists of floats representing the results of the observers.
        """
        log, raw, raw_op = self.run_now(netlist, simulation_name)

        result_bool = []
        result_values = []
        for obs in observers:
            observation = obs.observe(log,raw,raw_op)
            result_bool.append(observation[0])
            result_values.append(observation[1])

        del log
        del raw
        del raw_op

        return (result_bool, result_values)
