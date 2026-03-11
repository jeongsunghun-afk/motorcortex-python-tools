#!/usr/bin/python3

#
#   Developer: Alexey Zakharov (alexey.zakharov@vectioneer.com)
#   All rights reserved. Copyright (c) 2016-2020 VECTIONEER.
#


class Reply(object):
    """Reply handle is a JavaScript-like Promise.

        It is resolved when a reply is received with successful status and fails otherwise.
    """

    def __init__(self, future):
        self.__future = future

    def get(self, timeout_ms=None):
        """A blocking call to wait for the reply and returns a value.

            Args:
                timeout_ms(integer): timeout for reply in milliseconds

            Returns:
                A protobuf message with a parameter description and value.

            Examples:
                  >>> param_tree_reply = req.getParameterTree()
                  >>> value = param_tree_reply.get()

        """
        return self.__future.result(timeout_ms / 1000.0 if timeout_ms else None)

    def done(self):
        """
            Returns:
                bool: True if the call was successfully canceled or finished running.
        """
        return self.__future.done()

    def then(self, received_clb, *args, **kwargs):
        """JavaScript-like promise, which is resolved when a reply is received.

                Args:
                    received_clb: callback which is resolved when the reply is received.

                Returns:
                    self pointer to add 'catch' callback

                Examples:
                    >>> param_tree_reply.then(lambda reply: print("got reply: %s"%reply))
                    >>>                 .catch(lambda g: print("failed"))
        """
        self.__future.add_done_callback(
            lambda msg: received_clb(msg.result(), *args, **kwargs) if msg.result() else None
        )
        return self

    def catch(self, failed_clb, *args, **kwargs):
        """JavaScript-like promise, which is resolved when receive has failed.

            Args:
                failed_clb: callback which is resolved when receive has failed

            Returns:
                self pointer to add 'then' callback

            Examples:
                >>> param_tree_reply.catch(lambda g: print("failed")).then(lambda reply: print("got reply: %s"%reply))
        """
        self.__future.add_done_callback(
            lambda msg: failed_clb(*args, **kwargs) if not msg.result() else None
        )
        return self
