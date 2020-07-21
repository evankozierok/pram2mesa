import textwrap
from typing import Iterable, Tuple, Set, List

from pram.rule import IterAlways, IterPoint, IterInt, IterSet
from pram.rule import TimeAlways, TimePoint, TimeInt, TimeSet
from pram.sim import Simulation
from pram2mesa.make_python_identifier import make_python_identifier as mpi
import dill
import os.path
import re
import json
import iteround
import inspect
import ast
import astor
import autopep8
import shutil
from pram2mesa.rule_writer import RuleWriter


# TODO: package mpi with each translation? -- Make more specific function for that
# TODO: maybe incorporate is_applicable into __call__ or something
# TODO: make all dangling random calls go to pop.random
# TODO: _attr, _rel, and thus get_attrs and get_rels are not good. Could try doing __setattr__ shenanigans? Or just say
#       goodbye to that part... (matching full queries also a mess)
# TODO: SimRules
# TODO: more robust handling of inheritance; currently we stop after finding an apply but maybe we should keep going?
# TODO: make it faster. A large portion of time is spent in get_groups when trying a GroupQry
def pram2mesa(sim: Simulation, name: str, autopep: bool = True) -> None:
    """
    Converts a PyPRAM simulation object to equivalent Mesa Agent and Model classes.
    This function should be the only function a user must call.

    :param sim: The PyPRAM Simulation to translate
    :param name: The prefix of the files to be created.
    :param autopep: Should the files be run through autopep8 to clean the code?
                    If autopep evaluates to False, autopep8 will not be used.
                    If custom autopep8 usage is desired, set autopep to False and do so manually
    :return: None. Creates two Python files containing the new Mesa Agent and Model classes and three JSON data files.
             From there, instantiate one of these Models and proceed using standard Mesa tools.
    """
    directory = _make_filename(name, extension='')
    os.mkdir(directory)
    os.chdir(directory)
    # model relies on make_python_identifier so we pack it up
    shutil.copy(inspect.getsourcefile(mpi), '.')
    group_file, site_file, rule_file = create_json_data(sim, name)
    rw = RuleWriter()

    new_rules, rule_imports = translate_rules([type(r) for r in sim.rules], rw)
    top_level_rules = [type(r).__name__ for r in sim.rules]

    group_setup = sim.fn.group_setup or ''
    if group_setup:
        tree = ast.parse(textwrap.dedent(inspect.getsource(group_setup)))
        tree.body[0].name = '_group_setup'
        # tree.body[0].args.args[0].arg = 'self'  # FIXME: this is hacky
        tree.body[0].decorator_list.append('staticmethod')
        group_setup = astor.to_source(rw.visit(tree))

    agent_file = create_agent_class(name, new_rules, top_level_rules, rule_file, used_functions=rw.used,
                                    custom_imports='\n'.join(rule_imports))
    model_file = create_model_class(name, group_file, site_file, agent_file, top_level_rules, group_setup,
                                    used_functions=rw.used)

    if autopep:
        autopep8.fix_file(agent_file, options=autopep8.parse_args(['--in-place', agent_file]))
        autopep8.fix_file(model_file, options=autopep8.parse_args(['--in-place', model_file]))

    # if autopep:
    #     default_pep = {'in_place': True}
    #     if isinstance(autopep, dict):
    #         default_pep.update(autopep)
    #     # the above code will have in_place as True unless explicitly set otherwise.
    #     # However, if it is set otherwise, we must make new files for the modified code
    #     if not default_pep['in_place']:
    #         new_agent_file = f'{agent_file}_autopep'
    #         new_model_file = f'{model_file}_autopep'
    #         with open(new_agent_file, 'w') as file:
    #             autopep8.fix_file(agent_file, options=default_pep, output=file)
    #         with open(new_model_file, 'w') as file:
    #             autopep8.fix_file(model_file, options=default_pep, output=file)
    #     else:
    #         autopep8.fix_file(agent_file, options=default_pep)
    #         autopep8.fix_file(model_file, options=default_pep)


