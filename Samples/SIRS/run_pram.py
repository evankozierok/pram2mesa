"""
Original PRAM Simulation from:
    pram/src/sim/04-flu-prog-01/sim.py
"""


from pram.data        import ProbePersistenceDB, ProbeMsgMode, GroupSizeProbe
from pram.entity      import Group, GroupQry, GroupSplitSpec
from pram.model.model import MCSolver
from pram.model.epi   import SIRSModel
from pram.sim         import Simulation

import matplotlib.pyplot as plt
import time

# ----------------------------------------------------------------------------------------------------------------------
sir_probe = GroupSizeProbe.by_attr('flu', 'flu', ['s', 'i', 'r'], persistence=ProbePersistenceDB(), msg_mode=ProbeMsgMode.DISP)

s = (Simulation().
    add_probe(sir_probe).
    add_rule(SIRSModel('flu', beta=0.05, gamma=0.50, alpha=0.10, solver=MCSolver())).
    add_group(Group(m=1000, attr={ 'flu': 's' }))
)

runs = 48

t0 = time.time()
s.run(runs)
time_elapsed = time.time() - t0
print(f'Time elapsed in {runs} runs: {time_elapsed} seconds')

series = [
    { 'var': 'p0', 'lw': 2, 'linestyle': '-',  'marker': '', 'color': 'blue',   'markersize': 0, 'lbl': 'Susceptible' },
    { 'var': 'p1', 'lw': 2, 'linestyle': '-', 'marker': '', 'color': 'orange', 'markersize': 0, 'lbl': 'Infected' },
    { 'var': 'p2', 'lw': 2, 'linestyle': '-',  'marker': '', 'color': 'green',   'markersize': 0, 'lbl': 'Recovered' },
]

fig = sir_probe.plot(series, figsize=(8, 6))
fig.suptitle(f'SIRS PRAM Model - {runs} iterations', y=0.95)
fig.savefig("SIRS_PRAM_out")
