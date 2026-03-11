#!/usr/bin/python3

#
#   Developer: Alexey Zakharov (alexey.zakharov@vectioneer.com)
#   All rights reserved. Copyright (c) 2016 VECTIONEER.
#

from __future__ import unicode_literals
import motorcortex.motorcortex_pb2
import logging
import sys
import os

if sys.version_info[0] >= 3:
    from importlib.machinery import SourceFileLoader

    if sys.version_info[1] < 4:
        def importLibrary(name, path):
            return SourceFileLoader(name, path).load_module()
    else:
        from types import ModuleType


        def importLibrary(name, path):
            loader = SourceFileLoader(name, path)
            mod = ModuleType(loader.name)
            loader.exec_module(mod)
            return mod
else:
    from builtins import bytes
    from imp import load_source


    def importLibrary(name, path):
        return load_source(name, path)

from json import load
from inspect import ismodule

from collections import namedtuple
import struct

# defines
motorcortex_parameter_msg = 1
motorcortex_parameter_list_msg = 2

ParameterMsg = namedtuple('ParameterMsg', 'header, info, value, status')
"""Data type which represents parameter description and value"""

ParameterListMsg = namedtuple('ParameterListMsg', 'header, params')
"""Data type which represents a list of parameters with descriptions and values"""

StatusCode = dict()
UserLevel = dict()


class PrimitiveTypes(object):
    def __init__(self, type_name):
        self.__decoder = None
        self.__encoder = None
        self.__prepare = None
        if type_name == "BOOL":
            self.__decoder = lambda length, val: struct.unpack('%db' % length, val)
            self.__encoder = lambda length, val: struct.pack('%db' % length, *val)
            self.__prepare = lambda val: [bool(x) for x in val.split(",")]
        elif type_name == "DOUBLE":
            self.__decoder = lambda length, val: struct.unpack('%dd' % length, val)
            self.__encoder = lambda length, val: struct.pack('%dd' % length, *val)
            self.__prepare = lambda val: [float(x) for x in val.split(",")]
        elif type_name == "FLOAT":
            self.__decoder = lambda length, val: struct.unpack('%df' % length, val)
            self.__encoder = lambda length, val: struct.pack('%df' % length, *val)
            self.__prepare = lambda val: [float(x) for x in val.split(",")]
        elif type_name == "INT8":
            self.__decoder = lambda length, val: struct.unpack('%db' % length, val)
            self.__encoder = lambda length, val: struct.pack('%db' % length, *val)
            self.__prepare = lambda val: [int(float(x)) & 0x7f for x in val.split(",")]
        elif type_name == "UINT8":
            self.__decoder = lambda length, val: struct.unpack('%dB' % length, val)
            self.__encoder = lambda length, val: struct.pack('%dB' % length, *val)
            self.__prepare = lambda val: [int(float(x)) & 0xff for x in val.split(",")]
        elif type_name == "INT16":
            self.__decoder = lambda length, val: struct.unpack('%dh' % length, val)
            self.__encoder = lambda length, val: struct.pack('%dh' % length, *val)
            self.__prepare = lambda val: [int(float(x)) & 0x7fff for x in val.split(",")]
        elif type_name == "UINT16":
            self.__decoder = lambda length, val: struct.unpack('%dH' % length, val)
            self.__encoder = lambda length, val: struct.pack('%dH' % length, *val)
            self.__prepare = lambda val: [int(float(x)) & 0xffff for x in val.split(",")]
        elif type_name == "INT32":
            self.__decoder = lambda length, val: struct.unpack('%di' % length, val)
            self.__encoder = lambda length, val: struct.pack('%di' % length, *val)
            self.__prepare = lambda val: [int(float(x)) & 0x7fffffff for x in val.split(",")]
        elif type_name == "UINT32":
            self.__decoder = lambda length, val: struct.unpack('%dI' % length, val)
            self.__encoder = lambda length, val: struct.pack('%dI' % length, *val)
            self.__prepare = lambda val: [int(float(x)) & 0xffffffff for x in val.split(",")]
        elif type_name == "INT64":
            self.__decoder = lambda length, val: struct.unpack('%dq' % length, val)
            self.__encoder = lambda length, val: struct.pack('%dq' % length, *val)
            self.__prepare = lambda val: [int(float(x)) for x in val.split(",")]
        elif type_name == "UINT64":
            self.__decoder = lambda length, val: struct.unpack('%dQ' % length, val)
            self.__encoder = lambda length, val: struct.pack('%dQ' % length, *val)
            self.__prepare = lambda val: [int(float(x)) for x in val.split(",")]
        elif type_name == "STRING":
            self.__decoder = lambda length, val: val.split(b'\0')[0].decode()
            self.__encoder = lambda length, val: (val + '\0').encode()
        elif type_name == "USER_TYPE":
            self.__decoder = lambda length, val: val
            self.__encoder = lambda length, val: val

    def decode(self, value, number_of_elements):
        val = self.__decoder(number_of_elements, value)
        return val

    def encode(self, value):
        t = type(value)
        # if bytes do nothing
        if t is bytes:
            return value

        # if the argument is a string, prepare and encode
        if t is str:
            return self.__encoder(-1, value)

        # if not list, convert to list
        if t is not list:
            value = [value]

        # encode
        values = self.__encoder(len(value), value)

        return values


