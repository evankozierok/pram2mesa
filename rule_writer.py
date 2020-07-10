"""
The RuleWriter class contains all the logic for transforming PyPRAM rules into rules applicable to mesa Agents.
"""

import ast
from ast import Add, And, Assign, Attribute, AugAssign, BinOp, BoolOp, Call, ClassDef, Compare, Constant, Dict, \
                DictComp, Eq, Expr, For, FunctionDef, GeneratorExp, If, IfExp, In, Index, Lambda, List, ListComp, \
                Load, Lt, LtE, Module, Name, NodeTransformer, Not, Return, Store, Subscript, Tuple, UnaryOp, With, \
                arg, arguments, comprehension, withitem

import warnings
from typing import Any, Optional, Union, Sequence

import typing

from make_python_identifier import make_python_identifier as mpi


class RuleWriter(NodeTransformer):
    # a list containing all the functions that require special functions to be added to the agent or model
    customs = ('copy', 'get_mass', 'has_attr', 'ha', 'has_rel', 'has_sites', 'hr', 'matches_qry', 'ga', 'get_attr',
               'get_groups', 'get_group', 'get_groups_mass', 'get_groups_mass_prop', 'get_groups_mass_and_prop')

    def __init__(self):
        self.used = set()  # which functions from customs are actually used?
        self.rule_names = []  # a list of rules that were processed

    def visit_Module(self, node: Module) -> Any:
        """
        Back-references each node with a parent (primarily for debugging).
        This is always called first since Module is a top-level node.
        :param node: A Module node
        :return: the node with parent back-references
        """
        for n in ast.walk(node):
            for child in ast.iter_child_nodes(n):
                child.parent = n
        node.parent = None
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node: ClassDef) -> Any:
        """
        Modifies a class definition (i.e. a Rule definition) in the following steps:
        * Handles all child nodes
        * Adds the rule's name to a list of rule names
        * tosses superclasses if the rule has an apply method; otherwise keeps them
        * adds a generic __call__ function that calls the rule's apply method if the agent and iteration match the
            rule's group_qry and iteration timer
            (if iteration and time are distinguished between, can add that here too)
        :param node: A ClassDef node; likely a PyPRAM Rule
        :return: a processed node
        """
        self.generic_visit(node)
        self.rule_names.append(node.name)
        bases = [] if any([isinstance(n, FunctionDef) and n.name == 'apply' for n in node.body]) else node.bases
        node.body.append(FunctionDef(
            name='__call__',
            args=arguments(
                args=[
                    arg(arg='self', annotation=None)
                ],
                posonlyargs=[],
                kwonlyargs=[],
                defaults=[],
                vararg=None,
                kwarg=None,
                kw_defaults=None
            ),
            body=[
                If(
                    test=UnaryOp(
                        op=Not(),
                        operand=Call(
                            func=Attribute(
                                value=Name(id='self', ctx=Load()),
                                attr=Attribute(
                                    value=Name(id='agent', ctx=Load()),
                                    attr='matches_qry'
                                )
                            ),
                            args=[Attribute(
                                value=Name(id='self', ctx=Load()),
                                attr='group_qry'
                            )],
                            keywords=[]
                        ),
                    ),
                    body=[Return(value=None)],
                    orelse=[]
                ),
                If(
                    test=UnaryOp(
                        op=Not(),
                        operand=Attribute(
                            value=Name(id='self', ctx=Load()),
                            attr='i'
                        )
                    ),
                    body=[RuleWriter._apply_call()],
                    orelse=[
                        If(
                            test=BoolOp(
                                op=And(),
                                values=[
                                    Call(
                                        func=Name(id='isinstance', ctx=Load()),
                                        args=[
                                            Attribute(
                                                value=Name(id='self', ctx=Load()),
                                                attr='i'
                                            ),
                                            Name(id='int', ctx=Load())
                                        ],
                                        keywords=[]
                                    ),
                                    Compare(
                                        left=Attribute(
                                            value=Attribute(
                                                value=Name(id='self', ctx=Load()),
                                                attr='model',
                                                ctx=Load()
                                            ),
                                            attr='time',
                                            ctx=Load()
                                        ),
                                        ops=[Eq()],
                                        comparators=[Attribute(
                                            value=Name(id='self', ctx=Load()),
                                            attr='i'
                                        )]
                                    )
                                ]
                            ),
                            body=[RuleWriter._apply_call()],
                            orelse=[If(
                                test=Call(
                                    func=Name(id='isinstance', ctx=Load()),
                                    args=[
                                        Attribute(
                                            value=Name(id='self', ctx=Load()),
                                            attr='i'
                                        ),
                                        Name(id='list', ctx=Load())
                                    ],
                                    keywords=[]
                                ),
                                body=[If(
                                    test=BoolOp(
                                        op=And(),
                                        values=[
                                            Compare(
                                                left=Subscript(
                                                    value=Attribute(
                                                        value=Name(id='self', ctx=Load()),
                                                        attr='i'
                                                    ),
                                                    slice=Index(value=Constant(value=1)),
                                                    ctx=Load()
                                                ),
                                                ops=[Eq()],
                                                comparators=[Constant(value=0)]
                                            ),
                                            Compare(
                                                left=Attribute(
                                                    value=Attribute(
                                                        value=Name(id='self', ctx=Load()),
                                                        attr='model',
                                                        ctx=Load()
                                                    ),
                                                    attr='time',
                                                    ctx=Load()
                                                ),
                                                ops=[LtE()],
                                                comparators=[Subscript(
                                                    value=Attribute(
                                                        value=Name(id='self', ctx=Load()),
                                                        attr='i'
                                                    ),
                                                    slice=Index(value=Constant(value=0)),
                                                    ctx=Load()
                                                )]
                                            )
                                        ]
                                    ),
                                    body=[RuleWriter._apply_call()],
                                    orelse=[If(
                                        test=Compare(
                                            left=Subscript(
                                                value=Attribute(
                                                    value=Name(id='self', ctx=Load()),
                                                    attr='i'
                                                ),
                                                slice=Index(value=Constant(value=0)),
                                                ctx=Load()
                                            ),
                                            ops=[LtE(), LtE()],
                                            comparators=[
                                                Attribute(
                                                    value=Attribute(
                                                        value=Name(id='self', ctx=Load()),
                                                        attr='model',
                                                        ctx=Load()
                                                    ),
                                                    attr='time',
                                                    ctx=Load()
                                                ),
                                                Subscript(
                                                    value=Attribute(
                                                        value=Name(id='self', ctx=Load()),
                                                        attr='i'
                                                    ),
                                                    slice=Index(value=Constant(value=1)),
                                                    ctx=Load()
                                                )
                                            ]
                                        ),
                                        body=[RuleWriter._apply_call()],
                                        orelse=[]
                                    )]
                                )],
                                orelse=[If(
                                    test=BoolOp(
                                        op=And(),
                                        values=[
                                            Call(
                                                func=Name(id='isinstance', ctx=Load()),
                                                args=[
                                                    Attribute(
                                                        value=Name(id='self', ctx=Load()),
                                                        attr='i'
                                                    ),
                                                    Name(id='set', ctx=Load())
                                                ],
                                                keywords=[]
                                            ),
                                            Compare(
                                                left=Attribute(
                                                    value=Attribute(
                                                        value=Name(id='self', ctx=Load()),
                                                        attr='model',
                                                        ctx=Load()
                                                    ),
                                                    attr='time',
                                                    ctx=Load()
                                                ),
                                                ops=[In()],
                                                comparators=[Attribute(
                                                    value=Name(id='self', ctx=Load()),
                                                    attr='i'
                                                )]
                                            )
                                        ]
                                    ),
                                    body=[RuleWriter._apply_call()],
                                    orelse=[]
                                )]
                            )]
                        )
                    ]
                )
            ],
            decorator_list=[]
        ))

        return ClassDef(
            name=node.name,
            # bases=[],  # toss out inheritances. NOTE: This might be sketchy
            bases=bases,  # ^ it was sketchy
            keywords=[],
            body=node.body,
            decorator_list=node.decorator_list
        )

    def visit_FunctionDef(self, node: FunctionDef) -> Any:
        """
        Edits an __init__ function definition, allowing the Rule to be bound to an agent and model, and attempting to
        read rule data from the relevant JSON file
        :param node: A FunctionDef node
        :return: If node represents an __init__ function, returns node processed as described above.
                 Otherwise, returns node with all child nodes handled
        """
        if node.name != '__init__':
            self.generic_visit(node)
            return node

        return FunctionDef(
            name='__init__',
            args=arguments(
                args=[
                    arg(arg='self', annotation=None),
                    arg(arg='agent', annotation=None)
                ],
                posonlyargs=[],
                kwonlyargs=[],
                defaults=[],
                vararg=None,
                kwarg=None,
                kw_defaults=None
            ),
            body=[
                Assign(
                    targets=[Attribute(
                        value=Name(id='self', ctx=Load()),
                        attr='agent',
                        ctx=Store()
                    )],
                    value=Name(id='agent', ctx=Load())
                ),
                Assign(
                    targets=[Attribute(
                        value=Name(id='self', ctx=Load()),
                        attr='model',
                        ctx=Store()
                    )],
                    value=Attribute(
                        value=Name(id='agent', ctx=Load()),
                        attr='model',
                        ctx=Load()
                    )
                ),
                With(
                    items=[withitem(
                        context_expr=Call(
                            func=Name(id='open', ctx=Load()),
                            args=[
                                Name(id='rule_file', ctx=Load()),
                                Constant(value='r')
                            ],
                            keywords=[]
                        ),
                        optional_vars=Name(id='file', ctx=Store())
                    )],
                    body=[
                        Assign(
                            targets=[Name(id='j', ctx=Store())],
                            value=Call(
                                func=Attribute(
                                    value=Name(id='json', ctx=Load()),
                                    attr='load',
                                    ctx=Load()
                                ),
                                args=[Name(id='file', ctx=Load())],
                                keywords=[]
                            )
                        ),
                        Assign(
                            targets=[Name(id='data', ctx=Store())],
                            value=Call(
                                func=Name(id='next', ctx=Load()),
                                args=[
                                    GeneratorExp(
                                        elt=Name(id='d', ctx=Load()),
                                        generators=[comprehension(
                                            target=Name(id='d', ctx=Store()),
                                            iter=Name(id='j', ctx=Load()),
                                            ifs=[Compare(
                                                left=Subscript(
                                                    value=Name(id='d', ctx=Load()),
                                                    slice=Index(value=Constant(value='rule_type')),
                                                    ctx=Load()
                                                ),
                                                ops=[Eq()],
                                                comparators=[Attribute(
                                                    value=Call(
                                                        func=Name(id='type', ctx=Load()),
                                                        args=[Name(id='self', ctx=Load())],
                                                        keywords=[]
                                                    ),
                                                    attr='__name__',
                                                    ctx=Load()
                                                )]
                                            )]
                                        )]
                                    ),
                                    # superclasses will not have any data stored (but we don't really care)
                                    Dict(keys=[], values=[])
                                ],
                                keywords=[]
                            )
                        ),
                        If(
                            test=Name(id='data', ctx=Load()),
                            body=[
                                Assign(
                                    targets=[Name(id='gq', ctx=Store())],
                                    value=Subscript(
                                        value=Name(id='data', ctx=Load()),
                                        slice=Index(value=Constant(value='group_qry')),
                                        ctx=Load()
                                    )
                                ),
                                If(
                                    test=Name(id='gq', ctx=Load()),
                                    body=[Assign(
                                        targets=[Subscript(
                                            value=Name(id='data', ctx=Load()),
                                            slice=Index(value=Constant(value='group_qry')),
                                            ctx=Store()
                                        )],
                                        value=Call(
                                            func=Name(id='GroupQry', ctx=Load()),
                                            args=[
                                                Subscript(
                                                    value=Name(id='gq', ctx=Load()),
                                                    slice=Index(value=Constant(value='attr')),
                                                    ctx=Load()
                                                ),
                                                Subscript(
                                                    value=Name(id='gq', ctx=Load()),
                                                    slice=Index(value=Constant(value='rel')),
                                                    ctx=Load()
                                                ),
                                                Call(
                                                    func=Attribute(
                                                        value=Name(id='dill', ctx=Load()),
                                                        attr='loads'
                                                    ),
                                                    args=[Call(
                                                        func=Attribute(
                                                            value=Name(id='bytes', ctx=Load()),
                                                            attr='fromhex'
                                                        ),
                                                        args=[Subscript(
                                                            value=Name(id='gq', ctx=Load()),
                                                            slice=Index(value=Constant(value='cond')),
                                                            ctx=Load()
                                                        )],
                                                        keywords=[]
                                                    )],
                                                    keywords=[]
                                                ),
                                                Subscript(
                                                    value=Name(id='gq', ctx=Load()),
                                                    slice=Index(value=Constant(value='full')),
                                                    ctx=Load()
                                                ),
                                            ],
                                            keywords=[]
                                        )
                                    )],
                                    orelse=[]
                                )
                            ],
                            orelse=[]
                        ),
                        Expr(value=Call(
                            func=Attribute(
                                value=Attribute(
                                    value=Name(id='self', ctx=Load()),
                                    attr='__dict__',
                                    ctx=Load()
                                ),
                                attr='update',
                                ctx=Load()
                            ),
                            args=[Name(id='data', ctx=Load())],
                            keywords=[]
                        ))
                    ]
                )
            ],
            decorator_list=[]
        )

    def visit_Call(self, node: Call) -> Any:
        """
        Attempts to translate a function call in the following steps:
        * handles all child nodes
        * Searches a lookup table of PRAM functions for the function name. If found, passes the node to the relevant
            translation method; otherwise leaves it as is (i.e. ignore generic python functions or other libraries)
        * if the function is one that requires a special function in the Agent or Model class, marks that as so
        :param node: A function Call node
        :return: The processed node
        """
        self.generic_visit(node)
        if isinstance(node.func, Name):
            fname = node.func.id
        elif isinstance(node.func, Attribute):
            fname = node.func.attr
        else:
            # raise TypeError(f"The Call node ({node})'s func should be a Name or Attribute, "
            #                 f"but was of type {type(node.func)}")  # TODO: check if we should be raising an error here
            fname = ''

        f = RuleWriter.lookup.get(fname, None)
        if f:  # don't do anything with a function not listed here
            if fname in RuleWriter.customs:
                self.used.add(fname)

            return f(node)

        return node

    def visit_Attribute(self, node: Attribute) -> Any:
        """
        It is reasonable to suppose a user might want to access the GroupPopulation's sites or groups, and there are no
        PRAM methods for doing so. Thus, if we think there is an access to pop.sites or pop.groups, we turn it into
        something usable here. (Other Attribute access is left untouched)
        :param node: an Attribute node
        :return: The processed node
        """
        self.generic_visit(node)
        if isinstance(node.value, Name) and node.value.id == 'pop':
            if node.attr == 'sites':
                return Attribute(
                    value=node.value,
                    attr='site_hashes',
                    ctx=Load()
                )
            elif node.attr == 'groups':
                return DictComp(
                    key=Attribute(
                        value=Name(id='a', ctx=Load()),
                        attr='unique_id',
                        ctx=Load()
                    ),
                    value=Name(id='a', ctx=Load()),
                    generators=[comprehension(
                        target=Name(id='a', ctx=Store()),
                        iter=Attribute(
                            value=Attribute(
                                value='pop',
                                attr='schedule',
                                ctx=Load()
                            ),
                            attr='agents',
                            ctx=Load()
                        ),
                        ifs=[]
                    )]
                )

        return node

    def visit_Return(self, node: Return) -> Any:  # TODO: ensure we only screw with returns where we should
        """
        Translates a return statement into a series of appropriate calls.
        * 'return None' becomes the generic 'return'
        * return statements that return lists or tuples are prepended with a random number call and then expanded into
            chained if-else's of attribute setting/deletion
        * return statements that return a list comprehension are again prepended with a random number call, and then
            attempt to expand the list comprehension into a for loop.
        For more details, see `RuleWriter._parse_gss_call`.
        :param node: a Return node
        :return: A series of nodes that are equivalent to the original node, or the original node
        """
        self.generic_visit(node)
        if isinstance(node.value, Constant):
            if node.value.value is None:
                return Return(value=None)  # turns 'return None' into generic 'return'
            else:
                # raise ValueError(f"The Return node ({node}) had a value of type Constant, but the Constant had value "
                #                  f"{node.value.value}, not `None`")
                return node

        if isinstance(node.value, (List, Tuple)):
            # ignore return statements that aren't returning GSS calls
            elts_are_gss_calls = [isinstance(e, Call) and isinstance(e.func, Name) and e.func.id == 'GroupSplitSpec'
                                  for e in node.value.elts]
            if not all(elts_are_gss_calls):
                # if some, but not all values in the list/tuple are GSS calls, that's a bad return construction
                if any(elts_are_gss_calls):
                    raise ValueError(f"The Return node ({node}) contains both calls to GroupSplitSpec and other calls")
                return node

            # special case for single value collections (i.e. probability 1)
            if len(node.value.elts) == 1:
                calls, _ = RuleWriter._parse_gss_call(node.value.elts[0])
                return calls

            cml_probs = []

            # this starting call (technically an Assign) is currently `_x = pop.random.random()`.
            # this is a placeholder for a better sampling method to come.
            ifs = [Assign(
                targets=[Name(id='_x', ctx=Store())],
                value=Call(
                    func=Attribute(
                        value=Attribute(
                            value=Name(id='pop', ctx=Load()),
                            attr='random',
                            ctx=Load()
                        ),
                        attr='random',
                        ctx=Load()
                    ),
                    args=[],
                    keywords=[]
                )
            )]
            for elt in node.value.elts[:-1]:
                # elt is (should be) a Call node creating a GroupSplitSpec object
                calls = []
                c, p = RuleWriter._parse_gss_call(elt)
                calls.extend(c)
                cml_probs.append(p)

                addition = RuleWriter._sum_nodes(cml_probs)

                orelse = []
                if elt == node.value.elts[-2]:  # the second to last node becomes an if/else
                    # process node.value.elts[-1] as orelse section
                    orelse, _ = RuleWriter._parse_gss_call(node.value.elts[-1])  # ignore p

                ifs.append(If(
                    test=Compare(
                        left=Name(id='_x', ctx=Load()),
                        ops=[Lt()],
                        comparators=[addition]
                    ),
                    body=calls,
                    orelse=orelse
                ))

            return ifs

        if isinstance(node.value, ListComp):
            # TODO: this may need revisiting

            # skip list comprehensions that aren't of GSS calls
            if not (isinstance(node.value.elt, Call) and isinstance(node.value.elt.func, Name)
                    and node.value.elt.func.id == 'GroupSplitSpec'):
                return node

            calls, p = RuleWriter._parse_gss_call(node.value.elt)

            statements = [
                Assign(
                    targets=[Name(id='_cml_prob', ctx=Store())],
                    value=Constant(value=0.0)
                ),
                Assign(
                    targets=[Name(id='_x', ctx=Store())],
                    value=Call(
                        func=Attribute(
                            value=Attribute(
                                value=Name(id='pop', ctx=Load()),
                                attr='random',
                                ctx=Load()
                            ),
                            attr='random',
                            ctx=Load()
                        ),
                        args=[],
                        keywords=[]
                    )
                ),
                For(
                    target=node.value.generators[0].target,
                    iter=node.value.generators[0].iter,
                    body=[If(
                        test=BoolOp(
                            op=And(),
                            values=node.value.generators[0].ifs
                        ),
                        body=[
                            AugAssign(
                                target=Name(id='_cml_prob', ctx=Store()),
                                op=Add(),
                                value=p
                            ),
                            If(
                                test=Compare(
                                    left=Name(id='_x', ctx=Load()),
                                    ops=[Lt()],
                                    comparators=[Name(id='_cml_prob', ctx=Load())]
                                ),
                                body=calls,
                                orelse=[]
                            )
                        ],
                        orelse=[]
                    )],
                    orelse=[]
                )
            ]

            return statements

        if hasattr(node.parent, 'name') and node.parent.name == 'apply':
            raise TypeError(f"The Return node ({node})'s value should be a List, ListComp, Tuple, or Constant (with "
                            f"value `None`), but was of type {type(node.value)}")

        return node

    @staticmethod
    def _apply_call() -> Call:
        """
        A shorthand method for `self.apply(self.model, self.agent, self.model.time, self.model.time)`
        :return: A Call node equivalent to the above line
        """
        return Call(
            func=Attribute(
                value=Name(id='self', ctx=Load()),
                attr='apply',
                ctx=Load()
            ),
            args=[
                Attribute(
                    value=Name(id='self', ctx=Load()),
                    attr='model',
                    ctx=Load()
                ),
                Attribute(
                    value=Name(id='self', ctx=Load()),
                    attr='agent',
                    ctx=Load()
                ),
                Attribute(
                    value=Attribute(
                        value=Name(id='self', ctx=Load()),
                        attr='model',
                        ctx=Load()
                    ),
                    attr='time',
                    ctx=Load()
                ),
                #  right now iter and t are the same. If PRAM ever properly distinguishes them this could change
                Attribute(
                    value=Attribute(
                        value=Name(id='self', ctx=Load()),
                        attr='model',
                        ctx=Load()
                    ),
                    attr='time',
                    ctx=Load()
                )
            ],
            keywords=[]
        )

    @staticmethod
    def _get_argument(node: Call, pos: int, name: str) -> Any:
        """
        Finds the argument in position pos, or the named argument in keywords if the positional argument list is not
        that long. If the argument can't be found, returns a Constant node with value None
        :param node: a Call node
        :param pos: a positive integer
        :param name: A string of the argument name, to be used if the positional check fails
        :return: the argument node, or a node representing None
        """
        if pos < len(node.args):
            return node.args[pos]
        else:
            for kw in node.keywords:
                if kw.arg == name:
                    return kw.value

        return Constant(value=None)

    @staticmethod
    def _get_ancestor(node: Any, type: type) -> Optional[Any]:
        """
        Determines if the given node has an ancestor of the given type and returns the first applicable node (or None)
        This function thus also serves as a tester of whether such an ancestor exists.
        :param node: the node to examine (should be preprocessed by RuleWriter's visit_Module)
        :param type: a class type
        :return: The first of node's ancestors of the matching type; if no ancestor is of the type, returns None
        """
        # eventually, Module has a specified parent of None
        if node is None:
            return None
        try:
            p = node.parent
        except AttributeError:
            return None

        if isinstance(p, type):
            return p
        return RuleWriter._get_ancestor(p, type)

    @staticmethod
    def _parse_gss_call(elt: Call) -> typing.Tuple[typing.List, Optional[Any]]:
        """
        Translates a GroupSplitSpec definition Call into a series of Calls to getattr and delattr, followed by a Return.
        Also returns the probability value.
        :param elt: A Call node, hopefully calling a GroupSplitSpec initialization
        :return: A tuple containing a list of Call nodes, and a node representing the probability that those calls
                 should occur at
        """
        calls = []
        p = None
        for kw in elt.keywords:
            if kw.arg == 'p':
                p = kw.value
            if kw.arg.endswith("set"):
                # kw.value is (should be) a Dict node
                # one special case is Group.VOID which is an attribute
                if isinstance(kw.value, Attribute) \
                        and isinstance(kw.value.value, Name) and kw.value.value.id == 'Group' \
                        and kw.value.attr == 'VOID':
                    kw.value = Dict(keys=[Constant(value='__void__')], values=[Constant(value=True)])

                # process setting position specially (i.e. pop.grid.move_agent(group, value) )
                pos_change = next(iter([
                    key for key in kw.value.keys
                    if (isinstance(key, Constant) and key.value == '@')
                       or (isinstance(key, Attribute)
                           and getattr(key.value, 'id', False) == 'Site'  # implies a Name
                           and key.attr == 'AT')
                ]), None)
                if pos_change:
                    pos_change_index = kw.value.keys.index(pos_change)
                    kw.value.keys.pop(pos_change_index)  # don't need a setattr for this
                    calls.append(Expr(Call(
                        func=Attribute(
                            value=Attribute(
                                value=Name(id='pop', ctx=Load()),
                                attr='grid',
                                ctx=Load()
                            ),
                            attr='move_agent',
                            ctx=Load()
                        ),
                        args=[
                            Name(id='group', ctx=Load()),
                            kw.value.values.pop(pos_change_index)
                        ],
                        keywords=[]
                    )))

                calls.extend([Expr(Call(
                    func=Name(id='setattr', ctx=Load()),
                    args=[
                        Name(id='group', ctx=Load()),
                        # ensure we are setting appropriate variables
                        Constant(value=mpi(key.value)[0]) if isinstance(key, Constant) else key,
                        value
                    ],
                    keywords=[]
                )) for key, value in zip(kw.value.keys, kw.value.values)])
            if kw.arg.endswith("del"):
                # kw.value is (should be) a Set node
                calls.extend([Expr(Call(
                    func=Name(id='delattr', ctx=Load()),
                    args=[
                        Name(id='group', ctx=Load()),
                        Constant(value=mpi(key.value)[0]) if isinstance(key, Constant) else key
                    ],
                    keywords=[]
                )) for key in kw.value.elts])

        calls.append(Return(value=None))
        return calls, p

    @staticmethod
    def _pop_or_g_model(node: Any) -> Union[Attribute, Name]:
        """
        Determines whether this node is likely in a lambda function for a GroupQry, and returns a node
        representing either `pop` or `g.model` (where g is the singular argument of the lambda function).
        :param node: the node to examine
        :return: an Attribute or Name node
        """
        lamb = RuleWriter._get_ancestor(node, Lambda)
        # if we are in a lambda function with one argument, `pop` becomes `g.model` (or similar)
        if lamb and len(lamb.args.args) == 1 and len(lamb.args.posonlyargs) == 0 and len(lamb.args.kwonlyargs) == 0:
            val = Attribute(
                value=Name(id=lamb.args.args[0].arg, ctx=Load()),  # yes that id= is legit. I know.
                attr='model',
                ctx=Load()
            )
        else:
            val = Name(id='pop', ctx=Load())
        return val

    @staticmethod
    def _sum_nodes(nodes: Sequence) -> Union[BinOp, Any]:
        """
        Recursively turns a list of nodes into an BinOp node representing their summation
        :param nodes: A list of nodes to be summed
        :return: A BinOp node representing their summation (or the original node if only one node is passed)
        """
        if len(nodes) <= 1:
            return nodes[0]

        return BinOp(
            left=RuleWriter._sum_nodes(nodes[:-1]),
            op=Add(),
            right=nodes[-1]
        )

    # ------------------------------- FUNCTION TRANSLATIONS -------------------------------

    @staticmethod
    def t_copy(node):
        """
        This method does not change anything, but by being called, flags that a copy method (defined elsewhere)
        should be added to the Mesa Agent class.
        """
        return node

    @staticmethod
    def t_get_attr(node):
        """
        Both the Group and Site class have a get_attr with an (almost) identical argument signature. As such,
        a custom function is needed that will test the type of object get_attr is being called for - a string Node in
        the NetworkGrid (a Site) or an Agent (a Group). As with other Site methods, this is a Model-level method for
        easier access to the grid.

        Translates a call like:
            x.get_attr(name)
                OR
            s.get_attr()
        into a call like:
            pop.get_attr(x, name)
                OR
            pop.get_attr(s)

        Also flags that a get_attr method (defined elsewhere) should be added to the Mesa Model class.
        :param node:
        :return:
        """
        attr_val = RuleWriter._pop_or_g_model(node)

        name = RuleWriter._get_argument(node, 0, 'name')
        return Call(
            func=Attribute(
                value=attr_val,
                attr='get_attr',
                ctx=Load()
            ),
            args=[
                node.func.value,  # caller
                name
            ],
            keywords=[]
        )
        # """
        # Translates a call like:
        #     g.get_attr(name)
        # into a call like:
        #     getattr(g, name, g.namespace[name])
        # """
        # return Call(
        #     func=Name(id='getattr', ctx=Load()),
        #     args=[
        #         node.func.value,  # caller
        #         node.args[0],  # the first (and only?) argument passed to get_attr
        #         Subscript(
        #             value=Attribute(
        #                 value=node.func.value,
        #                 attr=Name(id='namespace', ctx=Load()),
        #                 ctx=Load()
        #             ),
        #             slice=Index(value=node.args[0]),
        #             ctx=Load()
        #         )
        #     ],
        #     keywords=[]
        # )

    @staticmethod
    def t_ga(node):
        """See t_get_attr"""
        return RuleWriter.t_get_attr(node)

    @staticmethod
    def t_get_attrs(node):
        """
        Translates a call like:
            g.get_attrs()
        into a call like:
            {k: getattr(g, k) for k in g._attr}
        :param node:
        :return:
        """
        # warnings.warn('Translating calls to get_attrs is currently not supported. These calls will not be changed')

        return DictComp(
            key=Name(id='k', ctx=Load()),
            value=Call(
                func=Name(id='getattr', ctx=Load()),
                args=[
                    node.func.value,  # caller
                    Name(id='k', ctx=Load())
                ],
                keywords=[]
            ),
            generators=[comprehension(
                target=Name(id='k', ctx=Store()),
                iter=Attribute(
                    value=node.func.value,  # caller
                    attr='_attr',
                    ctx=Load()
                ),
                ifs=[]
            )]
        )

    @staticmethod
    def t_get_hash(node):
        warnings.warn('Although Mesa Agents are technically hashable as most class instances are, their hashes are '
                      'unique to each instance and as such cannot be used for comparison as in PRAM. Calls to '
                      'get_hash will not be translated.')
        return node

    @staticmethod
    def t_get_mass(node):
        """
        Translates a call like:
            x.get_mass()
                OR
            s.get_mass(qry)
        into a call like:
            pop.get_mass(s, qry)
        Also, by being called, flags that both a get_mass and get_groups function (defined elsewhere) should be added
        to the Mesa Model class.
        """
        attr_val = RuleWriter._pop_or_g_model(node)

        qry = RuleWriter._get_argument(node, 0, 'qry')
        return Call(
            func=Attribute(
                value=attr_val,
                attr='get_mass',
                ctx=Load()
            ),
            args=[
                node.func.value,  # caller
                qry
            ],
            keywords=[]
        )

    @staticmethod
    def t_get_site_at(node):
        """
        Translates a call like:
            g.get_site_at()
        into a call like:
            g.pos
        :param node:
        :return:
        """
        return Attribute(
            value=node.func.value,  # caller
            attr='pos',
            ctx=Load()
        )

    @staticmethod
    def t_get_rel(node):
        """
        Translates a call like:
            g.get_rel(name)
        into a call like:
            # g.pos if name == '@' else getattr(g, name, g.namespace[name])
            g.pos if name == '@' else getattr(g, mpi(name)[0])
        :param node:
        :return:
        """
        name = RuleWriter._get_argument(node, 0, 'name')
        # mod_name = name
        # if isinstance(name, Constant) and isinstance(name.value, str):
        #     mod_name, _ = mpi(name)

        return IfExp(
            test=Compare(
                left=name,
                ops=[Eq()],
                comparators=[Constant(value='@')]
            ),
            body=RuleWriter.t_get_site_at(node),
            # orelse=RuleWriter.t_get_attr(node)
            orelse=Call(
                func=Name(id='getattr', ctx=Load()),
                args=[
                    node.func.value,  # caller
                    Subscript(
                        value=Call(
                            func=Name(id='mpi', ctx=Load()),
                            args=[name],
                            keywords=[]
                        ),
                        slice=Index(value=Constant(value=0)),
                        ctx=Load()
                    )
                ],
                keywords=[]
            )
        )

    @staticmethod
    def t_get_rels(node):
        """
        Translates a call like:
            g.get_rels()
        into a call like:
            {k: getattr(g, k) for k in g._rel}
        :param node:
        :return:
        """
        # warnings.warn('Translating calls to get_attrs is currently not supported. These calls will not be changed')

        return DictComp(
            key=Name(id='k', ctx=Load()),
            value=Call(
                func=Name(id='getattr', ctx=Load()),
                args=[
                    node.func.value,  # caller
                    Name(id='k', ctx=Load())
                ],
                keywords=[]
            ),
            generators=[comprehension(
                target=Name(id='k', ctx=Store()),
                iter=Attribute(
                    value=node.func.value,  # caller
                    attr='_rel',
                    ctx=Load()
                ),
                ifs=[]
            )]
        )

    @staticmethod
    def t_gr(node):
        """See t_get_rel"""
        return RuleWriter.t_get_rel(node)

    @staticmethod
    def t_ha(node):
        """
        Translates calls to ha into equivalent calls to has_attr.
        Also, by being called, flags that a has_attr method (defined elsewhere) should be added to the Mesa Agent class.
        See has_attr for details
        :param node:
        :return:
        """
        return Call(
            func=Attribute(
                value=node.func.value,
                attr='has_attr',
                ctx=node.func.ctx
            ),
            args=node.args,
            keywords=node.keywords
        )

    @staticmethod
    def t_has_attr(node):
        """
        This method does not change anything, but by being called, flags that a has_attr method (defined elsewhere)
        should be added to the Mesa Agent class.
        """
        return node

    @staticmethod
    def t_has_rel(node):
        """
        This method does not change anything, but by being called, flags that a has_rel method (defined elsewhere)
        should be added to the Mesa Agent class.
        """
        return node

    @staticmethod
    def t_has_sites(node):
        """
        Translates calls to has_sites into equivalent calls to has_rel.
        Also, by being called, flags that a has_rel method (defined elsewhere) should be added to the Mesa Agent class.
        See has_rel for details
        :param node:
        :return:
        """
        warnings.warn("Calls to function has_sites may be unintended... perhaps you want has_rel instead?")
        return Call(
            func=Attribute(
                value=node.func.value,
                attr='has_rel',
                ctx=node.func.ctx
            ),
            args=node.args,
            keywords=node.keywords
        )

    @staticmethod
    def t_hr(node):
        """
        Translates calls to hr into equivalent calls to has_rel.
        Also, by being called, flags that a has_rel method (defined elsewhere) should be added to the Mesa Agent class.
        See has_rel for details
        :param node:
        :return:
        """
        return Call(
            func=Attribute(
                value=node.func.value,
                attr='has_rel',
                ctx=node.func.ctx
            ),
            args=node.args,
            keywords=node.keywords
        )

    @staticmethod
    def t_is_at_site(node):
        """
        Translates a call like:
            g.is_at_site(site)
        into a call like:
            g.pos == site
        :param node:
        :return:
        """
        site = RuleWriter._get_argument(node, 0, 'site')
        # this function may be triggered by is_at_site, which takes a `site`, or is_at_site_name, which takes a `name`
        if isinstance(site, Constant) and site.value is None:
            site = RuleWriter._get_argument(node, 0, 'name')

        return Compare(
            left=RuleWriter.t_get_site_at(node),
            ops=[Eq()],
            comparators=[site]
        )

    @staticmethod
    def t_is_at_site_name(node):
        """See t_is_at_site. Because of the way Mesa nodes work here, these *should* be the same..."""
        return RuleWriter.t_is_at_site(node)

    @staticmethod
    def t_is_void(node):
        """
        Translates a call like:
            g.is_void()
        into a call like:
            getattr(g, '__void__', False)
        :param node:
        :return:
        """
        return Call(
            func=Name(id='getattr', ctx=Load),
            args=[
                node.func.value,  # caller
                Constant(value='__void__'),
                Constant(value=False)
            ],
            keywords=[]
        )

    @staticmethod
    def t_matches_qry(node):
        """
        This method does not change anything, but by being called, flags that a matches_qry method (defined elsewhere)
        should be added to the Mesa Agent class.
        """
        # warnings.warn('Translating calls to matches_qry is currently not supported. These calls will not be changed')
        return node

    @staticmethod
    def t_set_attr(node):
        """
        Translates a call like:
            g.set_attr(name, value, do_force=bool_val)
        into a call like:
            setattr(g, mpi(name)[0], value)
        :param node:
        :return:
        """
        name = RuleWriter._get_argument(node, 0, 'name')
        value = RuleWriter._get_argument(node, 1, 'value')
        return Call(
            func=Name(id='setattr', ctx=Load()),
            args=[
                node.func.value,  # caller
                Subscript(
                    value=Call(
                        func=Name(id='mpi', ctx=Load()),
                        args=[name],
                        keywords=[]
                    ),
                    slice=Index(value=Constant(value=0)),
                    ctx=Load()
                ),
                value
            ],
            keywords=[]
        )

    @staticmethod
    def t_set_attrs(node):
        """
        Translates a call like:
            g.set_attrs(attrs, do_force=bool_val)
        into a call like:
            for name, value in attrs.items():
                setattr(a, mpi(name)[0], value)
        :param node:
        :return:
        """
        attrs = RuleWriter._get_argument(node, 0, 'attrs')

        return For(  # for...
            target=Tuple(  # k, v...
                elts=[
                    Name(id='name', ctx=Store()),
                    Name(id='value', ctx=Store())
                ],
                ctx=Store()
            ),  # in...
            iter=Call(  # attrs.items(): \n...
                func=Attribute(
                    value=attrs,
                    attr=Name(id='items', ctx=Load()),
                    ctx=Load()
                ),
                args=[],
                keywords=[]
            ),
            body=[Call(  # setattr(a, name, value)
                func=Name(id='setattr', ctx=Load()),
                args=[
                    node.func.value,  # caller
                    Subscript(
                        value=Call(
                            func=Name(id='mpi', ctx=Load()),
                            args=[Name(id='name', ctx=Load())],
                            keywords=[]
                        ),
                        slice=Index(value=Constant(value=0)),
                        ctx=Load()
                    ),
                    Name(id='value', ctx=Load())
                ],
                keywords=[]
            )],
            orelse=[]
        )

    @staticmethod
    def t_set_rel(node):
        """
        Translates a call like:
            g.set_rel(name, value, do_force=bool_val)
        into a call like:
            if name == '@':
                pop.grid.move_agent(g, value)
            else:
                setattr(a, mpi(name)[0], value)
        :param node:
        :return:
        """
        name = RuleWriter._get_argument(node, 0, 'name')
        value = RuleWriter._get_argument(node, 1, 'value')

        return If(
            test=Compare(
                left=name,
                ops=[Eq()],
                comparators=[Constant(value='@')]
            ),
            body=[Call(
                func=Attribute(
                    value=Attribute(
                        value=Name(id='pop', ctx=Load()),
                        attr='grid',
                        ctx=Load()
                    ),
                    attr='move_agent',
                    ctx=Load()
                ),
                args=[
                    node.func.value,  # caller
                    value
                ],
                keywords=[]
            )],
            orelse=[Call(
                func=Name(id='setattr', ctx=Load()),
                args=[
                    node.func.value,
                    Subscript(
                        value=Call(
                            func=Name(id='mpi', ctx=Load()),
                            args=[name],
                            keywords=[]
                        ),
                        slice=Index(value=Constant(value=0)),
                        ctx=Load()
                    ),
                    value
                ],
                keywords=[]
            )]
        )

    @staticmethod
    def t_set_rels(node):
        """
        Translates a call like:
            g.set_rels(rels, do_force=bool_val)
        into a call like:
            for name, value in rels.items():
                if name == '@':
                    pop.grid.move_agent(g, value)
                else:
                    setattr(a, mpi(name)[0], value)
        :param node:
        :return:
        """
        rels = RuleWriter._get_argument(node, 0, 'rels')

        return For(
            target=Tuple(
                elts=[
                    Name(id='name', ctx=Store()),
                    Name(id='value', ctx=Store())
                ],
                ctx=Store()
            ),
            iter=Call(
                func=Attribute(
                    value=rels,
                    attr=Name(id='items', ctx=Load()),
                    ctx=Load()
                ),
                args=[],
                keywords=[]
            ),
            body=[If(
                test=Compare(
                    left=Name(id='name', ctx=Load()),
                    ops=[Eq()],
                    comparators=[Constant(value='@')]
                ),
                body=[Call(
                    func=Attribute(
                        value=Attribute(
                            value=Name(id='pop', ctx=Load()),
                            attr='grid',
                            ctx=Load()
                        ),
                        attr='move_agent',
                        ctx=Load()
                    ),
                    args=[
                        node.func.value,  # caller
                        Name(id='value', ctx=Load())
                    ],
                    keywords=[]
                )],
                orelse=[Call(
                    func=Name(id='setattr', ctx=Load()),
                    args=[
                        node.func.value,
                        Subscript(
                            value=Call(
                                func=Name(id='mpi', ctx=Load()),
                                args=[Name(id='name', ctx=Load())],
                                keywords=[]
                            ),
                            slice=Index(value=Constant(value=0)),
                            ctx=Load()
                        ),
                        Name(id='value', ctx=Load())
                    ],
                    keywords=[]
                )]
            )],
            orelse=[]
        )

    @staticmethod
    def t_get_groups(node):
        """
        Translates a call like:
            x.get_groups(qry, non_empty_only=bool_val)
        into a call like:
            pop.get_groups(x, qry)
        Also, by being called, flags a get_groups method (defined elsewhere) should be added to the Mesa Model class.
        """
        attr_val = RuleWriter._pop_or_g_model(node)

        qry = RuleWriter._get_argument(node, 0, 'qry')
        return Call(
            func=Attribute(
                value=attr_val,
                attr='get_groups',
                ctx=Load()
            ),
            args=[
                node.func.value,  # caller
                qry
            ],
            keywords=[]
        )

    @staticmethod
    def t_get_mass_prop(node):
        """
        Translates a call like:
            s.get_mass_prop(qry)
        into a call like:
            pop.get_mass_prop(s, qry)
        Also, by being called, flags that the get_groups, get_mass, and get_mass_prop methods (defined elsewhere) should
        be added to the Mesa Model class.
        """
        attr_val = RuleWriter._pop_or_g_model(node)

        qry = RuleWriter._get_argument(node, 0, 'qry')
        return Call(
            func=Attribute(
                value=attr_val,
                attr='get_mass_prop',
                ctx=Load()
            ),
            args=[
                node.func.value,  # caller
                qry
            ],
            keywords=[]
        )

    @staticmethod
    def t_get_mass_and_prop(node):
        """
        Translates a call like:
            s.get_mass_and_prop(qry)
        into a call like:
            pop.get_mass_and_prop(s, qry)
        Also, by being called, flags that the get_groups, get_mass, get_mass_prop, and get_mass_and_prop methods
        (defined elsewhere) should be added to the Mesa Model class.
        """
        attr_val = RuleWriter._pop_or_g_model(node)

        qry = RuleWriter._get_argument(node, 0, 'qry')
        return Call(
            func=Attribute(
                value=attr_val,
                attr='get_mass_and_prop',
                ctx=Load()
            ),
            args=[
                node.func.value,  # caller
                qry
            ],
            keywords=[]
        )

    @staticmethod
    def t_add_vita_group(node):
        """
        Translates a call like:
            p.add_vita_group(g)
        into a call like:
            p.vita_groups.append(g)
        (the actual work of adding the group is done in the model's step() )
        :param node:
        :return:
        """
        group = RuleWriter._get_argument(node, 0, 'group')
        return Call(
            func=Attribute(
                value=Attribute(
                    value=node.func.value,  # caller; should be pop
                    attr='vita_groups',
                    ctx=Load()
                ),
                attr='append',
                ctx=Load()
            ),
            args=[group],
            keywords=[]
        )

    @staticmethod
    def t_get_group(node):
        """
        Translates a call like:
            p.get_group(attr, rel)
        into a call like:
            p.get_groups(GroupQry(attr, rel, [], True))
        If rel is not provided, automatically sets it to {}.
        Also, by being called, flags a get_groups method (defined elsewhere) should be added to the Mesa Model class.
        :param node:
        :return:
        """
        attr = RuleWriter._get_argument(node, 0, 'attr')
        rel = RuleWriter._get_argument(node, 1, 'rel')
        # rel has default value `{}`
        if isinstance(rel, Constant) and rel.value is None:
            rel = Dict(keys=[], values=[])

        return Call(
            func=Attribute(
                value=node.func.value,  # caller
                attr='get_groups',
                ctx=Load()
            ),
            args=[Call(
                func=Name(id='GroupQry', ctx=Load()),
                args=[
                    attr,
                    rel,
                    List(elts=[], ctx=Load()),
                    Constant(value=True)
                ],
                keywords=[]
            )],
            keywords=[]
        )

    @staticmethod
    def t_get_group_cnt(node):
        """
        Translates a call like:
            p.get_group_cnt(only_non_empty=bool_val)
        into a call like:
            len(p.schedule.agents)
        :param node:
        :return:
        """
        return Call(
            func=Name(id='len', ctx=Load()),
            args=[Attribute(
                value=Attribute(
                    value=node.func.value,  # caller
                    attr='schedule',
                    ctx=Load()
                ),
                attr='agents',
                ctx=Load()
            )],
            keywords=[]
        )

    @staticmethod
    def t_get_groups_mass(node):
        """
        Translates a call like:
            p.get_groups_mass(qry, hist_delta=d)
        into a call like:
            p.get_groups_mass(qry)
        if hist_delta is specified, a warning is raised, since that functionality is not supported.
        Also, by being called, flags the get_groups and get_groups_mass methods (defined elsewhere) should be added to
        the Mesa Model class.
        :param node:
        :return:
        """
        qry = RuleWriter._get_argument(node, 0, 'qry')
        hist_delta = RuleWriter._get_argument(node, 1, 'hist_delta')
        if not (isinstance(hist_delta, Constant) and hist_delta.value is None):
            warnings.warn(f'The hist_delta parameter in get_groups_mass is not supported; it will be treated as 0'
                          f' (i.e. ignored)')
        return Call(
            func=node.func,
            args=[qry],
            keywords=[]
        )

    @staticmethod
    def t_get_groups_mass_prop(node):
        """
        Does not change anything, but by being called, flags the get_groups, get_groups_mass, and get_groups_mass_prop
        methods (defined elsewhere) should be added to the Mesa Model class.
        """
        return node

    @staticmethod
    def t_get_groups_mass_and_prop(node):
        """
        Does not change anything, but by being called, flags the get_groups, get_groups_mass, get_groups_mass_prop,
        and get_groups_mass_and_prop methods (defined elsewhere) should be added to the Mesa Model class.
        """
        return node

    @staticmethod
    def t_get_site_cnt(node):
        """
        Translates a call like:
            p.get_site_cnt()
        into a call like:
            len(p.site_hashes)
        :param node:
        :return:
        """
        return Call(
            func=Name(id='len', ctx=Load()),
            args=[Attribute(
                value=node.func.value,  # caller
                attr='site_hashes',
                ctx=Load()
            )],
            keywords=[]
        )

    @staticmethod
    def t_add_group(node):
        warnings.warn(f'adding groups in a rule using add_group is not supported; try add_vita_group instead')
        return node

    @staticmethod
    def t_add_groups(node):
        warnings.warn(f'adding groups in a rule using add_groups is not supported; try add_vita_group instead')
        return node

    @staticmethod
    def t_unexpected(node):
        """
        This method is called when a PRAM function is encountered but it is a function that is not usually applicable
        inside a Rule. Calls are not translated and intended functionality may have to be manually implemented
        :param node:
        :return:
        """
        warnings.warn(f'unexpected function call {node.func.attr} in {node}. Call may not be modified', UserWarning)
        return node

    @staticmethod
    def t_resource_method(node):
        warnings.warn(f'Translating Resources is not currently supported; the call {node.func.attr} in {node} will'
                      f'not be modified. Perhaps you want to use a Site?', UserWarning)
        return node