def create_agent_class(name: str, rules: Iterable[str], rule_names: Iterable[str], rule_file: str,
                       custom_imports: str = '', used_functions: Set[str] = None) -> str:
    """
    Creates a Python file containing code for the custom Agent class.
    :param name: The name from which the filename will be derived
    :param rules: A list of strings containing code for the rules that will be added
    :param rule_names: A list of class names of the rules that will be added
    :param rule_file: A string containing the filename of the JSON Rule data
    :param custom_imports: Non-default import statements that should be included
    :param used_functions: A set of custom functions that must be added. This is derived in rule processing
    :return: The filename of the new Python file.
    """
    if not used_functions:
        used_functions = set()
    class_name = f'{name}Agent'
    filename = _make_filename(class_name)
    # \n is not permitted in an f-string expression, so do so beforehand
    rules = '\n'.join(rules)
    rule_declarations = '\n        '.join([f'self.{r} = {r}(self)' for r in rule_names])
    # step_functions = ['rule_a', 'rule_b', 'rule_c']
    # step_functions_out = '\n        '.join([f'{step}()' for step in step_functions])

    code = f'''"""
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
{custom_imports}

rule_file = '{rule_file}'  # This could probably be done better?

# GroupQry = namedtuple('GroupQry', 'attr rel cond full', defaults=[{{}}, {{}}, [], False])
@dataclass
class GroupQry:
    attr: Dict[str, Any] = field(default_factory=dict)
    rel: Dict[str, str] = field(default_factory=dict)  # check type of values here
    cond: List[Callable[[Agent], bool]] = field(default_factory=list)
    full: bool = False
    def __post_init__(self):
        # ensure attributes and relations are valid variable names
        self.attr = {{mpi(k): v for k, v in self.attr.items()}}
        self.rel = {{mpi(k): v for k, v in self.rel.items()}}
    

class {class_name}(Agent):

    _protected = ('model', 'random', 'source_name', 'unique_id', '_attr', '_rel', 'pos',
                  {', '.join([f"'{r}'" for r in rule_names])})  # TODO: should pos actually be in here
    
    # def __init__(self, unique_id, model):
    def __init__(self, unique_id, model, attr, rel):
        # Mesa generally holds Agent data (including locations) as attributes, not dictionary entries.
        # as such, we only store names of attributes and relations in different sets for compatibility with some
        # specific PRAM functions like get_attrs and get_rels. If needed, attribute values are retrieved lazily
        self._attr = set()
        self._rel = set()
        super().__init__(unique_id, model)
        # making identifiers should be handled in translation now
        # self.namespace = {{}}  # for make_python_identifier
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
        {rule_declarations}

    # we customize __setattr__ in order to:
    # - keep track of attributes vs relations, mostly for pram compatibility.
    # - prevent some awkward constructs when trying to set position (i.e., `if xyz == '@'...`)
    # - transparently use make_python_identifier to ensure safe variable names
    def __setattr__(self, name, value):
        # don't treat special variables any different
        if name in {class_name}._protected:
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
        #     raise AttributeError(f"'{{type(self).__name__}}' object has no attribute '{{mod_name}}'")
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
                

    # currently, translated models use StagedActivation for all their rules.
    # in the future, a sort of simultaneous staged activation may be possible.
    #
    # as such, the step function should not be used.
    def step(self): 
        pass

'''
    if 'copy' in used_functions:
        code += '''
    def copy(self, is_deep=False):
        """
        Copies an agent, but explicitly *does not* add them to the scheduler or grid.
        To do so, call add_vita_group (in PRAM).
        NOTE: deep copies are NOT RECOMMENDED.
        """
        
        new = copy.copy(self) if not is_deep else copy.deepcopy(self)
        new.unique_id = None
        new.model = None
        return new
'''

    if 'ha' in used_functions or 'has_attr' in used_functions:
        code += '''
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
            
        raise TypeError(f'qry passed to has_attr should be of type dict, str, or Iterable, but was {type(qry)} instead')
'''
    if {'hr', 'has_rel', 'has_sites'} & used_functions:
        code += '''
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
            qry = {mpi(key): value for key, value in qry}
            return qry.items() <= self.__dict__.items()
        elif isinstance(qry, str):  # place above iterable check, since str is iterable
            return mpi(qry) in self.__dict__.keys()
        elif isinstance(qry, Iterable):
            return all(mpi(i) in self.__dict__.keys() for i in qry)
            
        raise TypeError(f'qry passed to has_rel should be of type dict, str, or Iterable, but was {type(qry)} instead')
'''
    # if {'matches_qry', 'get_groups', 'get_mass', 'get_mass_prop', 'get_mass_and_prop', 'get_group', 'get_groups_mass',
    #         'get_groups_mass_prop', 'get_groups_mass_and_prop'} & used_functions:
    if True:  # currently all rules use matches_qry
        code += '''
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
            return qry.attr.items() == {k: getattr(self, k) for k in self._attr}.items() \\
                   and qry.rel.items() == {k: getattr(self, k) for k in self._rel}.items() \\
                   and all([fn(self) for fn in qry.cond])
        else:
            return qry.attr.items() <= {k: getattr(self, k) for k in self._attr}.items() \\
                   and qry.rel.items() <= {k: getattr(self, k) for k in self._rel}.items() \\
                   and all([fn(self) for fn in qry.cond])
'''

    code += rules

    # this is pretty lazy but a good safeguard
    code = code.replace("Site.AT", "'@'")

    with open(filename, 'w') as file:
        file.write(code)

    return filename


