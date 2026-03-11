#!/usr/bin/python3

#
#   Developer : Philippe Piatkiewitz (philippe.piatkiewitz@vectioneer.com)
#   All rights reserved. Copyright (c) 2019 VECTIONEER.
#

import time, operator
from motorcortex_tools.datalogger import *
import lzma
import pandas as pd

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

def convertDate(timestamp):
    # This is a hack to avoid plot from freaking out. We have to add one microsecond
    return pd.to_datetime(float(timestamp)*1e6+1, unit='us')

def loadData(filename, nodateconv=True):
    if (filename[-2:] == "xz"):
        fd = lzma.open(filename, "rt")
    else:
        fd = open(filename, "r")
    #colnames = [x.strip() for x in fd.readline().split(",")]
    fd.seek(0)
    if nodateconv:
        P = pd.read_csv(fd,
                        sep=',',
                        header=0,
                        skip_blank_lines=False,
                        index_col=False
                        )
    else:
        P = pd.read_csv(fd,
                        sep=',',
                        header=0,
                        skip_blank_lines=False,
                        converters={0: convertDate},
                        index_col=False
                        )
    return P