# dictionary of PRAM function names to RuleWriter translation methods
RuleWriter.lookup = {
    # --- Group functions ---
    'copy': RuleWriter.t_copy,
    'get_attr': RuleWriter.t_get_attr,
    'ga': RuleWriter.t_ga,  # also a Site function
    'get_attrs': RuleWriter.t_get_attrs,
    'get_hash': RuleWriter.t_get_hash,
    'get_mass': RuleWriter.t_get_mass,  # also a Site function and a GroupPopulation function
    'get_site_at': RuleWriter.t_get_site_at,
    'get_rel': RuleWriter.t_get_rel,
    'get_rels': RuleWriter.t_get_rels,
    'gr': RuleWriter.t_gr,
    'ha': RuleWriter.t_ha,
    'has_attr': RuleWriter.t_has_attr,  # also a Site function
    'has_rel': RuleWriter.t_has_rel,
    'has_sites': RuleWriter.t_has_sites,
    'hr': RuleWriter.t_hr,
    'is_at_site': RuleWriter.t_is_at_site,
    'is_at_site_name': RuleWriter.t_is_at_site_name,
    'is_void': RuleWriter.t_is_void,
    'matches_qry': RuleWriter.t_matches_qry,
    'set_attr': RuleWriter.t_set_attr,
    'set_attrs': RuleWriter.t_set_attrs,
    'set_rel': RuleWriter.t_set_rel,
    'set_rels': RuleWriter.t_set_rels,
    # --- Site functions ---
    'get_groups': RuleWriter.t_get_groups,  # also a GroupPopulation function
    'get_mass_prop': RuleWriter.t_get_mass_prop,
    'get_mass_and_prop': RuleWriter.t_get_mass_and_prop,
    # --- GroupPopulation functions ---
    'add_group': RuleWriter.t_add_group,
    'add_groups': RuleWriter.t_add_groups,
    'add_vita_group': RuleWriter.t_add_vita_group,
    'get_group': RuleWriter.t_get_group,
    'get_group_cnt': RuleWriter.t_get_group_cnt,
    'get_groups_mass': RuleWriter.t_get_groups_mass,
    'get_groups_mass_prop': RuleWriter.t_get_groups_mass_prop,
    'get_groups_mass_and_prop': RuleWriter.t_get_groups_mass_and_prop,
    'get_site_cnt': RuleWriter.t_get_site_cnt,
    # --- functions that should not appear in a rule ---
    '_has_attr': RuleWriter.t_unexpected,
    '_has_rel': RuleWriter.t_unexpected,
    'apply_rules': RuleWriter.t_unexpected,
    'done': RuleWriter.t_unexpected,
    'gen_from_db': RuleWriter.t_unexpected,
    'gen_from_db_tmp1': RuleWriter.t_unexpected,
    'gen_from_db_tmp2': RuleWriter.t_unexpected,
    'gen_dict': RuleWriter.t_unexpected,
    'gen_hash': RuleWriter.t_unexpected,
    'link_to_site_at': RuleWriter.t_unexpected,
    'matches_qry_full_cond0': RuleWriter.t_unexpected,
    'matches_qry_full_cond1': RuleWriter.t_unexpected,
    'matches_qry_part_cond0': RuleWriter.t_unexpected,
    'matches_qry_part_cond1': RuleWriter.t_unexpected,
    'split': RuleWriter.t_unexpected,
    '__key': RuleWriter.t_unexpected,
    'add_group_link': RuleWriter.t_unexpected,
    'reset_group_links': RuleWriter.t_unexpected,
    'add_resource': RuleWriter.t_unexpected,
    'add_resources': RuleWriter.t_unexpected,
    'add_site': RuleWriter.t_unexpected,
    'add_sites': RuleWriter.t_unexpected,
    'archive': RuleWriter.t_unexpected,
    'compact': RuleWriter.t_unexpected,
    'do_post_iter': RuleWriter.t_unexpected,
    'freeze': RuleWriter.t_unexpected,
    'gen_agent_pop': RuleWriter.t_unexpected,
    'get_next_group_name': RuleWriter.t_unexpected,
    'transfer_mass': RuleWriter.t_unexpected,
    # --- Resource functions are not yet supported ---
    'allocate': RuleWriter.t_resource_method,
    'allocate_any': RuleWriter.t_resource_method,
    'allocate_all': RuleWriter.t_resource_method,
    'can_accommodate_all': RuleWriter.t_resource_method,
    'can_accommodate_any': RuleWriter.t_resource_method,
    'can_accommodate_one': RuleWriter.t_resource_method,
    'get_capacity': RuleWriter.t_resource_method,
    'get_capacity_left': RuleWriter.t_resource_method,
    'get_capacity_max': RuleWriter.t_resource_method,
    'release': RuleWriter.t_resource_method,
    'toJson': RuleWriter.t_resource_method
}