def create_model_class(name: str, group_file: str, site_file: str, agent_file: str, stage_list: Iterable[str],
                       group_setup: str = '', custom_imports: str = '', used_functions: Set[str] = None) -> str:
    """
    Creates a Python file containing code for the custom Model class.
    :param name: The name from which the filename will be derived
    :param group_file: The name of the JSON file storing Group data from the PRAM
    :param site_file: The name of the JSON file storing Site data from the PRAM
    :param agent_file: The name of the corresponding Mesa Agent file
    :param stage_list: A list of stage functions for the schedule
    :param group_setup: The definition of a pre-run group setup rule, or None
    :param custom_imports: Non-default import statements that should be included
    :param used_functions: A set of custom functions that must be added. This is derived in rule processing
    :return: The filename of the new Python file.
    """
    if not used_functions:
        used_functions = set()

    class_name = f'{name}Model'
    agent_module = agent_file[:-3]  # strip .py
    code = f'''"""
A custom Model class for a Mesa simulation.
"""

from .{agent_module} import {agent_module}, GroupQry
import json
import os
import warnings
from mesa import Agent, Model
from mesa.space import NetworkGrid
from mesa.time import StagedActivation
from .make_python_identifier import make_python_identifier as mpi
import networkx as nx
{custom_imports}


class {class_name}(Model):
    
    def __init__(self, datacollector=None):
        super().__init__()
        # work from directory this file is in
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        self.schedule = StagedActivation(self, stage_list={stage_list})
        self.G = nx.Graph()
        self.time = 0  # simple iteration counter
        self._generate_sites()
        self.grid = NetworkGrid(self.G)
        # make a dictionary of {{hash: site}} values for easy relation lookups in agent generation
        self.site_hashes = {{h: s for s, h in dict(self.G.nodes.data('hash')).items()}}
        self._generate_agents()
        self.vita_groups = []
        self.datacollector = datacollector
        {f"""
        for a in self.schedule.agents:
            {class_name}._group_setup(self, a)""" 
        if group_setup else ""}
        
        
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
        with open("{group_file}", 'r') as file:
            j = json.load(file)
            for group in j:
                for _ in range(group['m']): 
                    a = {name}Agent(self.next_id(), self, group['attr'], group['rel'])
                    self.schedule.add(a)
    
    def _generate_sites(self):
        """
        Called once during __init__ to load the original simulation's sites into the networkx graph.
        Loads site data from a JSON file created during translation.
        """
        with open("{site_file}", 'r') as file:
            j = json.load(file)
            for site in j:
                self.G.add_node(str(site['name']), hash=site['hash'], rel_name=site['rel_name'])
                for k, v in site['attr'].items():
                    self.G.nodes[str(site['name'])][k] = v

{textwrap.indent(group_setup, '    ') if group_setup else ""}

    # ------------------------- RUNTIME FUNCTIONS -------------------------
'''

    if 'ga' in used_functions or 'get_attr' in used_functions:
        code += '''
    def get_attr(self, agent_or_node, name=None):
        """
        Retrieves an attribute of a Mesa Agent or NetworkGrid node.
        :param name: A string containing the attribute to retrieve, or None
        :param agent_or_node: A Mesa Agent or a string corresponding to a node in the NetworkGrid
        :return: If agent_or_node is a string, returns the named attribute represented by it, or the node's entire
                     attribute dictionary if name is None (note: this includes the special 'agent' attribute)
                 If agent_or_node is an Agent, returns the named attribute of that Agent
        """
        name = mpi(name) if name is not None else name
        if isinstance(agent_or_node, str):
            node_dict = self.grid.G.nodes[agent_or_node]
            return node_dict.get(name) if name is not None else node_dict
        elif isinstance(agent_or_node, Agent):
            # return getattr(agent_or_node, name, agent_or_node.namespace[name])
            return getattr(agent_or_node, name)
        else:
            raise TypeError(f"get_attr expected a str or Agent for agent_or_node, but received {type(agent_or_node)}")
'''

    if {'get_groups', 'get_mass', 'get_mass_prop', 'get_mass_and_prop', 'get_group', 'get_groups_mass',
            'get_groups_mass_prop', 'get_groups_mass_and_prop'} & used_functions:
        code += '''
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
            raise TypeError(f"get_groups expects a str or Model for node_or_model, but received {type(node_or_model)}")
        
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
    '''

    if {'get_mass', 'get_mass_prop', 'get_mass_and_prop'} & used_functions:
        code += '''
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
                        if k not in ('unique_id', 'source_name')} # toss unique identifiers
            return sum([mod_dict == {k: v for k, v in a.__dict__.items() if k not in ('unique_id', 'source_name')}
                        for a in self.schedule.agents])
        elif isinstance(agent_node_model, Model):
            return len(agent_node_model.schedule.agents)
        else:
            raise TypeError(f"get_mass expects a str, Agent, or Model for agent_node_model, but received "
                            f"{type(agent_node_model)}")
'''

    if 'get_mass_prop' in used_functions or 'get_mass_and_prop' in used_functions:
        code += '''
    def get_mass_prop(self, node, qry=None):
        """
        Returns the fraction of agents at the given node with attributes satisfying the given qry.
        :param node: A string corresponding to a node in the NetworkGrid
        :param qry: a GroupQry namedtuple
        :return: The fraction of agents at node with attributes satisfying qry (if qry=None, this will usually be 1),
                 *unless* the node is empty, in which case returns 0.
        """
        m = self.get_mass(node)
        return self.get_mass(node, qry) / m if m > 0 else 0
'''

    if 'get_mass_and_prop' in used_functions:
        code += '''
    def get_mass_and_prop(self, node, qry=None):
        """
        Returns a tuple containing the number of agents at the given node satisfying the qry and the fraction of
        agents at that site satisfying the qry.
        :param node: A string corresponding to a node in the NetworkGrid
        :param qry: a GroupQry namedtuple
        :return: a tuple containing the number of agents at the given node satisfying the qry and the fraction of
        agents at that site satisfying the qry.
        """
        return (self.get_mass(node, qry), self.get_mass_prop(node, qry))
'''

    if {'get_groups_mass', 'get_groups_mass_prop', 'get_groups_mass_and_prop'} & used_functions:
        code += '''
    def get_groups_mass(self, qry=None):
        """
        Returns the number of agents in the model that satisfy the given qry, or all agents if qry is None.
        :param qry: a GroupQry namedtuple
        :return: the number of agents in the model that satisfy the given qry
        """
        return len(self.get_groups(self, qry))
'''

    if 'get_groups_mass_prop' in used_functions or 'get_groups_mass_and_prop' in used_functions:
        code += '''
    def get_groups_mass_prop(self, qry=None):
        """
        Returns the fraction of agents in the model satisfying the given qry.
        :param qry: a GroupQry namedtuple
        :return: The fraction of agents in the model satisfying qry (if qry=None, this will usually be 1),
                 *unless* the model is empty, in which case returns 0.
        """
        m = len(self.schedule.agents)
        return self.get_groups_mass(qry) / m if m > 0 else 0
'''

    if 'get_groups_mass_and_prop' in used_functions:
        code += '''
    def get_groups_mass_and_prop(self, qry=None):
        """
        Returns a tuple containing the number of agents in the model satisfying the qry and the fraction of agents
        in the model satisfying the qry.
        :param qry: a GroupQry namedtuple
        :return: a tuple containing the number of agents in the model satisfying the qry and the fraction of agents 
        in the model satisfying the qry.
        """
        return (self.get_groups_mass(qry), self.get_groups_mass_prop(qry))
'''
    filename = _make_filename(class_name)

    # this is pretty lazy but a good safeguard
    code = code.replace("Site.AT", "'@'")

    with open(filename, 'w') as file:
        file.write(code)

    return filename


