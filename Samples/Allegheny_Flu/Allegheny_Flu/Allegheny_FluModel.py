"""
A custom Model class for a Mesa simulation.
"""

from .Allegheny_FluAgent import Allegheny_FluAgent, GroupQry
import json
import os
import warnings
from mesa import Agent, Model
from mesa.space import NetworkGrid
from mesa.time import SimultaneousActivation
from .make_python_identifier import make_python_identifier as mpi
import networkx as nx


class Allegheny_FluModel(Model):

    def __init__(self, datacollector=None):
        super().__init__()
        # work from directory this file is in
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        self.schedule = SimultaneousActivation(self)
        self.G = nx.Graph()
        self.time = 0  # simple iteration counter
        self._generate_sites()
        self.grid = NetworkGrid(self.G)
        # make a dictionary of {hash: site} values for easy relation lookups in agent generation
        self.site_hashes = {h: s for s, h in dict(
            self.G.nodes.data('hash')).items()}
        self._generate_agents()
        self.vita_groups = []
        self.datacollector = datacollector

        for a in self.schedule.agents:
            Allegheny_FluModel._group_setup(self, a)
            a.advance()  # apply changes

    def step(self):
        if self.datacollector:
            self.datacollector.collect(self)
        else:
            warnings.warn('This Model has no DataCollector! You may want to add one in the `datacollector` attribute '
                          'before running the model')

        self.schedule.step()

        while self.vita_groups:
            a = self.vita_groups.pop()
            a.unique_id = self.next_id()
            a.model = self
            self.schedule.add(a)

        for a in self.schedule.agents:
            if a.get('__void__', False):
                self.grid._remove_agent(a, a.pos)
                self.schedule.remove(a)

        self.time += 1

    # ------------------------- INITIALIZATION HELPERS -------------------------

    def _generate_agents(self):
        """
        Called once during __init__ to create appropriate groups from the original simulation's model and add them to
        the model grid.
        Loads group data from the JSON file created during translation.
        """
        with open("Allegheny_FluGroups.json", 'r') as file:
            j = json.load(file)
            for group in j:
                for _ in range(group['m']):
                    a = Allegheny_FluAgent(
                        self.next_id(), self, group['attr'], group['rel'])
                    self.schedule.add(a)

    def _generate_sites(self):
        """
        Called once during __init__ to load the original simulation's sites into the networkx graph.
        Loads site data from a JSON file created during translation.
        """
        with open("Allegheny_FluSites.json", 'r') as file:
            j = json.load(file)
            for site in j:
                self.G.add_node(
                    str(site['name']), hash=site['hash'], rel_name=site['rel_name'])
                for k, v in site['attr'].items():
                    self.G.nodes[str(site['name'])][k] = v

    @staticmethod
    def _group_setup(pop, group):
        _x = pop.random.random()
        if _x < 0.9:
            group.set('flu', 's')
            return
        else:
            group.set('flu', 'i')
            return

    # ------------------------- RUNTIME FUNCTIONS -------------------------

    def get_groups(self, node_or_model, qry=None):
        """
        Returns a list of agents at the node or the entire model that satisfy the qry. 
        :param node_or_model: A string corresponding to a node in the NetworkGrid, or a Mesa Model
        :param qry: a GroupQry namedtuple
        :return: a list of agents at the node satisfying the qry. 
        """
        if isinstance(node_or_model, Model):
            agents = node_or_model.schedule.agents
        elif isinstance(node_or_model, str):
            agents = self.grid.get_cell_list_contents([node_or_model])
        else:
            raise TypeError(
                f"get_groups expects a str or Model for node_or_model, but received {type(node_or_model)}")

        return [a for a in agents if a.matches_qry(qry)]
        # if not qry:
        #     return agents
        # # the code below is REALLY PAINFUL... replacing it with 'return agents` makes the code run like 20x faster
        # elif qry.full:
        #     return [a for a in agents
        #             if qry.attr.items() == {k: getattr(a, k) for k in a._attr}.items()
        #             and qry.rel.items() == {k: getattr(a, k) for k in a._rel}.items()
        #             and all([fn(a) for fn in qry.cond])]
        # else:
        #     return [a for a in agents
        #             if qry.attr.items() <= {k: getattr(a, k) for k in a._attr}.items()
        #             and qry.rel.items() <= {k: getattr(a, k) for k in a._rel}.items()
        #             and all([fn(a) for fn in qry.cond])]

    def get_mass(self, agent_node_model, qry=None):
        """
        If agent_node_model is an agent, returns the number of agents with the same attributes as it, including itself.
        This ignores unique_id (and source_name).
        This is probably very unoptimized.
        If agent_node_model is a string corresponding to a node in the NetworkGrid, returns the number of agents at that
        node with the attributes specified in qry, or all agents at that node if qry is None.
        If agent_node_model is a Model, returns the total number of agents in the model.
        """
        if isinstance(agent_node_model, str):
            return len(self.get_groups(agent_node_model, qry))
        elif isinstance(agent_node_model, Agent):
            mod_dict = {k: v for k, v in agent_node_model.__dict__.items()
                        if k not in ('unique_id', 'source_name')}  # toss unique identifiers
            return sum([mod_dict == {k: v for k, v in a.__dict__.items() if k not in ('unique_id', 'source_name')}
                        for a in self.schedule.agents])
        elif isinstance(agent_node_model, Model):
            return len(agent_node_model.schedule.agents)
        else:
            raise TypeError(f"get_mass expects a str, Agent, or Model for agent_node_model, but received "
                            f"{type(agent_node_model)}")
