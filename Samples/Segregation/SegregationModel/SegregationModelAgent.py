"""
A custom Agent class for a Mesa simulation.
"""

from mesa import Agent
from pram2mesa.make_python_identifier import make_python_identifier_original as mpi
from dataclasses import dataclass, field
from typing import Any, List, Dict, Callable
import dill
import json
# ---- CUSTOM IMPORTS ----
# (many may be extraneous)
from collections import Iterable
import random

rule_file = 'SegregationModelRules.json'  # This could probably be done better?

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
        self.attr = {mpi(k)[0]: v for k, v in self.attr.items()}
        self.rel = {mpi(k)[0]: v for k, v in self.rel.items()}


class SegregationModelAgent(Agent):

    # def __init__(self, unique_id, model):
    def __init__(self, unique_id, model, attr, rel):
        super().__init__(unique_id, model)
        # making identifiers should be handled in translation now
        # self.namespace = {}  # for make_python_identifier
        # Mesa generally holds Agent data (including locations) as attributes, not dictionary entries.
        # as such, we only store names of attributes and relations in different sets for compatibility with some
        # specific PRAM functions like get_attrs and get_rels. If needed, attribute values are retrieved lazily
        self._attr = set()
        self._rel = set()
        for key, value in attr.items():
            # id, self.namespace = mpi(key, namespace=self.namespace, reserved_words=[])
            # setattr(self, id, value)
            # self._attr.add(id)
            setattr(self, key, value)
            self._attr.add(key)
        for key, value in rel.items():
            s = self.model.site_hashes[value]
            if key == '@':
                self.model.grid.place_agent(self, s)
                self._rel.add('pos')
            else:
                # id, self.namespace = mpi(key, namespace=self.namespace, reserved_words=['agent', 'weight'])
                # setattr(self, id, s)
                # self._rel.add(id)
                setattr(self, key, s)
                self._rel.add(key)
        # make (callable) instances of each of our rules
        self.SegregationModel = SegregationModel(self)

    # currently, translated models use StagedActivation for all their rules.
    # in the future, a sort of simultaneous staged activation may be possible.
    #
    # as such, the step function should not be used.
    def step(self):
        pass

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
            qry = {mpi(key)[0]: value for key, value in qry.items()}
            return qry.items() <= self.__dict__.items()
        elif isinstance(qry, str):  # place above iterable check, since str is iterable
            return mpi(qry)[0] in self.__dict__.keys()
        elif isinstance(qry, Iterable):
            return all(mpi(i)[0] in self.__dict__.keys() for i in qry)

        raise TypeError(
            f'qry passed to has_attr should be of type dict, str, or Iterable, but was {type(qry)} instead')

    def has_rel(self, qry):
        """
        Determines if this agent matches a specified query of relations.
        Currently, this is the same function as has_attr.
        :param qry: A string, iterable, or mapping of relations.
        :return: True if... (False otherwise)
            * qry is a string and is a key in this agent's __dict__
            * qry is an iterable and all items in it are keys in this agent's __dict__
            * qry is a mapping and all items in it are in this agent's __dict__
            Note: these checks are done after making the string, iterable items, or keys into python-safe names.
        """
        if isinstance(qry, dict):
            qry = {mpi(key)[0]: value for key, value in qry}
            return qry.items() <= self.__dict__.items()
        elif isinstance(qry, str):  # place above iterable check, since str is iterable
            return mpi(qry)[0] in self.__dict__.keys()
        elif isinstance(qry, Iterable):
            return all(mpi(i)[0] in self.__dict__.keys() for i in qry)

        raise TypeError(
            f'qry passed to has_rel should be of type dict, str, or Iterable, but was {type(qry)} instead')

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
            return qry.attr.items() == {k: getattr(self, k) for k in self._attr}.items() \
                and qry.rel.items() == {k: getattr(self, k) for k in self._rel}.items() \
                and all([fn(self) for fn in qry.cond])
        else:
            return qry.attr.items() <= {k: getattr(self, k) for k in self._attr}.items() \
                and qry.rel.items() <= {k: getattr(self, k) for k in self._rel}.items() \
                and all([fn(self) for fn in qry.cond])


class SegregationModel:
    """
    Segregation model.


    ----[ Notation A ]----

    code:
        SegregationModel('team', 2)

    init:
        p_migrate = 0.05

    is-applicable:
        has-attr: team
        has-rel: @

    apply:
        p_team = n@_{attr.team = group.attr.team} / n@  # ...
        if (p_team < 0.5):
            rd p_migrate -> R:@ = get_random_site()
            nc 1 - p_migrate


    ----[ Notation B ]----

    p_team = n@_{attr.team = group.attr.team} / n@
    if (p_team < 0.5) p_migrate -> R:@ = get_random_site()
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
        attr_val = pop.get_attr(group, self.attr)
        site = group.pos
        m = pop.get_mass(site, None)
        if m == 0:
            return
        m_team = pop.get_mass(site, GroupQry(attr={self.attr: attr_val}))
        p_team = m_team / m
        if p_team < self.p_repel:
            site_rnd = self.get_random_site(pop, site)
            _x = pop.random.random()
            if _x < self.p_migrate:
                pop.grid.move_agent(group, site_rnd)
                return
            else:
                return
        else:
            return

    def get_random_site(self, pop, site):
        """ Returns a random site different than the specified one. """
        s = random.choice(list(pop.site_hashes.values()))
        while s == site:
            s = random.choice(list(pop.site_hashes.values()))
        return s

    def is_applicable(self, group, iter, t):
        return super().is_applicable(group, iter, t) and group.has_attr([
            self.attr]) and group.has_rel(['@'])

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
