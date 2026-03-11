#!/usr/bin/python3

#
#   Developer: Alexey Zakharov (alexey.zakharov@vectioneer.com)
#   All rights reserved. Copyright (c) 2016-2025 VECTIONEER.
#

import pynng
from pynng import Sub0, TLSConfig
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import Any, Callable, Dict, Optional, List

from motorcortex.request import Request, Reply, ConnectionState
from motorcortex.subscription import Subscription
from motorcortex.state_callback_handler import StateCallbackHandler
from motorcortex.setup_logger import logger
from motorcortex.nng_url import NngUrl


class Subscribe:
    """
    Subscribe class is used to receive continuous parameter updates from the motorcortex server.

    This class simplifies creating and removing subscription groups, managing the connection,
    and handling the reception of parameter updates.
    """

    def __init__(self, req: Request, protobuf_types: Any, number_of_threads: int = 2) -> None:
        """
        Initialize a Subscribe object.

        Args:
            req (Request): Reference to a Request instance.
            protobuf_types (Any): Reference to a MessageTypes instance.
            number_of_threads (int): Thread pool size (minimum 2, None - use default (CPU-based)).
        """
        self.__socket: Optional[Sub0] = None
        self.__connected_event: Optional[Event] = None
        self.__is_connected: bool = False
        self.__url: Optional[str] = None
        self.__req: Request = req
        self.__protobuf_types: Any = protobuf_types
        self.__subscriptions: Dict[int, Subscription] = dict()
        if number_of_threads and number_of_threads < 2:
            number_of_threads = 2
        self.__pool: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=number_of_threads, thread_name_prefix="mcx_sub")
        self.__callback_handler: StateCallbackHandler = StateCallbackHandler()
        self.__connection_state: ConnectionState = ConnectionState.DISCONNECTED
        logger.debug("[SUBSCRIBE] Subscribe object initialized with state: DISCONNECTED")

    def connect(self, url: str, **kwargs: Any) -> Reply:
        """
        Open a subscription connection.

        Args:
            url (str): Motorcortex server URL.
            **kwargs: Additional connection parameters. Supported keys include:
                certificate (str, optional): Path to a TLS certificate file for secure connections.
                conn_timeout_ms (int, optional): Connection timeout in milliseconds (default: 1000).
                recv_timeout_ms (int, optional): Receive timeout in milliseconds (default: 500).
                login (str, optional): Username for authentication (if required by server).
                password (str, optional): Password for authentication (if required by server).
                state_update (Callable, optional): Callback function to be called on connection state changes.
                timeout_ms (int, optional): Alternative timeout in milliseconds (used by Request.parse).

        Returns:
            Reply: A promise that resolves when the connection is established.
        """
        logger.debug(f"[SUBSCRIBE-CONNECT] Starting subscription connection to {url}")
        logger.debug(f"[SUBSCRIBE-CONNECT] Current state: {self.__connection_state.name}")

        self.__connection_state = ConnectionState.CONNECTING
        conn_timeout_ms, recv_timeout_ms, certificate, state_update = Request.parse(**kwargs)

        logger.debug(
            f"[SUBSCRIBE-CONNECT] Parameters - timeout: {conn_timeout_ms}ms, recv_timeout: {recv_timeout_ms}ms, "
            f"has_cert: {certificate is not None}, has_state_update: {state_update is not None}")

        if state_update:
            logger.debug("[SUBSCRIBE-CONNECT] Starting state callback handler")
            self.__callback_handler.start(state_update)

        if not recv_timeout_ms:
            recv_timeout_ms = 500
            logger.debug(f"[SUBSCRIBE-CONNECT] Using default recv_timeout: {recv_timeout_ms}ms")

        self.__url = url
        tls_config = None
        if certificate:
            parsed = NngUrl(url)
            logger.debug(f"[SUBSCRIBE-CONNECT] Using TLS with certificate: {certificate}")
            tls_config = TLSConfig(TLSConfig.MODE_CLIENT, ca_files=certificate, server_name=parsed.hostname)

        logger.debug(f"[SUBSCRIBE-CONNECT] Creating Sub0 socket with recv_timeout={recv_timeout_ms}ms")
        self.__socket = Sub0(recv_timeout=recv_timeout_ms, tls_config=tls_config)

        self.__connected_event = Event()
        self.__is_connected = False

        logger.debug("[SUBSCRIBE-CONNECT] Socket created, registering callbacks")

        def pre_connect_cb(_pipe):
            logger.debug(f"[SUBSCRIBE-CALLBACK] PRE_CONNECT fired - Subscription connection established")
            old_state = self.__connection_state.name
            self.__is_connected = True
            self.__connection_state = ConnectionState.CONNECTION_OK
            logger.debug(f"[SUBSCRIBE-CALLBACK] State transition: {old_state} -> {self.__connection_state.name}")
            self.__callback_handler.notify(self.__req, self, self.connectionState())
            self.__connected_event.set()  # Wake up all waiting threads
            logger.debug("[SUBSCRIBE-CALLBACK] Connection event set, is_connected=True")

        def post_remove_cb(_pipe):
            logger.debug(f"[SUBSCRIBE-CALLBACK] POST_REMOVE fired - Subscription connection lost/failed")
            old_state = self.__connection_state.name

            if self.__connection_state == ConnectionState.DISCONNECTING:
                self.__connection_state = ConnectionState.DISCONNECTED
                logger.debug(f"[SUBSCRIBE-CALLBACK] Clean disconnect: {old_state} -> DISCONNECTED")
            elif self.__connection_state == ConnectionState.CONNECTING:
                self.__connection_state = ConnectionState.CONNECTION_FAILED
                logger.debug(f"[SUBSCRIBE-CALLBACK] Connection failed: {old_state} -> CONNECTION_FAILED")
            elif self.__connection_state == ConnectionState.CONNECTION_OK:
                self.__connection_state = ConnectionState.CONNECTION_LOST
                logger.debug(f"[SUBSCRIBE-CALLBACK] Connection lost: {old_state} -> CONNECTION_LOST")

            self.__is_connected = False
            self.__callback_handler.notify(self.__req, self, self.connectionState())
            self.__connected_event.set()
            logger.debug("[SUBSCRIBE-CALLBACK] Connection event set, is_connected=False")

        self.__socket.add_pre_pipe_connect_cb(pre_connect_cb)
        self.__socket.add_post_pipe_remove_cb(post_remove_cb)
        logger.debug("[SUBSCRIBE-CONNECT] Callbacks registered successfully")

        logger.debug(f"[SUBSCRIBE-CONNECT] Starting dial to {url} (non-blocking)")
        self.__socket.dial(url, block=False)

        logger.debug("[SUBSCRIBE-CONNECT] Submitting run() to thread pool")
        self.__pool.submit(self.run, self.__socket)

        logger.debug(f"[SUBSCRIBE-CONNECT] Submitting waitForConnection with timeout={conn_timeout_ms / 1000.0}s")
        return Reply(self.__pool.submit(Request.waitForConnection, self.__connected_event,
                                        conn_timeout_ms / 1000.0, lambda: self.__is_connected))

    def close(self) -> None:
        """
        Close connection to the server and clean up resources.
        """
        logger.debug("[SUBSCRIBE-CLOSE] Closing subscription connection")
        logger.debug(
            f"[SUBSCRIBE-CLOSE] Current state: {self.__connection_state.name}, is_connected: {self.__is_connected}")
        logger.debug(f"[SUBSCRIBE-CLOSE] Active subscriptions: {len(self.__subscriptions)}")

        self.__connection_state = ConnectionState.DISCONNECTING
        if self.__connected_event:
            self.__is_connected = False
            self.__connected_event.set()
            logger.debug("[SUBSCRIBE-CLOSE] Connection event set for shutdown")
        else:
            logger.debug("[SUBSCRIBE-CLOSE] No connection event to set")

        if self.__socket:
            logger.debug("[SUBSCRIBE-CLOSE] Closing socket")
            self.__socket.close()
        else:
            logger.debug("[SUBSCRIBE-CLOSE] No socket to close")

        logger.debug("[SUBSCRIBE-CLOSE] Stopping callback handler")
        self.__callback_handler.stop()

        logger.debug("[SUBSCRIBE-CLOSE] Shutting down thread pool (blocking)")
        self.__pool.shutdown(wait=True)
        logger.debug("[SUBSCRIBE-CLOSE] Subscription connection closed successfully")

    def run(self, socket: Sub0) -> None:
        """
        Main receive loop for the subscription socket.

        Args:
            socket (Sub0): The subscription socket to receive messages from.
        """
        logger.debug("[SUBSCRIBE-RUN] Subscription receive loop started")

        # Wait for initial connection
        while not self.__is_connected:
            logger.debug("[SUBSCRIBE-RUN] Waiting for connection...")
            self.__connected_event.wait()  # Wait until connected

            # Check if we're shutting down
            if not self.__is_connected:
                if self.__connection_state in (ConnectionState.DISCONNECTING,
                                               ConnectionState.DISCONNECTED,
                                               ConnectionState.CONNECTION_FAILED):
                    logger.debug("[SUBSCRIBE-RUN] Connection closed or failed during startup, exiting")
                    return
                logger.debug("[SUBSCRIBE-RUN] Spurious wakeup, continuing to wait")

        logger.debug("[SUBSCRIBE-RUN] Connection established, starting receive loop")
        message_count = 0

        while True:
            try:
                buffer = socket.recv()
                message_count += 1
                if message_count % 100 == 0:  # Log every 100 messages to avoid spam
                    logger.debug(f"[SUBSCRIBE-RUN] Received {message_count} messages so far")

            except pynng.Timeout:
                # This is normal - just continue
                continue

            except pynng.Closed:
                logger.debug('[SUBSCRIBE-RUN] Socket closed, exiting subscription loop')
                break

            except RuntimeError as e:
                if "pool" in str(e).lower():
                    logger.debug('[SUBSCRIBE-RUN] Thread pool shutting down, exiting')
                    break
                logger.error(f'[SUBSCRIBE-RUN] RuntimeError in subscription loop: {e}')
                continue

            except Exception as e:
                logger.error(f'[SUBSCRIBE-RUN] Unexpected error in subscription loop: {type(e).__name__}: {e}')
                continue

            if buffer:
                sub_id_buf = buffer[:4]
                protocol_version = sub_id_buf[3]
                sub_id = sub_id_buf[0] + (sub_id_buf[1] << 8) + (sub_id_buf[2] << 16)
                sub = self.__subscriptions.get(sub_id)

                if sub:
                    length = len(buffer)
                    if protocol_version == 1:
                        sub._updateProtocol1(buffer[4:], length - 4)
                    elif protocol_version == 0:
                        sub._updateProtocol0(buffer[4:], length - 4)
                    else:
                        logger.error(
                            f'[SUBSCRIBE-RUN] Unknown protocol version: {protocol_version} for sub_id: {sub_id}')
                else:
                    logger.debug(f'[SUBSCRIBE-RUN] Received data for unknown subscription id: {sub_id}')

        logger.debug('[SUBSCRIBE-RUN] Subscription loop ended')

    def subscribe(self, param_list: List[str], group_alias: str, frq_divider: int = 1) -> Subscription:
        """
        Create a subscription group for a list of parameters.

        Args:
            param_list (List[str]): List of the parameters to subscribe to.
            group_alias (str): Name of the group.
            frq_divider (int, optional): Frequency divider for the group publish rate. Defaults to 1.

        Returns:
            Subscription: A subscription handle, which acts as a JavaScript Promise. It is resolved when the
            subscription is ready or failed. After the subscription is ready, the handle is used to retrieve the latest data.
        """
        logger.debug(
            f"[SUBSCRIBE] Creating subscription group '{group_alias}' with {len(param_list)} parameters, frq_divider={frq_divider}")
        logger.debug(
            f"[SUBSCRIBE] Parameters: {param_list[:5]}{'...' if len(param_list) > 5 else ''}")  # Show first 5 params

        subscription = Subscription(group_alias, self.__protobuf_types, frq_divider, self.__pool)
        reply = self.__req.createGroup(param_list, group_alias, frq_divider)
        reply.then(self.__complete, subscription, self.__socket).catch(subscription._failed)

        return subscription

    def unsubscribe(self, subscription: Subscription) -> Reply:
        """
        Unsubscribe from the group.

        Args:
            subscription (Subscription): Subscription handle.

        Returns:
            Reply: A promise that resolves when the unsubscribe operation is complete, fails otherwise.
        """
        sub_id = subscription.id()
        sub_id_buf = Subscribe.__idBuf(subscription.id())

        logger.debug(f"[UNSUBSCRIBE] Unsubscribing from group '{subscription.alias()}' (id={sub_id})")

        # stop receiving sub
        try:
            self.__socket.unsubscribe(sub_id_buf)
            logger.debug(f"[UNSUBSCRIBE] Socket unsubscribed from id={sub_id}")
        except Exception as e:
            logger.debug(f"[UNSUBSCRIBE] Failed to unsubscribe socket: {e}")

        # find and remove subscription
        if sub_id in self.__subscriptions:
            sub = self.__subscriptions[sub_id]
            # stop sub update thread
            sub.done()
            del self.__subscriptions[sub_id]
            logger.debug(
                f"[UNSUBSCRIBE] Removed subscription from internal dict, remaining: {len(self.__subscriptions)}")
        else:
            logger.debug(f"[UNSUBSCRIBE] Subscription id={sub_id} not found in internal dict")

        # send remove group request to the server
        return self.__req.removeGroup(subscription.alias())

    def connectionState(self) -> ConnectionState:
        """
        Get the current connection state.

        Returns:
            ConnectionState: The current state of the subscription connection.
        """
        return self.__connection_state

    def resubscribe(self) -> None:
        """
        Resubscribe all current groups after a reconnect.
        """
        logger.debug(f"[RESUBSCRIBE] Starting resubscription for {len(self.__subscriptions)} groups")
        old_sub = self.__subscriptions.copy()
        self.__subscriptions.clear()

        for i, (sub_id, s) in enumerate(old_sub.items()):
            logger.debug(f"[RESUBSCRIBE] Resubscribing group {i + 1}/{len(old_sub)}: '{s.alias()}' (old_id={sub_id})")
            try:
                # unsubscribe from the old group
                self.__socket.unsubscribe(Subscribe.__idBuf(s.id()))
            except Exception as e:
                logger.debug(f"[RESUBSCRIBE] Failed to unsubscribe old id: {e}")

            # subscribe again, update id
            msg = self.__req.createGroup(s.layout(), s.alias(), s.frqDivider()).get()
            s._updateId(msg.id)
            self.__socket.subscribe(Subscribe.__idBuf(s.id()))
            self.__subscriptions[s.id()] = s
            logger.debug(f"[RESUBSCRIBE] Group '{s.alias()}' resubscribed with new id={s.id()}")

        logger.debug(f"[RESUBSCRIBE] Completed resubscription for {len(self.__subscriptions)} groups")

    @staticmethod
    def __idBuf(msg_id: int) -> bytes:
        """
        Convert a message id to a 3-byte buffer.

        Args:
            msg_id (int): The message id.

        Returns:
            bytes: The id buffer.
        """
        return bytes([msg_id & 0xff, (msg_id >> 8) & 0xff, (msg_id >> 16) & 0xff])

    def __complete(self, msg: Any, subscription: Subscription, socket: Sub0) -> None:
        """
        Complete the subscription setup after receiving a reply from the server.

        Args:
            msg (Any): The reply message from the server.
            subscription (Subscription): The subscription object.
            socket (Sub0): The subscription socket.
        """
        logger.debug(f"[SUBSCRIBE-COMPLETE] Subscription '{subscription.alias()}' completed with id={msg.id}")
        if subscription._complete(msg):
            id_buf = Subscribe.__idBuf(msg.id)
            socket.subscribe(id_buf)
            self.__subscriptions[msg.id] = subscription
            logger.debug(f"[SUBSCRIBE-COMPLETE] Subscription '{subscription.alias()}' active (id={msg.id}), "
                         f"total active: {len(self.__subscriptions)}")
        else:
            logger.debug(f"[SUBSCRIBE-COMPLETE] Failed to complete subscription '{subscription.alias()}'")