def create_json_data(sim: Simulation, name: str) -> Tuple[str, str, str]:
    """
    Creates JSON files storing data about the simulation Groups, Sites, and Rules.
    At this time, Resources are not handled as they seem to be seldom used.
    :param sim: The PyPRAM simulation
    :param name: The prefix of the files to create (without .json ending)
    :return: A tuple containing the group, site, and rule datafile names.
    """
    group_filename = _make_filename(f'{name}Groups', extension='.json')
    site_filename = _make_filename(f'{name}Sites', extension='.json')
    rule_filename = _make_filename(f'{name}Rules', extension='.json')

    # ---- Make Groups ----
    groups = sim.pop.get_groups()
    rounded_mass = iteround.saferound([group.m for group in groups], 0)
    # make (optional) name part of attr and ensure attributes are valid variable names
    # TODO: are there potential name clashes here since we aren't maintaining a namespace?
    attrs = [{**{mpi(k): v for k, v in group.get_attrs().items()}, "source_name": group.name} for group in groups]
    attrs = [{'attr': attr} for attr in attrs]
    rounded_mass = [{'m': int(m)} for m in rounded_mass]
    rels = [{'rel': group.rel} for group in groups]
    # print(attrs, '\n', rounded_mass, '\n', rels)
    # group_data = list(zip(attrs, rounded_mass, rels))
    group_data = []
    for i in range(len(groups)):  # can this be done with zip()? The solution evades me...
        group_data.append({**attrs[i], **rounded_mass[i], **rels[i]})

    with open(group_filename, 'w') as file:
        json.dump(group_data, file, indent=4)

    # ---- Make Sites ----
    sites = sim.pop.sites.values()  # keys are the hashes, which we'll also want for decoding group relations
    # make capacity_max an attribute and ensure attributes are valid variable names
    s_attrs = [{**{mpi(k): v for k, v in site.get_attr().items()}, "capacity_max": site.capacity_max} for site in sites]
    s_attrs = [{'attr': attr} for attr in s_attrs]
    s_names = [{'name': site.name} for site in sites]
    s_relnames = [{'rel_name': site.rel_name} for site in sites]
    s_hashes = [{'hash': h} for h in sim.pop.sites.keys()]

    site_data = []
    for i in range(len(sites)):
        site_data.append({**s_attrs[i], **s_names[i], **s_relnames[i], **s_hashes[i]})

    with open(site_filename, 'w') as file:
        json.dump(site_data, file, indent=4)

    # ---- Store Rule Attributes ----
    rules = sim.rules
    rule_data = [{**r.__dict__, 'rule_type': type(r).__name__} for r in rules]

    # handle group_qry, t, and i specially
    for data, rule in zip(rule_data, rules):
        if rule.group_qry:
            data['group_qry'] = {
                'attr': rule.group_qry.attr,
                'rel': rule.group_qry.rel,
                'cond': dill.dumps(rule.group_qry.cond).hex(),
                'full': rule.group_qry.full
            }

        if isinstance(rule.i, IterAlways):
            data['i'] = None
        elif isinstance(rule.i, IterPoint):
            data['i'] = rule.i.i
        elif isinstance(rule.i, IterInt):
            data['i'] = (rule.i.i0, rule.i.i1)
        elif isinstance(rule.i, IterSet):
            data['i'] = rule.i.i
        else:
            raise TypeError(f'Unexpected type for i: {type(rule.i)}')

        if isinstance(rule.t, TimeAlways):
            data['t'] = None
        elif isinstance(rule.t, TimePoint):
            data['t'] = rule.t.t
        elif isinstance(rule.t, TimeInt):
            data['t'] = (rule.t.t0, rule.t.t1)
        elif isinstance(rule.t, TimeSet):
            data['t'] = rule.t.t
        else:
            raise TypeError(f'Unexpected type for t: {type(rule.t)}')

    with open(rule_filename, 'w') as file:
        # rule attributes include some non-serializable objects, principally, `t` and `i`
        json.dump(rule_data, file, indent=4, default=lambda o: '<NOT SERIALIZABLE>')

    return group_filename, site_filename, rule_filename


