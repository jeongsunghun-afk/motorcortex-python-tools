#!/usr/bin/python3

#
#   Developer : Philippe Piatkiewitz (philippe.piatkiewitz@vectioneer.com)
#   All rights reserved. Copyright (c) 2019 VECTIONEER.
#

import time
from motorcortex_tools.datalogger import *

import importlib
mpl_spec = importlib.util.find_spec("matplotlib")

def waitFor(req, param, value=True, index=0, timeout=30, testinterval=0.2):
    print("Waiting for " + param + " to become equal to " + str(value))
    to=time.time()+timeout
    while not (req.getParameter(param).get().value[index] == value):
        time.sleep(testinterval)
        if (time.time()>to):
            print("Timeout")
            return False
    return True


