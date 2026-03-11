#!/usr/bin/python3

#
#   Developer: Alexey Zakharov (alexey.zakharov@vectioneer.com)
#   All rights reserved. Copyright (c) 2025 VECTIONEER.
#

from queue import Queue, Empty
import threading
from motorcortex.setup_logger import logger

from typing import Any, Callable, Optional, Tuple


class StateCallbackHandler:
    """
    Handles state change callbacks processing.

    This class manages a background thread and a queue to process state update notifications
    using a user-provided callback function.
    """

    def __init__(self) -> None:
        """
        Initializes the StateCallbackHandler.
        """
        self.running: bool = False
        self.callback_queue: Queue = Queue()
        self.callback_thread: Optional[threading.Thread] = None
        self.state_update_handler: Optional[Callable[..., Any]] = None

    def start(self, state_update_handler: Callable[..., Any]) -> None:
        """
        Start the callback handler with the given update function.

        Args:
            state_update_handler (Callable[..., Any]):
                The function to call when a state update is notified. Should accept arbitrary arguments.
        """
        if state_update_handler:
            self.state_update_handler = state_update_handler
            self.running = True
            self.callback_thread = threading.Thread(
                target=self.__process_callbacks,
                daemon=True
            )
            self.callback_thread.start()

    def stop(self) -> None:
        """
        Stop the callback handler and clean up resources.
        """
        self.running = False
        if self.callback_thread:
            self.callback_queue.put(None)  # Signal thread to exit
            self.callback_thread.join(timeout=1.0)
            self.callback_thread = None
        self.state_update_handler = None

    def notify(self, *args: Any) -> None:
        """
        Queue a state update notification.

        Args:
            *args (Any): Arguments to pass to the state update handler.
        """
        if self.state_update_handler:
            self.callback_queue.put(args)

    def __process_callbacks(self) -> None:
        """
        Process callbacks in a dedicated thread.
        """
        while self.running:
            try:
                args = self.callback_queue.get(timeout=0.1)
                if args is None:  # Stop signal
                    break
                try:
                    self.state_update_handler(*args)
                except Exception as e:
                    logger.exception("Error in state callback: %s", e)
            except Empty:
                continue
            except Exception as e:
                if self.running:
                    logger.exception("Error processing callbacks: %s", e)
