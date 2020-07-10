"""
Original PRAM Simulation from:
    pram/src/sim/09-segregation/sim.py
"""

import math
import random
import os

from scipy.stats import poisson

from pram.data   import GroupSizeProbe, ProbeMsgMode, ProbePersistenceDB
from pram.entity import Group, GroupDBRelSpec, GroupQry, GroupSplitSpec, Site
from pram.rule   import SegregationModel
from pram.sim    import Simulation

import time
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------------------------------------------------------
# (1) Simulation (two locations)

loc = [Site('a'), Site('b')]

# probes will not impede pram2mesa but they are not converted either
probe_loc  = GroupSizeProbe.by_rel('loc', Site.AT, loc, msg_mode=ProbeMsgMode.DISP)
probe_sim  = GroupSizeProbe(
    name='sim',
    queries=[
        GroupQry(attr={ 'team': 'blue' }, rel={ Site.AT: loc[0] }),
        GroupQry(attr={ 'team': 'red'  }, rel={ Site.AT: loc[0] }),
        GroupQry(attr={ 'team': 'blue' }, rel={ Site.AT: loc[1] }),
        GroupQry(attr={ 'team': 'red'  }, rel={ Site.AT: loc[1] })
    ],
    qry_tot=None,
    persistence=ProbePersistenceDB(),
    msg_mode=ProbeMsgMode.DISP
)

s = (Simulation().
    set().
        pragma_autocompact(True).
        pragma_live_info(False).
        done().
    add([
        SegregationModel('team', len(loc)),
        Group(m=200, attr={ 'team': 'blue' }, rel={ Site.AT: loc[0] }),
        Group(m=300, attr={ 'team': 'blue' }, rel={ Site.AT: loc[1] }),
        Group(m=100, attr={ 'team': 'red'  }, rel={ Site.AT: loc[0] }),
        Group(m=400, attr={ 'team': 'red'  }, rel={ Site.AT: loc[1] }),
        probe_loc,  # the distribution should tend to 50%-50%
        probe_sim  # mass should tend to move towards two of the four sites
    ])
)

runs = 70

t0 = time.time()
s.run(runs)
time_elapsed = time.time() - t0
print(f'Time elapsed in {runs} runs: {time_elapsed} seconds')

series = [
    { 'var': 'p0', 'lw': 2, 'linestyle': '-',  'marker': '', 'color': 'blue',   'markersize': 0, 'lbl': 'Blue @ A' },
    { 'var': 'p1', 'lw': 2, 'linestyle': '-', 'marker': '', 'color': 'red', 'markersize': 0, 'lbl': 'Red @ A' },
    { 'var': 'p2', 'lw': 2, 'linestyle': '-',  'marker': '', 'color': 'navy',   'markersize': 0, 'lbl': 'Blue @ B' },
    { 'var': 'p3', 'lw': 2, 'linestyle': '-',  'marker': '', 'color': 'firebrick',   'markersize': 0, 'lbl': 'Red @ B' }
]

fig = probe_sim.plot(series, figsize=(8, 6))
fig.suptitle(f'Segregation PRAM Model - {runs} iterations', y=0.965)
fig.savefig("Segregation_PRAM_out")
