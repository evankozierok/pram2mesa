from pram.entity import Group, GroupDBRelSpec, GroupQry, GroupSplitSpec, Site
from pram.rule   import Rule, TimeAlways
from pram.sim    import Simulation
import os

from pram.data   import GroupSizeProbe, ProbePersistenceDB
from pram.entity import GroupQry, Site


# ----------------------------------------------------------------------------------------------------------------------
fpath_out = os.path.join(os.path.dirname(__file__), 'output', 'allegheny-flu-results.sqlite3')

if os.path.isfile(fpath_out):
    os.remove(fpath_out)

pp = ProbePersistenceDB(fpath_out)


# ----------------------------------------------------------------------------------------------------------------------
def probe_flu_at(school, name=None):
    return GroupSizeProbe(
        name=name or str(school.name),
        queries=[
            GroupQry(attr={ 'flu': 's' }, rel={ 'school': school }),
            GroupQry(attr={ 'flu': 'i' }, rel={ 'school': school }),
            GroupQry(attr={ 'flu': 'r' }, rel={ 'school': school })
        ],
        qry_tot=GroupQry(rel={ 'school': school }),
        persistence=pp,
        var_names=['ps', 'pi', 'pr', 'ns', 'ni', 'nr']
    )


fpath_db = os.path.join(os.path.dirname(__file__), '..', 'Data', 'allegheny-students-modified.sqlite3')


# ----------------------------------------------------------------------------------------------------------------------

class FluProgressRule(Rule):
    def __init__(self):
        super().__init__('flu-progress', TimeAlways())

    def apply(self, pop, group, iter, t):
        # Susceptible:
        if group.has_attr({ 'flu': 's' }):
            at  = group.get_rel(Site.AT)
            n   = at.get_mass()                               # total    population at current location
            n_i = at.get_mass(GroupQry(attr={ 'flu': 'i' }))  # infected population at current location

            p_infection = float(n_i) / float(n)  # changes every iteration (i.e., the source of the simulation dynamics)

            return [
                GroupSplitSpec(p=    p_infection, attr_set={ 'flu': 'i' }),
                GroupSplitSpec(p=1 - p_infection, attr_set={ 'flu': 's' })
            ]

        # Infected:
        if group.has_attr({ 'flu': 'i' }):
            return [
                GroupSplitSpec(p=0.2, attr_set={ 'flu': 'r' }),  # group size after: 20% of before (recovered)
                GroupSplitSpec(p=0.8, attr_set={ 'flu': 'i' })   # group size after: 80% of before (still infected)
            ]

        # Recovered:
        if group.has_attr({ 'flu': 'r' }):
            return [
                GroupSplitSpec(p=0.9, attr_set={ 'flu': 'r' }),
                GroupSplitSpec(p=0.1, attr_set={ 'flu': 's' })
            ]


# ----------------------------------------------------------------------------------------------------------------------
class FluLocationRule(Rule):
    def __init__(self):
        super().__init__('flu-location', TimeAlways())

    def apply(self, pop, group, iter, t):
        # Infected and low income:
        if group.has_attr({ 'flu': 'i', 'income_level': 'l' }):
            return [
                GroupSplitSpec(p=0.1, rel_set={ Site.AT: group.get_rel('home') }),
                GroupSplitSpec(p=0.9)
            ]

        # Infected and medium income:
        if group.has_attr({ 'flu': 'i', 'income_level': 'm' }):
            return [
                GroupSplitSpec(p=0.6, rel_set={ Site.AT: group.get_rel('home') }),
                GroupSplitSpec(p=0.4)
            ]

        # Recovered:
        if group.has_attr({ 'flu': 'r' }):
            return [
                GroupSplitSpec(p=0.8, rel_set={ Site.AT: group.get_rel('school') }),
                GroupSplitSpec(p=0.2)
            ]

        return None


# ----------------------------------------------------------------------------------------------------------------------
# (1) Sites:

site_home = Site('home')
school_l  = Site(450149323)  # 88% low income students
school_m  = Site(450067740)  #  7% low income students


# ----------------------------------------------------------------------------------------------------------------------
# (2) Simulation:

def grp_setup(pop, group):
    return [
        GroupSplitSpec(p=0.9, attr_set={ 'flu': 's' }),
        GroupSplitSpec(p=0.1, attr_set={ 'flu': 'i' })
    ]


(Simulation().
    set().
        rand_seed(1928).
        pragma_autocompact(True).
        pragma_live_info(True).
        pragma_live_info_ts(False).
        pragma_fractional_mass(True).
        fn_group_setup(grp_setup).
        done().
    add().
        rule(FluProgressRule()).
        rule(FluLocationRule()).
        probe(probe_flu_at(school_l, 'low-income')).  # the simulation output we care about and want monitored
        probe(probe_flu_at(school_m, 'med-income')).  # ^
        done().
    db(fpath_db).
        gen_groups(
            tbl      = 'students',
            attr_db  = ['income_level'],
            rel_db   = [GroupDBRelSpec(name='school', col='school_id')],
            attr_fix = {},
            rel_fix  = { 'home': site_home },
            rel_at   = 'school'
        ).
        done().
    run(100)
)
