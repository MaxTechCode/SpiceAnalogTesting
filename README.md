# SpiceAnalogTesting

This repository holds a python structure which can be used to interface LTSpice via [PyLTSpice](https://pypi.org/project/PyLTSpice/) in order to enable analog test development.

## Foundation of this Project

This project was created as part of a university project at the University of British Columbia (EECE 571I, Prof. André Ivanov) and follows the initial idea of the below mentioned [paper](https://doi.org/10.1109/VTS60656.2024.10538672). The authors introduce a approach for built-in self-test which uses injection points to inject perturbances and observe these through few observation nodes.

## Current State

Currently, a complete object oriented structure is created to allow for quick modification of the netlist in order to inject/eject and activate/deactivate injection points and observers. There is only the capability to pull a node to supply voltage and ground currently available. Also only a observer which inserts an inverter is currently implemented. Additionally a simple transistor fault model consisting of six faults following this [paper](https://doi.org/10.1109/SBCCI55532.2022.9893224) is implemented. For resistors only a short and open fault is present and for capacitors only a short fault can be injected currently.

## Credits 

### On/Off Keying BIST scheme

S. K. Kashyap, C. Raghavendra, S. Natarajan and S. Ozev, "Structural Built In Self Test of Analog Circuits using ON/OFF Keying and Delay Monitors," 2024 IEEE 42nd VLSI Test Symposium (VTS), Tempe, AZ, USA, 2024, pp. 1-7, doi: 10.1109/VTS60656.2024.10538672.

### Transistor Fault Model

M. Saikiran, M. Ganji and D. Chen, "A Time-Efficient Defect Simulation Framework for Analog and Mixed Signal (AMS) Circuits," 2022 35th SBC/SBMicro/IEEE/ACM Symposium on Integrated Circuits and Systems Design (SBCCI), Porto Alegre, Brazil, 2022, pp. 1-6, doi: 10.1109/SBCCI55532.2022.9893224.
