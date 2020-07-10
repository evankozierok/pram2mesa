from pram.rule import Rule
from pram.entity import Site, GroupQry, GroupSplitSpec
import random

class TranslateEverything(Rule):
    # this class does nothing, it just lists everything that could be in a rule to see if they are translated well
    def __init__(self):
        super().__init__('TranslateEverything')

    def apply(self, pop, group, iter, t):
        group.apply_rules(pop, pop.rules, iter, t)
        g1 = group.copy(is_deep=False)
        group.done()
        a = group.get_attr('foo')
        b = group.ga('bar')
        c = group.get_attrs()
        d = group.get_hash()
        e = group.get_mass()
        site = group.get_site_at()
        f = group.get_rel('@')
        g = group.gr(Site.AT)
        h = group.get_rels()
        i = group.has_attr('string')
        j = group.ha(['attr1', 'attr2'])
        k = group.has_rel({'one': 1, 'two': 2})
        l = group.hr(('x', 'y', 'z'))
        m = group.has_sites(['a', ])
        if group.is_at_site(site):
            print('n')
        if group.is_at_site_name(site):
            print('o')
        if group.is_void():
            print('p')
        group.link_to_site_at()
        if group.matches_qry(GroupQry(c, rel=h, full=True)):
            print('q')
        group.set_attr('foo', b, do_force=False)
        group.set_attrs({'foo': b, 'bar': a}, True)
        group.set_rel('origin', site, False)
        group.set_rels({'@': site, 'origin': g})
        group.split()
        # - - - - - - - - - - - - - - - - - - - - - - - - - -
        g = group
        site.add_group_link(g)
        sa = site.ga('max_capacity')
        sb = site.get_attr('agent')
        qry = GroupQry({'foo': 1, 'bar': 2}, {'@': site}, [lambda g: g.get_attr('goo') > 0], full=False)
        sc = site.get_groups(qry, non_empty_only=False)
        sd = site.get_mass(qry)
        se = site.get_mass_prop(qry)
        sf = site.get_mass_and_prop(qry)
        site.reset_group_links()
        # - - - - - - - - - - - - - - - - - - - - - - - - - -
        pop.add_group(g1)
        pop.add_groups([g1, g1])
        pop.add_vita_group(g1)
        pa = pop.get_group({'foo': 1})
        pb = pop.get_group_cnt(False)
        pc = pop.get_groups(qry)
        pd = pop.get_groups_mass(qry, 5)
        pe = pop.get_groups_mass(qry, hist_delta=1)
        pf = pop.get_groups_mass(qry)
        pg = pop.get_groups_mass(qry=qry)
        ph = pop.get_groups_mass_prop(qry)
        pi = pop.get_groups_mass_and_prop(qry)
        pj = pop.get_mass()
        pk = pop.get_next_group_name()
        pl = pop.get_site_cnt()
        pop.transfer_mass()
        pm = pop.sites
        pn = pop.groups

        return [
            GroupSplitSpec(p=0.1, attr_set={'foo': 1}, rel_set={Site.AT: site}, attr_del=['d'], rel_del={'origin'}),
            GroupSplitSpec(p=0.2, attr_set={}),
            GroupSplitSpec(p=random.random() / 2),
            GroupSplitSpec(p=1 - 0.1 - 0.2 - random.random() / 2, rel_set={'@': site})
        ]

class LambdasAndArguments(Rule):
    # tests translation of lambdas (i.e. in GroupQry calls) and arguments that can be passed positionally or as keywords
    def __init__(self):
        super().__init__('LambdasAndArguments')

    def apply(self, pop, group, iter, t):
        # ----- ARGUMENTS -----
        a1 = group.get_attr('foo')
        # a2 = group.get_attr(name='bar') # not legal PRAM code

        b1 = group.is_at_site('1')
        b2 = group.is_at_site(site='2')
        b3 = group.is_at_site_name('3')
        b4 = group.is_at_site_name(name='4')

        c1 = group.set_attr('foo', 'bar')
        c2 = group.set_attr('foo', value='bar')
        c3 = group.set_attr(name='foo', value='bar')
        c4 = group.set_attr('foo', 'bar', False)
        c5 = group.set_attr('foo', 'bar', do_force=False)
        c6 = group.set_attr('foo', value='bar', do_force=False)
        c7 = group.set_attr(name='foo', value='bar', do_force=False)

        d1 = pop.get_group({'one': 1})
        d2 = pop.get_group(attr={'one': 1})
        d3 = pop.get_group({'one': 1}, {'two': 2})
        d4 = pop.get_group({'one': 1}, rel={'two': 2})
        d5 = pop.get_group(attr={'one': 1}, rel={'two': 2})

        e1 = pop.get_groups_mass(GroupQry({'three': 3}))
        e2 = pop.get_groups_mass(qry=GroupQry({'three': 3}))
        e3 = pop.get_groups_mass(GroupQry({'three': 3}), 5)
        e4 = pop.get_groups_mass(GroupQry({'three': 3}), hist_delta=5)
        e5 = pop.get_groups_mass(qry=GroupQry({'three': 3}), hist_delta=5)

        # ----- LAMBDAS -----
        f1 = lambda g: g.get_attr('a') > 0
        f2 = lambda a, b, c: print(a, b, c)

        gq1 = GroupQry(cond=[
            lambda g1: g1.get_attr('a') > 0,
            lambda g2: g2.ga('b') < 0,
            lambda g3: g3.get_mass() == 100,
            lambda g4: g4.get_rel('origin') == 'a',
            lambda g5: g5.gr(Site.AT) == 'b',
            lambda g6: g6.has_attr('foo'),
            lambda g7: g7.get_site_at().get_groups()
        ])

        return None