def translate_rules(ruletypes: Iterable[type], writer: RuleWriter) -> Tuple[List[str], Set[str]]:
    """
    Translates each of a number of Rules, recursively handling superclasses until one with an apply method is found
    for each original rule. (This ignores any types passed to it not declared in a pram project file or in main.)
    :param ruletypes: A list of class types of rules to translate
    :param writer: A RuleWriter instance
    :return: A tuple containing:
        new_rules: A list of code blocks, each one corresponding to a translated rule
        rule_imports: A set of import statements extracted from each rule's source file. Not all import statements
                      may truly be needed but efforts are taken to skip imports to pram or pram2mesa.
    """
    new_rules = []
    rule_imports = []
    for t in ruletypes:
        if t.__module__.startswith(('pram', '__main__')):
            # if not hasattr(t, 'apply'):
            # this is hacky but overridden functions appear to be attributes not in __dict__
            if 'apply' not in t.__dict__.keys():
                r, i = translate_rules(t.__bases__, writer)
                new_rules.extend(r)
                rule_imports.extend(i)

            src = inspect.getsource(t)
            srcfile = inspect.getsourcefile(t)
            tree = ast.parse(src)
            new_rules.append(astor.to_source(writer.visit(tree)))
            rule_imports.extend(_extract_imports(srcfile))

    rule_imports = set(rule_imports)  # toss duplicate import statements

    return new_rules, rule_imports


