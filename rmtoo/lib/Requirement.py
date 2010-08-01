#
# Requirement class itself
#
# (c) 2010 by flonatel
#
# For licencing details see COPYING
#

import os
import time

from rmtoo.lib.Parser import Parser
from rmtoo.lib.digraph.Digraph import Digraph
from rmtoo.lib.RMTException import RMTException
from rmtoo.lib.MemLogStore import MemLogStore

class Requirement(Digraph.Node):

    # Requirment Type
    # Each requirement has exactly one type.
    # The class ReqType sets this from the contents of the file.
    # Note: There can only be one (master requirement)
    rt_master_requirement = 1
    rt_initial_requirement = 2
    rt_design_decision = 3
    rt_requirement = 4

    # Status Type
    # Each requirement has a Status.
    # It will be read in and set by the ReqStatus class.
    # The status must be one of the following:
    st_not_done = 1
    st_finished = 2

    # Class Type
    # This specifies, if this node is really a node or if this can /
    # must be elaborated in more detail.
    ct_implementable = 1
    ct_detailable = 2

    # Error Status of Requirement
    # (i.e. is the requirment usable?)
    er_fine = 0
    er_error = 1

    def __init__(self, fd, rid, mls, mods, opts, config):
        Digraph.Node.__init__(self, rid)

        self.tags = {}
        self.id = rid
        self.mls = mls
        self.mods = mods
        self.opts = opts
        self.config = config

        # The analytic modules store the results in this map:
        self.analytics = {}

        self.state = self.er_fine
        self.input(fd)

    def input(self, fd):
        # Read it in from the file (Syntactic input)
        req = Parser.read_as_map(self.id, fd)
        if req == None:
            self.state = self.er_error
            self.mls.error(42, "parser returned error", self.id)
            return

        # Handle all the modules (Semantic input)
        self.handle_modules_reqtag(req)

        # Do not check for remaining tags here. There must be some
        # left over: all those that work on the whole requirement set
        # (e.g. 'Depends on').

        # If everything's fine, store the rest of the req for later
        # inspection.
        self.req = req

    def handle_modules_reqtag(self, reqs):
        for modkey, module in self.mods.reqtag.items():
            try:
                key, value = module.rewrite(self.id, reqs)
                # Check if there is already a key with the current key
                # in the map.
                if key in self.tags:
                    print("+++ ERROR %s: tag '%s' already defined" %
                          (self.id, key))
                    self.state = er_error
                    # Also continue to get possible further error
                    # messages.
                self.tags[key] = value
            except RMTException, rmte:
                # Some sematic error occured: do not interpret key or
                # value.
                self.mls.error(rmte.lid, rmte.msg, rmte.efile)
                self.mls.error(41, "semantic error occured in "
                               "module '%s'" % modkey, self.id)
                #print("+++ root cause is: '%s'" % rmte)
                self.state = self.er_error
                # Continue (do not return immeditely) to get also
                # possible other errors.

    def ok(self):
        return self.state==self.er_fine

    # Error is an error (no distinct syntax error)
    def mark_syntax_error(self):
        self.state = self.er_error

    # Error is an error (no distinct sematic error)
    def mark_sematic_error(self):
        self.state = self.er_error

    def get_prio(self):
        return self.tags["Priority"]

    def is_open(self):
        return self.tags["Status"] == self.st_not_done

    def is_implementable(self):
        return self.tags["Class"] == self.ct_implementable

    # Write out the analytics results.
    def write_analytics_result(self, mstderr):
        for k, v in self.analytics.iteritems():
            if v[0]<0:
                mstderr.write("+++ Error:Analytics:%s:%s:result is '%+3d'\n"
                              % (k, self.id, v[0]))
                for l in v[1]:
                    mstderr.write("+++ Error:Analytics:%s:%s:%s\n" % 
                                  (k, self.id, l))

