#!/usr/bin/python3

#
#   Developer: Alexey Zakharov (alexey.zakharov@vectioneer.com)
#   All rights reserved. Copyright (c) 2016-2025 VECTIONEER.
#

from pynng._nng import lib
from motorcortex.setup_logger import logger


def init_nng_threads(task=2, expire=1, poller=1, resolver=1):
    """Must be called BEFORE any pynng socket operations!"""
    try:
        lib.nng_init_set_parameter(lib.NNG_INIT_NUM_TASK_THREADS, task)
        lib.nng_init_set_parameter(lib.NNG_INIT_NUM_EXPIRE_THREADS, expire)
        lib.nng_init_set_parameter(lib.NNG_INIT_NUM_POLLER_THREADS, poller)
        lib.nng_init_set_parameter(lib.NNG_INIT_NUM_RESOLVER_THREADS, resolver)
    except AttributeError:
        logger.error("[INIT-THREADS] Cannot adjust thread count: interface unavailable")