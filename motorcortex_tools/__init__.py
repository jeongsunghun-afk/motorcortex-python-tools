#!/usr/bin/python3

#
#   Developer : Philippe Piatkiewitz (philippe.piatkiewitz@vectioneer.com)
#   All rights reserved. Copyright (c) 2019 VECTIONEER.
#

import time, operator
from motorcortex_tools.datalogger import *

import importlib
mpl_spec = importlib.util.find_spec("matplotlib")

import operator
waitForOperators = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}

def waitFor(req, param, value=True, index=0, timeout=30, testinterval=0.2, operat="=="):
    to=time.time()+timeout
    op_func = waitForOperators[operat]
    print("Waiting for " + param + " " + str(operat) + " " + str(value))
    while not op_func(req.getParameter(param).get().value[index], value):
        time.sleep(testinterval)
        if (time.time()>to):
            print("Timeout")
            return False
    return True

