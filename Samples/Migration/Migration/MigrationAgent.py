"""
A custom Agent class for a Mesa simulation.
"""

from mesa import Agent, Model
from .make_python_identifier import make_python_identifier as mpi
from collections import Iterable, namedtuple
from dataclasses import dataclass, field
from typing import Any, List, Dict, Callable
import copy
import dill
import json
# ---- CUSTOM IMPORTS ----
# (many may be extraneous)
import random
import statistics

rule_file = 'MigrationRules.json'  # This could probably be done better?

# GroupQry = namedtuple('GroupQry', 'attr rel cond full', defaults=[{}, {}, [], False])


@dataclass
class GroupQry:
    attr: Dict[str, Any] = field(default_factory=dict)
    # check type of values here
    rel: Dict[str, str] = field(default_factory=dict)
    cond: List[Callable[[Agent], bool]] = field(default_factory=list)
    full: bool = False

    def __post_init__(self):
        # ensure attributes and relations are valid variable names
        self.attr = {mpi(k): v for k, v in self.attr.items()}
        self.rel = {mpi(k): v for k, v in self.rel.items()}


class MigrationAgent(Agent):

    _protected = ('model', 'random', 'source_name', 'unique_id', '_attr', '_rel', 'pos', 'set_dict', 'del_set',
                  'ConflictRule', 'MigrationRule')  # TODO: should pos actually be in here

    # def __init__(self, unique_id, model):
    def __init__(self, unique_id, model, attr, rel):
        # Mesa generally holds Agent data (including locations) as attributes, not dictionary entries.
        # as such, we only store names of attributes and relations in different sets for compatibility with some
        # specific PRAM functions like get_attrs and get_rels. If needed, attribute values are retrieved lazily
        self._attr = set()
        self._rel = set()
        self.set_dict = {}
        self.del_set = set()
        super().__init__(unique_id, model)
        # making identifiers should be handled in translation now
        # self.namespace = {}  # for make_python_identifier
        for key, value in attr.items():
            # id, self.namespace = mpi(key, namespace=self.namespace, reserved_words=[])
            # setattr(self, id, value)
            # self._attr.add(id)
            setattr(self, key, value)
            # self._attr.add(key)
        for key, value in rel.items():
            s = self.model.site_hashes[value]
            if key == '@':
                self.model.grid.place_agent(self, s)
                self._rel.add('pos')
            else:
                setattr(self, key, s)
            # else:
            #     # id, self.namespace = mpi(key, namespace=self.namespace, reserved_words=['agent', 'weight'])
            #     # setattr(self, id, s)
            #     # self._rel.add(id)
            #     setattr(self, key, s)
            #     self._rel.add(key)
        # make (callable) instances of each of our rules
        self.ConflictRule = ConflictRule(self)
        self.MigrationRule = MigrationRule(self)

    # we customize __setattr__ in order to:
    # - keep track of attributes vs relations, mostly for pram compatibility.
    # - prevent some awkward constructs when trying to set position (i.e., `if xyz == '@'...`)
    # - transparently use make_python_identifier to ensure safe variable names
    def __setattr__(self, name, value):
        # don't treat special variables any different
        if name in MigrationAgent._protected:
            object.__setattr__(self, name, value)
            return

        name = mpi(name)

        if value in self.model.grid.G.nodes:
            # if value in self.model.site_hashes | self.model.grid.G.nodes:
            #     try:
            #         value = self.model.site_hashes[value]
            #     except KeyError:
            #         pass
            if name == '_at_sign':
                self.model.grid.move_agent(self, value)
                # self._rel.add('pos')
            else:
                object.__setattr__(self, name, value)
                self._rel.add(name)
            return

        object.__setattr__(self, name, value)
        self._attr.add(name)

    # we also customize __getattr__ to use make_python_identifier where needed and for position lookups
    # we do not use __getattribute__; we only want to change behavior for non-safe/non-found attributes, and '@' (pos)
    def __getattr__(self, name):
        mod_name = mpi(name)
        # if name == mod_name:
        #     raise AttributeError(f"'{type(self).__name__}' object has no attribute '{mod_name}'")
        if mod_name == '_at_sign':
            return self.pos

        # all we do to fix broken lookups is look for positional calls and unsafe names.
        # if calling mpi fixes a name, this sends it back to __getattribute__ and we continue as normal.
        # if not, it will get caught by the first if clause above (this may be an inefficient way to do this)
        # return getattr(self, mod_name)
        return object.__getattribute__(self, mod_name)

    # we similarly customize __delattr__ to use make_python_identifier and to remove agents from the grid
    def __delattr__(self, name):
        try:
            object.__delattr__(self, name)
        except AttributeError:
            name = mpi(name)
            if name == 'at_sign':
                self.grid._remove_agent(self, self.pos)
                object.__delattr__(self, 'pos')
            else:
                object.__delattr__(self, name)

        # purge from _attr or _rel (we just blindly guess until we either get it or don't)
        try:
            self._attr.remove(name)
        except KeyError:
            try:
                self._rel.remove(name)
            except KeyError:
                pass

    # models use SimultaneousActivation.
    # The step function calls all of the rules, which will stage attribute changes.
    # The advance function makes those changes.
    def step(self):
        self.ConflictRule()
        self.MigrationRule()

    def advance(self):
        for key, value in self.set_dict.items():
            setattr(self, key, value)
        self.set_dict.clear()

        while self.del_set:
            delattr(self, self.del_set.pop())

    def set(self, key, value):
        """
        Use this function instead of directly setting an attribute in a rule.
        """
        self.set_dict[key] = value

    def get(self, key, default=None):
        """
        Alias for getattr(self, key, default).
        (Note however that this will return None instead of throw an AttributeError)
        """
        return getattr(self, key, default)

    def delete(self, key):
        """
        Use this function instead of directly deleting an attribute in a rule.
        """
        self.del_set.add(key)

    def has_attr(self, qry):
        """
        Determines if this agent matches a specified query of attributes.
        :param qry: A string, iterable, or mapping of attributes.
        :return: True if... (False otherwise)
            * qry is a string and is a key in this agent's __dict__
            * qry is an iterable and all items in it are keys in this agent's __dict__
            * qry is a mapping and all items in it are in this agent's __dict__
            Note: these checks are done after making the string, iterable items, or keys into python-safe names.
        """
        if isinstance(qry, dict):
            qry = {mpi(key): value for key, value in qry.items()}
            return qry.items() <= self.__dict__.items()
        elif isinstance(qry, str):  # place above iterable check, since str is iterable
            return mpi(qry) in self.__dict__.keys()
        elif isinstance(qry, Iterable):
            return all(mpi(i) in self.__dict__.keys() for i in qry)

        raise TypeError(
            f'qry passed to has_attr should be of type dict, str, or Iterable, but was {type(qry)} instead')

    def matches_qry(self, qry):
        """
        Determines if this agent matches the given GroupQry.
        If qry.full is True the attributes and relations must be an exact match (not including unique identifiers like
        unique_id and source_name); if False, the qry's attributes and relations need only be a subset of the agent's.
        An agent automatically matches a None qry
        :param qry: A GroupQry namedtuple
        :return: True if the agent matches the qry; False otherwise
        """

        if not qry:
            return True
        # the code below is REALLY PAINFUL... replacing it with 'return True` makes the code run like 20x faster
        if qry.rel.get('@'):
            qry.rel['pos'] = qry.rel.pop('@')

        if qry.full:
            return qry.attr.items() == {k: self.get(k) for k in self._attr}.items() \
                and qry.rel.items() == {k: self.get(k) for k in self._rel}.items() \
                and all([fn(self) for fn in qry.cond])
        else:
            return qry.attr.items() <= {k: self.get(k) for k in self._attr}.items() \
                and qry.rel.items() <= {k: self.get(k) for k in self._rel}.items() \
                and all([fn(self) for fn in qry.cond])


