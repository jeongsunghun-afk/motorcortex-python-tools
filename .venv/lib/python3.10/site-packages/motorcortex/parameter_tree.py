#!/usr/bin/python3

#
#   Developer: Alexey Zakharov (alexey.zakharov@vectioneer.com)
#   All rights reserved. Copyright (c) 2016 VECTIONEER.
#


from typing import Any, Dict, List, Optional


class ParameterTree(object):
    """
    Represents a parameter tree, obtained from the server.

    Reference to a parameter tree instance is needed for resolving parameters,
    data types and other information to build a correct request message.
    """

    def __init__(self) -> None:
        """
        Initializes an empty ParameterTree.
        """
        self.__parameter_tree: List[Any] = []
        self.__parameter_map: Dict[str, Any] = dict()

    def load(self, parameter_tree_msg: Any) -> None:
        """
        Loads a parameter tree from ParameterTreeMsg received from the server.

        Args:
            parameter_tree_msg (Any): Parameter tree message from the server (should have a .params attribute).

        Examples:
            >>> parameter_tree = motorcortex.ParameterTree()
            >>> parameter_tree_msg = param_tree_reply.get()
            >>> parameter_tree.load(parameter_tree_msg)
        """
        self.__parameter_tree = parameter_tree_msg.params
        for param in self.__parameter_tree:
            self.__parameter_map[param.path] = param

    def getParameterTree(self) -> List[Any]:
        """
        Returns the list of parameter descriptions in the tree.

        Returns:
            List[Any]: A list of parameter descriptions (ParameterInfo objects).
        """
        return self.__parameter_tree

    def getInfo(self, parameter_path: str) -> Optional[Any]:
        """
        Get the parameter description for a given path.

        Args:
            parameter_path (str): Path of the parameter.

        Returns:
            Optional[Any]: Parameter description (ParameterInfo) if found, else None.
        """
        return self.__parameter_map.get(parameter_path)

    def getDataType(self, parameter_path: str) -> Optional[Any]:
        """
        Get the data type for a given parameter path.

        Args:
            parameter_path (str): Path of the parameter.

        Returns:
            Optional[Any]: Parameter data type if found, else None.
        """
        info = self.getInfo(parameter_path)
        if info:
            return info.data_type
        return None
