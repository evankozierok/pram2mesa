# pram2mesa
Tools for translating [PyPRAM](https://momacs.github.io/pram/index.html)'s Probabilistic Relational Agent-Based Models to [Mesa](https://github.com/projectmesa/mesa)'s Agent-Based Models

pram2mesa is a tool allowing a Probabilistic Relational Agent-Based Model (PRAM) to be translated into an Agent-Based Model (ABM). There are a few tradeoffs here:
* PRAMs work at a group level, while ABMs work at an individual agent level
* PRAMs have a more formal grammar, while ABMs are open-ended
* PRAMs are often much faster than ABMs, especially on very large populations

Core to this project, however, is a more theoretical purpose - demonstrating the interconnectedness of the two frameworks. While they are not the same, they are similar in many ways, allowing a tool like pram2mesa to exist.

## Installation
### Dependencies (For Translation)
* [PyPRAM](https://momacs.github.io/pram/index.html) (must be installed separately; see below)
* [astor](https://astor.readthedocs.io/en/latest/)
* [autopep8](https://pypi.org/project/autopep8/)
* [dill](https://pypi.org/project/dill/)
* [iteround](https://pypi.org/project/iteround/)
### Dependencies (For Running Translated ABMs)
* [Mesa](https://mesa.readthedocs.io/en/master/)
* [networkx](https://networkx.github.io/) (also a dependency of Mesa)
* [dill](https://pypi.org/project/dill/)
### Setup
To install pram2mesa and its dependencies (except PyPRAM) simply use pip:
```
pip install pram2mesa
```
PyPRAM must be installed separately. See PyPRAM's [Setup](https://github.com/momacs/pram#setup) for details or just use:
```
pip install git+https://github.com/momacs/pram.git
```
Bear in mind that any computer running a translated ABM will (of course) need Mesa, but also dill. 

## Usage
### Translating the PRAM
To translate a PRAM, first create the PRAM in a Python file or interpreter. Make sure that you **do not run** the PRAM. If you do, your new ABM will be setup with the ending configuration of the PRAM, not the beginning.
```python
my_pram = (Simulation().
    add(...)
)
```
Ensure you have imported pram2mesa:
```python
from pram2mesa import pram2mesa
```
Then simply supply your PRAM simulation and a nice file-safe name for your new files:
```python
pram2mesa(my_pram, 'MyNewABM')
```
By default, pram2mesa will automatically clean the outputted Python files in an attempt to make them PEP8-compliant. To disable this, simply set `autopep` to `False`:
```python
pram2mesa(my_pram, 'MyNewABM', autopep=False)
```
This will create a new directory called `MyNewABM` (or `MyNewABM_1` if `MyNewABM` already exists; or `MyNewABM_2` etc...) containing two Python files and three JSON files:
```
MyNewABM
+-- MyNewABMAgent.py
+-- MyNewABMGroups.json
+-- MyNewABMModel.py
+-- MyNewABMRules.json
+-- MyNewABMSites.json
```
### Running the ABM
Once you've created the files, you can instantiate your new model and run it as you normally would in Mesa. Make sure to keep all the files together; the Agent and Model classes need the JSON files during their initialization.
```python
from MyNewABMModel import MyNewABMModel

model = MyNewABMModel()
```
You will want to be sure to add a datacollector to the model to measure and graph outputs.
```python
model.datacollector = DataCollector(...)
```
The Models that pram2mesa generates do not override `run_model()`. If you want, you can override it yourself in the Model class, or just use `step()`:
```python
for i in range(num_runs):
    model.step()
```
Then, you can extract graphs or other data from your datacollector. If you are unfamiliar with Mesa, you can look at their [documentation](https://mesa.readthedocs.io/en/master/) which includes some well-written tutorials. The files named `run_abm.py` in each folder of this project's `Samples` directory may also be useful.

## Acknowledgements
Thank you to my research mentors, Drs. [Paul Cohen](http://paulrcohen.github.io/) and [Tomek Loboda](https://tomekloboda.net/#p=0), for their support on this project.

This project is supported by the Brackenridge Fellowship at the [University of Pittsburgh Honors College](https://www.honorscollege.pitt.edu/).

## License
This project is licensed under the [MIT License](https://github.com/evankozierok/pram2mesa/blob/master/LICENSE).