class ConflictRule:
    """
    Conflict causes death and migration.  The probability of death scales with the conflict's severity and scale
    while the probability of migration scales with the conflict's scale only.  Multipliers for both factors are exposed
    as parameters.

    Time of exposure to conflict also increases the probability of death and migration, but that influence isn't
    modeled directly.  Instead, a proportion of every group of non-migrating agents can die or migrate at every step of
    the simulation.

    Every time a proportion of population is beginning to migrate, the destination site is set and the distance to that
    site use used elewhere to control settlement.
    """

    def __init__(self, agent):
        self.agent = agent
        self.model = agent.model
        with open(rule_file, 'r') as file:
            j = json.load(file)
            data = next((d for d in j if d['rule_type'] == type(self).
                         __name__), {})
            if data:
                gq = data['group_qry']
                if gq:
                    data['group_qry'] = GroupQry(gq['attr'], gq['rel'],
                                                 dill.loads(bytes.fromhex(gq['cond'])), gq['full'])
            self.__dict__.update(data)

    def apply(self, pop, group, iter, t):
        p_death = self.scale * self.severity * self.severity_death_mult
        p_migration = self.scale * self.scale_migration_mult
        # the definition of sites_dst is unfortunately missed in translation
        # site_dst = random.choice(sites_dst)
        site_dst = random.choice([s for s in pop.grid.G.nodes if s != 'Sudan'])
        _x = pop.random.random()
        if _x < p_death:
            group.set('__void__', True)
            return
        if _x < p_death + p_migration:
            group.set('is-migrating', True)
            group.set('migration-time', 0)
            group.set('travel-time-left', pop.get_attr(site_dst, 'travel-time')
                      )
            group.set('site-dst', site_dst)
            return
        else:
            return

    def __call__(self):
        if not self.agent.matches_qry(self.group_qry):
            return
        if not self.i:
            self.apply(self.model, self.agent, self.model.time,
                       self.model.time)
        elif isinstance(self.i, int) and self.model.time == self.i:
            self.apply(
                self.model, self.agent, self.model.time, self.model.time)
        elif isinstance(self.i, list):
            if self.i[1] == 0 and self.model.time <= self.i[0]:
                self.apply(self
                           .model, self.agent, self.model.time, self.model.time)
            elif self.i[0] <= self.model.time <= self.i[1]:
                self.apply(self.
                           model, self.agent, self.model.time, self.model.time)
        elif isinstance(self.i, set) and self.model.time in self.i:
            self.apply(
                self.model, self.agent, self.model.time, self.model.time)


