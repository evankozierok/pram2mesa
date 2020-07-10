"""
Original PRAM Simulation from:
    pram/src/sim/04-flu-prog-01/sim.py
"""


from pram.data        import ProbePersistenceDB, ProbeMsgMode, GroupSizeProbe
from pram.entity      import Group, GroupQry, GroupSplitSpec
from pram.model.model import MCSolver
from pram.model.epi   import SIRSModel
from pram.sim         import Simulation

from pram2mesa import pram2mesa

# ----------------------------------------------------------------------------------------------------------------------
s = (Simulation().
    add_probe(GroupSizeProbe.by_attr('flu', 'flu', ['s', 'i', 'r'], msg_mode=ProbeMsgMode.DISP)).
    add_rule(SIRSModel('flu', beta=0.05, gamma=0.50, alpha=0.10, solver=MCSolver())).
    add_group(Group(m=1000, attr={ 'flu': 's' }))
)

pram2mesa(s, "SIRSModel")
