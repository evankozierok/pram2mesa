"""
A custom Model class for a Mesa simulation.
"""

from .SIRSModelAgent import SIRSModelAgent, GroupQry
import json
import os
import warnings
from mesa import Agent, Model
from mesa.space import NetworkGrid
from mesa.time import StagedActivation
from make_python_identifier import make_python_identifier as mpi
import networkx as nx


class SIRSModelModel(Model):

    def __init__(self):
        super().__init__()
        # work from directory this file is in
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        self.schedule = StagedActivation(self, stage_list=['SIRSModel_MC'])
        self.G = nx.Graph()
        self.time = 0  # simple iteration counter
        self._generate_sites()
        self.grid = NetworkGrid(self.G)
        # make a dictionary of {hash: site} values for easy relation lookups in agent generation
        self.site_hashes = {h: s for s, h in dict(
            self.G.nodes.data('hash')).items()}
        self._generate_agents()
        self.vita_groups = []

    def step(self):
        if hasattr(self, 'datacollector'):
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
            if getattr(a, '__void__', False):
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
        with open("SIRSModelGroups.json", 'r') as file:
            j = json.load(file)
            for group in j:
                for _ in range(group['m']):
                    a = SIRSModelAgent(self.next_id(), self,
                                       group['attr'], group['rel'])
                    self.schedule.add(a)

    def _generate_sites(self):
        """
        Called once during __init__ to load the original simulation's sites into the networkx graph.
        Loads site data from a JSON file created during translation.
        """
        with open("SIRSModelSites.json", 'r') as file:
            j = json.load(file)
            for site in j:
                self.G.add_node(
                    site['name'], hash=site['hash'], rel_name=site['rel_name'])
                for k, v in site['attr'].items():
                    self.G.nodes[site['name']][k] = v

    # ------------------------- RUNTIME FUNCTIONS -------------------------

    def get_attr(self, agent_or_node, name=None):
        """
        Retrieves an attribute of a Mesa Agent or NetworkGrid node.
        :param name: A string containing the attribute to retrieve, or None
        :param agent_or_node: A Mesa Agent or a string corresponding to a node in the NetworkGrid
        :return: If agent_or_node is a string, returns the named attribute represented by it, or the node's entire
                     attribute dictionary if name is None (note: this includes the special 'agent' attribute)
                 If agent_or_node is an Agent, returns the named attribute of that Agent
        """
        name = mpi(name)[0] if name is not None else name
        if isinstance(agent_or_node, str):
            node_dict = self.grid.G.nodes[agent_or_node]
            return node_dict.get(name) if name is not None else node_dict
        elif isinstance(agent_or_node, Agent):
            # return getattr(agent_or_node, name, agent_or_node.namespace[name])
            return getattr(agent_or_node, name)
        else:
            raise TypeError(
                f"get_attr expected a str or Agent for agent_or_node, but received {type(agent_or_node)}")