class MigrationRule:
    """
    Migrating population has a chance of dying and the probability of that happening is proportional to the harshness
    of the environment and the mass of already migrating population.  Multipliers for both factors are exposed as
    parameters.

    Time of exposure to the environment also increases the probability of death, but that influence isn't modeled
    directly.  Instead, a proportion of every group of migrating agents can die at every step of the simulation.

    Environmental harshness can be controled via another rule which conditions it on the time of year (e.g., winter
    can be harsher than summer or vice versa depending on region).

    A migrating population end to migrate by settling in its destination site.
    """

    def __init__(self, agent):
        self.agent = agent
        self.model = agent.model
        with open(rule_file, 'r') as file:
            j = json.load(file)
            data = next((d for d in j if d['rule_type'] == type(self).
                         __name__), {})
            if data:
                gq = data['group_qry']
                if gq:
                    data['group_qry'] = GroupQry(gq['attr'], gq['rel'],
                                                 dill.loads(bytes.fromhex(gq['cond'])), gq['full'])
            self.__dict__.update(data)

    def apply(self, pop, group, iter, t):
        if group.has_attr({'travel-time-left': 0}):
            return self.apply_settle(pop, group, iter, t)
        else:
            return self.apply_keep_migrating(pop, group, iter, t)

    def apply_keep_migrating(self, pop, group, iter, t):
        migrating_groups = pop.get_groups(pop, GroupQry(cond=[lambda g: g.
                                                              has_attr({'is-migrating': True})]))
        if migrating_groups and len(migrating_groups) > 0:
            migrating_m = len(migrating_groups)
            migrating_p = migrating_m / pop.get_mass(pop, None) * 100
        else:
            migrating_p = 0
        p_death = min(self.env_harshness * self.env_harshness_death_mult +
                      migrating_p * self.migration_death_mult, 1.0)
        _x = pop.random.random()
        if _x < p_death:
            group.set('__void__', True)
            return
        else:
            group.set('migration-time', pop.get_attr(group,
                                                     'migration-time') + 1)
            group.set('travel-time-left', pop.get_attr(group,
                                                       'travel-time-left') - 1)
            return

    def apply_settle(self, pop, group, iter, t):
        group.set('migration-time', pop.get_attr(group, 'migration-time') + 1)
        group.set('is-migrating', False)
        group.set('has-settled', True)
        group.set('@', group.get('site-dst'))
        group.delete('site-dst')
        return

    def __call__(self):
        if not self.agent.matches_qry(self.group_qry):
            return
        if not self.i:
            self.apply(self.model, self.agent, self.model.time,
                       self.model.time)
        elif isinstance(self.i, int) and self.model.time == self.i:
            self.apply(
                self.model, self.agent, self.model.time, self.model.time)
        elif isinstance(self.i, list):
            if self.i[1] == 0 and self.model.time <= self.i[0]:
                self.apply(self
                           .model, self.agent, self.model.time, self.model.time)
            elif self.i[0] <= self.model.time <= self.i[1]:
                self.apply(self.
                           model, self.agent, self.model.time, self.model.time)
        elif isinstance(self.i, set) and self.model.time in self.i:
            self.apply(
                self.model, self.agent, self.model.time, self.model.time)