class ModuleHashListPairContainer(object):
    def __init__(self, module, hash_list):
        self.module = module
        self.hash_list = hash_list


class MessageTypes(object):
    """Class for handling motorcortex data types, loads proto files and hash files,
    creates a dictionary with all available data types, resolves data types by,
    name or by hash, performs encoding and decoding of the messages.

    """

    def __init__(self):
        self.__types_by_hash = dict()
        self.__hashes_by_name = dict()
        self.__hash_len = 4
        self.__module_hash_pair_list = []
        # Default motorcortex messages are loaded from the library folder.
        # They could be replaced by load command if needed
        path = os.path.dirname(motorcortex.motorcortex_pb2.__file__)
        self.load([{'proto': motorcortex.motorcortex_pb2, 'hash': os.sep.join([path, 'motorcortex_hash.json'])}])

    def motorcortex(self):
        """Returns default motorcortex messages, provided with the package.
        System messages could be replaced at runtime with a newer version,
        by load([{'proto': 'path to the new message proto', 'hash': 'path to the new message hash'}])

        Returns:
            returns motorcortex messages
        """
        return self.getNamespace('motorcortex')

    def load(self, proto_hash_pair_list=None):
        """Loads an array of .proto and .json file pairs.
            Args:
                proto_hash_pair_list([{'hash'-`str`,'proto'-`str`}]): list of hash and proto messages

            Returns:
                list(Module): list of loaded modules with protobuf messages.

            Examples:
                >>> motorcortex_msg, motionsl_msg = motorcortex_types.load(
                >>>     # motorcortex hashes and messages
                >>>     [{'proto': './motorcortex-msg/motorcortex_pb2.py',
                >>>       'hash': './motorcortex-msg/motorcortex_hash.json'},
                >>>     # robot motion hashes and messages
                >>>      {'proto': './motorcortex-msg/motionSL_pb2.py',
                >>>       'hash': './motorcortex-msg/motionSL_hash.json'}])

        """
        count = 0
        module_hash_pair_list = []
        for proto_hash_pair in proto_hash_pair_list:
            with open(proto_hash_pair['hash']) as data_file:
                hash = load(data_file)
                proto = proto_hash_pair['proto']
                if ismodule(proto):
                    logging.debug(f"Adding module: {proto}")
                    module_hash_pair_list.append(ModuleHashListPairContainer(proto, hash))
                elif isinstance(proto, str):
                    logging.debug(f"Loading module: {proto}")

                    name = os.path.splitext(os.path.basename(proto))[0]
                    module_hash_pair_list.append(
                        ModuleHashListPairContainer(importLibrary(str(name), proto), hash))
                else:
                    logging.error(f"Failed to load module: {proto}")
                    return
                count = count + 1

        for module_hash_pair in module_hash_pair_list:
            for hash_type_pair in module_hash_pair.hash_list:
                # getting hash and converting to int
                hash = int(hash_type_pair['hash'], 16)
                # creating dict
                self.__hashes_by_name[hash_type_pair['type']] = hash

                module = module_hash_pair.module
                # searching for messages from a hash file

                for name in module.__dict__:
                    type = module.__dict__[name]
                    if hasattr(type, 'DESCRIPTOR'):
                        if hasattr(type.DESCRIPTOR, 'full_name'):
                            msg_name = type.DESCRIPTOR.full_name
                            if (msg_name == hash_type_pair['type']):
                                setattr(type, "decode_value", 0)
                                self.__types_by_hash[hash] = type

            self.__loadPrimitives("DataType", module)
            self.__loadEnum("ParameterFlag", module, motorcortex)
            self.__loadEnum("ParameterType", module, motorcortex)
            self.__loadEnum("Permission", module, motorcortex)
            self.__loadEnum("StatusCode", module, motorcortex)
            self.__loadEnum("UserGroup", module, motorcortex)
            self.__loadEnum("Unit", module, motorcortex)

            param_msg_type = self.getTypeByName("motorcortex.ParameterMsg")
            if param_msg_type:
                param_msg_type.decode_value = motorcortex_parameter_msg

            param_list_msg_type = self.getTypeByName("motorcortex.ParameterListMsg")
            if param_list_msg_type:
                param_list_msg_type.decode_value = motorcortex_parameter_list_msg

            for module_hash in self.__module_hash_pair_list:
                module_name = module_hash.module.DESCRIPTOR.package
                if module_name == module_hash_pair.module.DESCRIPTOR.package:
                    logging.warning(f"Module {module_name} already exists, replacing it with a new version")
                    self.__module_hash_pair_list.remove(module_hash)

        self.__module_hash_pair_list += module_hash_pair_list
        return [el.module for el in module_hash_pair_list]

    def __loadPrimitives(self, name, object):
        try:
            primitive_data_type = getattr(object, name)
            for key in primitive_data_type.DESCRIPTOR.values:
                hash = key.number
                name = key.name
                if hash > 0:
                    self.__hashes_by_name[name] = hash
                    self.__types_by_hash[hash] = PrimitiveTypes(name)
            logging.debug(f"Loaded types from {name}")
        except:
            pass

    def __loadEnum(self, enum_name, object, module):
        try:
            enum = getattr(object, enum_name)
            for key in enum.DESCRIPTOR.values:
                setattr(module, key.name, key.number)
            logging.debug(f"Loaded enumerator {enum_name}")
        except:
            pass

    def createType(self, type_name):
        """Returns an instance of the loaded data type given type name.

            Args:
                type_name(str): type name

            Returns:
                an instance of the requested type.

        """
        type = self.getTypeByName(type_name)
        if type:
            return type()

        return None

    def getTypeByHash(self, id):
        """Returns a data type given its hash.

            Args:
                id(int): type hash

            Returns:
                requested data type.
        """

        return self.__types_by_hash.get(id)

    def getTypeByName(self, name):
        """Returns a data type given its name.

            Args:
                name(str): type name

            Returns:
                requested data type.
        """

        return self.__types_by_hash.get(self.__hashes_by_name.get(name))

    def getNamespace(self, name):
        """Returns a module/namespace with data types.

            Args:
                name(str): module name

            Returns:
                requested module

            Examples:
                >>> # loading module motion_spec
                >>> MotionSpecType = motorcortex_types.getNamespace("motion_spec")
                >>> # instantiating a motion program from the module
                >>> motion_program = MotionSpecType.MotionProgram()
        """

        for el in self.__module_hash_pair_list:
            if el.module.DESCRIPTOR.package == name:
                return el.module

        return None

    def decode(self, wire_data):
        """Decodes data received from the server"""

        hash = wire_data[0] + (wire_data[1] << 8) + (wire_data[2] << 16) + (wire_data[3] << 24)
        type_inst = self.__types_by_hash[hash]
        buf = wire_data[self.__hash_len:]
        msg = type_inst()
        msg.ParseFromString(buf)

        if type_inst.decode_value == motorcortex_parameter_msg:
            if msg.status == motorcortex.OK:
                value_type = self.__types_by_hash[msg.info.data_type]
                return ParameterMsg(msg.header, msg.info, value_type.decode(msg.value, msg.info.number_of_elements),
                                    motorcortex.OK)
            else:
                return ParameterMsg(msg.header, msg.info, None, msg.status)
        elif type_inst.decode_value == motorcortex_parameter_list_msg:
            params = []
            for param in msg.params:
                if msg.status == motorcortex.OK:
                    value_type = self.__types_by_hash[param.info.data_type]
                    params.append(ParameterMsg(param.header, param.info,
                                               value_type.decode(param.value, param.info.number_of_elements),
                                               motorcortex.OK))
                else:
                    params.append(ParameterMsg(msg.header, msg.info, None, msg.status))
            return ParameterListMsg(msg.header, params)

        return msg

    def encode(self, proto_data):
        """Encodes data to send to the server"""
        type_name = proto_data.DESCRIPTOR.full_name
        hash = self.__hashes_by_name[type_name]
        wire_type = bytes([hash & 0xff, (hash >> 8) & 0xff, (hash >> 16) & 0xff, (hash >> 24) & 0xff])
        wire_type += proto_data.SerializeToString()
        return wire_type
