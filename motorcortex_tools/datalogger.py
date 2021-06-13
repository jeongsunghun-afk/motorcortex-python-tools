#!/usr/bin/python3

#
#   Developer : Alexey Zakharov (alexey.zakharov@vectioneer.com)
#               Philippe Piatkiewitz (philippe.piatkiewitz@vectioneer.com)
#   All rights reserved. Copyright (c) 2018 VECTIONEER.
#

import motorcortex
import lzma

class DataLogger:
    """
    A Motorcortex tool to subscribe to signals from a server and store
    them in memory or stream them to a file.

    By default, the data is stored to memory when start() is called without
    a call to openFileAndWriteHeader() first. The data can be accessed in
    the objects traces property. traces is a dictionary, where the keys are
    the path names and the values another dictionary where key "t" contains
    a list of timestamps and key "y" contains a list of values. The lists
    for "t" and "y" have the same length.

    e.g. to plot some trace in matplotlib use:
    plot(logger.traces["/path/to/variable"]["t"], logger.traces["/path/to/variable"]["y"][0])
    where logger is an instance of the DataLogger class.

    To save data to a file the method openFileAndWriteHeader() must be called
    before start(). In this case the data is not stored in memory and the traces property
    is equal to None.


    Attributes
    ----------
    server : str
        the address or hostname of the server to connect to
    paths : str
        a list of paths to subscribe to
    divider : int, optional
        frequency divider
    login : str, optional
        user name used when logging in
    password : str, optional
        password used when logging in
    certificate : str, optional
        TLS certificate


    Methods
    -------
    connect(server, login="", password="", certificate="mcx.cert.pem")
        connects to a server
    openFileAndWriteHeader(filename)
        opens a file and writes the header information to that file
    writeParameters(filename)
        read all the parameters and values from the server and saves them to a file in JSON format
    start()
        start logging
    stop()
        stop logging
    closeFile()
        close the current file
    close()
        close the file (if open) and the connection
    """
    def __init__(self, url, paths, divider=10, login="", password="", certificate="mcx.cert.crt"):
        """
        :param url: the address of the server to connect to in the format wss://[host]:[sub_port]:[req_port]
        :param paths: a list of paths to subscribe to
        :param divider: frequency divider
        :param login: user name used when logging in
        :param password: password used when logging in
        :param certificate: TLS certificate
        """
        self.req = None
        self.sub = None
        # self.requestedpaths = paths
        self.paths = []
        self.file = None
        # Creating empty object for parameter tree
        self.tree = None
        self.subscription = None
        self.divider = divider
        self.traces = {}
        self.working = False

        self.connected = self.connect(url, login=login, password=password, certificate=certificate)
        if self.connected:
            self.__initTraces(paths)

    def connect(self, url, login, password, certificate="mcx.cert.pem", conn_timeout_ms=1000):
        """
        Connect to a Motorcortex server and login

        :param url: the address of the server to connect to in the format wss://[host]:[sub_port]:[req_port]
        :param login: user name used when logging in
        :param password: password used when logging in
        :param certificate: certificate file to use when connecting with a secure connection
        :param conn_timeout_ms: connection timeout in ms
        :param certificate: TLS certificate
        :return: True if connected, false if an error occurred
        """
        """
        Connect to a Motorcortex server and login
        """
        parameter_tree = motorcortex.ParameterTree()
        # Open request connection
        try:
          self.req, self.sub = motorcortex.connect(url, motorcortex.MessageTypes(), parameter_tree,
                                           certificate=certificate, timeout_ms=conn_timeout_ms,
                                           login=login, password=password)

        except RuntimeError as err:
            print("Failed to connect to {}, {}".format(url, err))
            return False

        self.tree = parameter_tree.getParameterTree()
        print("%d parameters in tree"%len(self.tree))
        return True

    def __messageReceived(self, parameters):
        """
        Callback that is called when a message is received
        """
        if self.file:
            # Do not store the data into memory
            # just write it to disk
            self.file.write("%d.%09d" % (parameters[0].timestamp.sec, parameters[0].timestamp.nsec))
            for cnt in range(0, len(parameters)):
                path = self.paths[cnt]["path"]
                param = parameters[cnt]
                i = 0
                for p in param.value:
                    # let python figure out how to print different types to sting
                    self.file.write(", %s" % p)
                    i = i + 1
            self.file.write("\n")
        else:
            # Store the data into memory
            for cnt in range(0, len(parameters)):
                path = self.paths[cnt]["path"]
                param = parameters[cnt]
                self.traces[path]["t"].append(param.timestamp.sec + param.timestamp.nsec * 1e-9)
                i = 0
                for p in param.value:
                    self.traces[path]["y"][i].append(p)
                    i = i + 1

    def __initTraces(self, requestedpaths):
        """
        Initialize memory where data from traces is stored
        """
        returnVal = True
        for v in requestedpaths:
            pathFound = False
            for item in self.tree:
                if v == item.path:
                    self.paths.append({"path": v, "number_of_elements": item.number_of_elements})
                    pathFound = True
            if (not pathFound):
                print("Parameter \"%s\" not found in tree!" % v)
                returnVal = False
        for path in self.paths:
            x = {"t": [], "y": []}
            for cnt in range(0, path["number_of_elements"]):
                x["y"].append([])
            self.traces[path["path"]] = x
        return returnVal

    def openFileAndWriteHeader(self, filename, compress=False):
        """
        Open a file an write the header containing column names for each signal
        """
        if compress:
            self.file = lzma.open(filename+'.xz', 'wt', preset=0)
        else:
            self.file = open(filename, 'w', buffering=1)
        self.file.write("time")
        returnVal = True
        for path in self.paths:
            v = path["path"]
            if (path["number_of_elements"] > 1):
                for i in range(path["number_of_elements"]):
                    self.file.write(", %s[%d]" % (v, i))
            else:
                self.file.write(", %s" % v)
        self.file.write("\n")
        return returnVal

    def writeParameters(self, filename):
        """
        Get all values for the Parameters in the tree and write them to a file.

        This is usefull for keeping a record of the server settings when the traces
        were made.
        """
        print("Getting Parameters from Tree...")
        fd = open(filename, 'w', buffering=1)
        for leaf in self.tree:
            if leaf.param_type == 256:
                try:
                  values = self.req.getParameter(leaf.path).get().value
                  line = leaf.path
                  for v in values:
                      line += " %s" % v
                  line += "\n"
                  fd.write(line)
                except:
                  print("Could not read paramater %s"%leaf.path)
        fd.close()

    def start(self):
        """
        Subscribe to the selected signals and start recording
        """
        print("Starting logger")
        paths = []
        for p in self.paths:
            paths.append(p["path"])
        self.subscription = self.sub.subscribe(paths, 'group1', self.divider)
        self.subscription.get(10)
        self.subscription.notify(self.__messageReceived)
        self.working = True

    def stop(self):
        """
        Stop recording and unsubscribe
        """
        print("Stopping logger")
        self.working = False
        self.sub.unsubscribe(self.subscription)

    def closeFile(self):
        """
        Close the current file, but stay connected.

        It is possible to create a new file by calling openFileAndWriteHeader()
        """
        if self.file:
            self.file.close()
            self.file = None

    def close(self):
        """
        Close the current file and disconnect.

        To start a new recording you need to call connect() first.
        """
        self.closeFile()
        self.sub.close()
        self.req.close()

