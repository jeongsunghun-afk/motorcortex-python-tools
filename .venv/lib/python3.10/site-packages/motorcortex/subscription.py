#!/usr/bin/python3

#
#   Developer: Alexey Zakharov (alexey.zakharov@vectioneer.com)
#   All rights reserved. Copyright (c) 2016-2025 VECTIONEER.
#

from collections import namedtuple
from struct import unpack_from
from concurrent.futures import Future
import time
from typing import Any, Callable, List, Optional, Union
from motorcortex.timespec import Timespec

# timespec = namedtuple('timespec', 'sec, nsec')


Parameter = namedtuple('Parameter', 'timestamp, value')


class Subscription(object):
    """
    Represents a subscription to a group of parameters in Motorcortex.

    The Subscription class allows you to:
    - Access the latest values and timestamps for a group of parameters.
    - Poll for updates or use observer callbacks for real-time notifications.
    - Chain asynchronous operations using `then` and `catch` (promise-like interface).

    Attributes:
        group_alias (str): Alias for the parameter group.
        protobuf_types (Any): Protobuf type definitions.
        frq_divider (str): Frequency divider for the group.
        pool (Any): Thread or process pool for observer callbacks.

    Methods:
        id() -> int
            Returns the subscription identifier.

        alias() -> str
            Returns the group alias.

        frqDivider() -> str
            Returns the frequency divider of the group.

        read() -> Optional[List[Parameter]]
            Returns the latest values of the parameters in the group.

        layout() -> Optional[List[str]]
            Returns the ordered list of parameter paths in the group.

        done() -> bool
            Returns True if the subscription is finished or cancelled.

        get(timeout_sec: float = 1.0) -> Optional[Any]
            Waits for the subscription to complete, returns the result or None on timeout.

        then(subscribed_clb: Callable[[Any], None]) -> Subscription
            Registers a callback for successful subscription completion.

        catch(failed: Callable[[], None]) -> Subscription
            Registers a callback for subscription failure.

        notify(observer_list: Union[Callable, List[Callable]]) -> None
            Registers observer(s) to be notified on every group update.

    Examples:
        >>> # Make sure you have a valid connection
        >>> subscription = sub.subscribe(paths, "group1", 100)
        >>> result = subscription.get()
        >>> if result is not None and result.status == motorcortex.OK:
        ...     print(f"Subscription successful, layout: {subscription.layout()}")
        ... else:
        ...     print(f"Subscription failed. Check parameter paths: {paths}")
        ...     sub.close()
        ...     exit()
        >>> # Use promise-like interface
        >>> subscription.then(lambda res: print("Subscribed:", res)).catch(lambda: print("Failed"))
        >>> # Use observer for real-time updates
        >>> def on_update(parameters):
        ...     for param in parameters:
        ...         timestamp = param.timestamp.sec + param.timestamp.nsec * 1e-9
        ...         print(f"Update: {timestamp:.6f}, {param.value}")
        >>> subscription.notify(on_update)
        >>> print("Waiting for parameter updates...")
        >>> import time
        >>> while True:
        ...     time.sleep(1)
    """

    def __init__(
            self,
            group_alias: str,
            protobuf_types: Any,
            frq_divider: str,
            pool: Any
    ) -> None:
        self.__info: Optional[Any] = None
        self.__group_alias: str = group_alias
        self.__protobuf_types: Any = protobuf_types
        self.__decoder: List[Any] = []
        self.__future: Future = Future()
        self.__values: Optional[List["Parameter"]] = None
        self.__layout: Optional[List[str]] = None
        self.__is_complete: bool = False
        self.__observer_list: List[Callable[[List["Parameter"]], None]] = []
        self.__pool: Any = pool
        self.__frq_divider: str = frq_divider

    def id(self) -> int:
        """
            Returns:
                int: subscription identifier
        """
        return self.__info.id

    def alias(self) -> str:
        """
            Returns:
                str: group alias
        """
        return self.__group_alias

    def frqDivider(self) -> str:
        """
            Returns:
                str: frequency divider of the group
        """
        return self.__frq_divider

    def read(self) -> Optional[List["Parameter"]]:
        """Read the latest values of the parameters in the group.

            Returns:
                list of Parameter: list of parameters
        """
        return self.__values[:] if self.__is_complete else None

    def layout(self) -> Optional[List[str]]:
        """Get a layout of the group.

            Returns:
                list of str: ordered list of the parameters in the group
        """
        return self.__layout[:] if self.__is_complete else None

    def done(self) -> bool:
        """
            Returns:
                bool: True if the call was successfully canceled or finished running.

            Examples:
                >>> subscription = sub.subscribe("root/logger/logOut", "log")
                >>> while not subscription.done():
                >>>     time.sleep(0.1)
        """
        return self.__future.done()

    def get(self, timeout_sec: float = 1.0) -> Optional[Any]:
        """
            Returns:
                bool: StatusMsg if the call was successful, None if timeout happened.

            Examples:
                >>> subscription = sub.subscribe("root/logger/logOut", "log")
                >>> done = subscription.get()
        """

        return self.__future.result(timeout_sec)

    def then(self, subscribed_clb: Callable[[Any], None]) -> "Subscription":
        """JavaScript-like promise, which is resolved when the subscription is completed.

            Args:
                subscribed_clb: callback which is resolved when the subscription is completed.

            Returns:
                self pointer to add 'catch' callback

            Examples:
                >>> subscription = sub.subscribe("root/logger/logOut", "log")
                >>> subscription.then(lambda val: print("got: %s"%val)).catch(lambda d: print("failed"))
        """

        self.__future.add_done_callback(
            lambda msg: subscribed_clb(msg.result()) if msg.result() else None
        )
        return self

    def catch(self, failed: Callable[[], None]) -> "Subscription":
        """JavaScript-like promise, which is resolved when subscription has failed.

            Args:
                failed: callback which is resolved when the subscription has failed

            Returns:
                self pointer to add 'then' callback

            Examples:
                >>> subscription = sub.subscribe("root/logger/logOut", "log")
                >>> subscription.catch(lambda d: print("failed")).then(lambda val: print("got: %s"%val))
        """

        self.__future.add_done_callback(
            lambda msg: failed() if not msg.result() else None
        )
        return self

    def notify(self, observer_list: Union[
        Callable[[List["Parameter"]], None], List[Callable[[List["Parameter"]], None]]]) -> None:
        """Set an observer, which is notified on every group update.

            Args:
                observer_list: a callback function (or list of callback functions)
                to notify when new values are available

            Examples:
                  >>> def update(parameters):
                  >>>   print(parameters) #list of Parameter tuples
                  >>> ...
                  >>> data_sub.notify(update)

        """
        self.__observer_list = observer_list if type(observer_list) is list else [observer_list]

    def _complete(self, msg: Any) -> bool:
        """Marks the subscription as complete and initializes decoders.

            Args:
                msg: Protobuf message containing subscription info.
                
            Returns:
                bool: True if completed successfully, False otherwise.
        """
        self.__decoder = []
        self.__values = []
        self.__layout = []
        if msg.status == 0:
            self.__info = msg
            for param in msg.params:
                data_type = param.info.data_type
                self.__decoder.append(self.__protobuf_types.getTypeByHash(data_type))
                self.__values.append(Parameter(Timespec(0, 0), [0] * param.info.number_of_elements))
                self.__layout.append(param.info.path)

            self.__is_complete = True
            self.__future.set_result(msg)
            return True
        else:
            self._failed()

        return False

    def _updateId(self, new_id: int) -> None:
        """Updates the subscription identifier.

            Args:
                new_id: New subscription identifier.
        """
        self.__info.id = new_id

    def _updateProtocol0(self, sub_msg: bytes, length: int) -> None:
        """Updates the subscription values using protocol version 0.
        
            Args:
                sub_msg: Subscription message bytes.
                length: Length of the subscription message.
        """
        if sub_msg:
            counter = 0
            n_params = len(self.__info.params)
            for param in self.__info.params:
                offset = param.offset
                size = param.size

                # the last element in the group may have a variable size
                if ((counter + 1) == n_params) and ((offset + size) > length):
                    size = length - offset

                if (offset + size) <= length:
                    timestamp = Timespec.from_iterable(unpack_from('QQ', sub_msg, offset))
                    value = self.__decoder[counter].decode(sub_msg[offset + 16: offset + size],
                                                           (size - 16) / param.info.data_size)
                    self.__values[counter] = Parameter(timestamp, value)

                counter += 1

            if self.__observer_list:
                value = self.__values[:]
                for observer in self.__observer_list:
                    self.__pool.submit(observer, value)

    def _updateProtocol1(self, sub_msg: bytes, length: int) -> None:
        if sub_msg:
            timestamp = Timespec.from_iterable(unpack_from('QQ', sub_msg, 0))
            counter = 0
            n_params = len(self.__info.params)
            for param in self.__info.params:
                offset = param.offset + 16
                size = param.size

                # the last element in the group may have a variable size
                if ((counter + 1) == n_params) and ((offset + size) > length):
                    size = length - offset

                if (offset + size) <= length:
                    value = self.__decoder[counter].decode(sub_msg[offset: offset + size],
                                                           size / param.info.data_size)
                    self.__values[counter] = Parameter(timestamp, value)

                counter += 1

            if self.__observer_list:
                value = self.__values[:]
                for observer in self.__observer_list:
                    self.__pool.submit(observer, value)

    def _failed(self) -> None:
        self.__future.set_result(None)