def _extract_imports(file: str) -> List[str]:
    """
    A rudimentary function that searches a file for top-level import or from..import statements.
    This DOES NOT go through try/except blocks for imports or other similar structures.
    To maintain Mesa's independence from PRAM, all imports from pram or a package in pram are skipped.
    This also scraps relative imports since everything will be moving around,
    and imports of pram2mesa itself.
    :param file: A python source file.
    :return: A list of strings each containing some type of (non-pram) absolute import statement found in the file
             (newlines stripped)
    """
    with open(file, 'r') as f:
        lines = f.readlines()

        # note we cannot just do `and 'pram' not in x` in case we have `import supramolecular` or whatever
        pram = re.compile(r'\bpram(2mesa)?\b')
        # relative imports always use from..import style and always have a leading dot
        rel_imp = re.compile(r'from\s+\.')
        return [x.strip() for x in lines if x.startswith(('from', 'import'))
                and not pram.search(x) and not rel_imp.match(x)]


def _make_filename(name: str, extension: str = '.py') -> str:
    """
    Checks the local directory for a file or directory with the given name and extension (if applicable). If it exists,
    it strips the version (a number preceding the extension and following an underscore) and replaces it with a version
    one larger.

    For example, if 'foo.py' already exists:
    >>> _make_filename('foo')
    'foo_1.py'

    If 'bar.py', 'bar_1.py', and 'bar_2.py' already exist:
    >>> _make_filename('bar')
    'bar_3.py'

    If 'hello.py' does not already exist:
    >>> _make_filename('hello')
    'hello.py'


    :param name: The name (without file extension) to make a filename out of
    :param extension: The file extension, including the period. Default is .py
    :return: a valid, non-taken Python filename
    """
    filename = f'{name}{extension}'
    while os.path.exists(filename):
        # match name ending in an underscore followed by 1 or more digits (and then the file extension)
        match = re.match(fr".*?_(\d+){extension}$", filename)
        if match:
            version = match.groups()[0]
            filename = str(int(version) + 1).join(filename.rsplit(version, 1))
        else:
            filename = f'{name}_1{extension}'
        # print(filename)
    return filename


# ---------------------------------------------------------------------------------------------------------------------


def main():
    # SAMPLE SIMULATION FROM 09-segregation
    import os

    from pram.data import GroupSizeProbe, ProbeMsgMode, ProbePersistenceDB
    from pram.entity import Group, GroupQry, Site, GroupSplitSpec
    from pram.rule import SegregationModel
    from pram.sim import Simulation

    # -----------------------------------------------------------------------------------------------------------------
    # (1) Simulation (two locations)

    loc = [Site('a'), Site('b')]

    def gs(pop, group):
        return [
            GroupSplitSpec(p=0.7, attr_set={ 'foobar': 'foo' }),
            GroupSplitSpec(p=0.3, attr_set={ 'foobar': 'bar' })
        ]

    probe_loc = GroupSizeProbe.by_rel('loc', Site.AT, loc, msg_mode=ProbeMsgMode.DISP)
    probe_sim = GroupSizeProbe(
        name='sim',
        queries=[
            GroupQry(attr={'team': 'blue'}, rel={Site.AT: loc[0]}),
            GroupQry(attr={'team': 'red'}, rel={Site.AT: loc[0]}),
            GroupQry(attr={'team': 'blue'}, rel={Site.AT: loc[1]}),
            GroupQry(attr={'team': 'red'}, rel={Site.AT: loc[1]})
        ],
        qry_tot=None,
        persistence=ProbePersistenceDB(),
        msg_mode=ProbeMsgMode.DISP
    )

    s = (Simulation().
        set().
        pragma_autocompact(True).
        pragma_live_info(False).
        fn_group_setup(gs).
        done().
        add([
            SegregationModel('team', len(loc)),
            # TranslateEverything(),
            # LambdasAndArguments(),
            Group(m=200, attr={'team': 'blue'}, rel={Site.AT: loc[0], 'origin': loc[0]}),
            Group(m=300, attr={'team': 'blue'}, rel={Site.AT: loc[1], 'origin': loc[1]}),
            Group(m=100, attr={'team': 'red'}, rel={Site.AT: loc[0], 'origin': loc[0]}),
            Group(m=400, attr={'team': 'red'}, rel={Site.AT: loc[1], 'origin': loc[1]}),
            probe_loc,  # the distribution should tend to 50%-50%
            probe_sim  # mass should tend to move towards two of the four sites
            # fixed naming issue in pram/sim.py line 815
        ])
    )
    pram2mesa(s, 'TestAttributeAccess')

    # tree = ast.parse(
    #     # "g.get_attr(name)\n"
    #     # "x = g.ga(n2)\n"
    #     # "g.get_site_at()\n"
    #     # "g.get_rel(name)\n"
    #     # "x = g.gr(n2)\n"
    #     # "g.is_at_site(site)\n"
    #     # "if g.is_at_site_name(name):\n"
    #     # "   pass\n"
    #     # "g.is_void()\n"
    #     # "g.set_attr(name, value, do_force=True)\n"
    #     # "g.set_attrs({'one': 1, 'two': 2}, do_force=False)\n"
    #     # "g.set_rel(name, value)\n"
    #     # "g.set_rels({'three': 3, 'four': 4}, do_force=True)\n"
    #     # "g.split(specs)\n"
    #     # "print('hello world')"
    #     "return [\n"
    #     "   GroupSplitSpec(p=p0, attr_set={'sir': 'i', 'mood': 'sad'}, rel_set={'@': 'b'}, attr_del=['to_del']),\n"
    #     "   GroupSplitSpec(p=1-p0, attr_set={'mood': 'happy'}, rel_set={}, rel_del=[])\n"
    #     "]"
    #
    # )
    # RuleWriter().visit(tree)
    # print(astor.to_source(tree))

    # class TestRule(Rule):
    #     def apply(self, pop, group, iter, t):
    #         pass
    #
    # t = TestRule()
    # print(inspect.getsourcefile(type(t)))


if __name__ == '__main__':
    main()
