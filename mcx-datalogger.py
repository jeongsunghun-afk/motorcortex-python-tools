#!/usr/bin/python3

#
#   Developer : Alexey Zakharov (alexey.zakharov@vectioneer.com)
#               Philippe Piatkiewitz (philippe.piatkiewitz@vectioneer.com)
#   All rights reserved. Copyright (c) 2019 VECTIONEER.
#

from motorcortex_tools.datalogger import DataLogger
import argparse
import operator
import time
import json


# DEFAULTHOST = "192.168.2.100"
DEFAULTURL = "wss://192.168.2.100:5568:5567"
DEFAULTCERT="mcx.cert.pem"
DEFAULTFREQDIV = 10
DEFAULTTRIGGERINTERVAL = 0.5

def createFileName(folder=".", filename=None, comment=None, extension=".csv"):
    TIMESTRING = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    if filename:
        return folder+"/"+filename
    else:
        if comment:
            comment = comment.replace(" ", "_")
            return folder+"/"+TIMESTRING + "_" + comment + extension
        else:
            return folder+"/"+TIMESTRING + extension

def main():
    # Parse the command line
    DESC = """
    Log data from a MOTORCORTEX Server to a CSV file.
    """
    parser = argparse.ArgumentParser(description=DESC)
    parser.add_argument('-p', '--parameterfile',
                        help='JSON file that contains a list of parameters to log. \
                        The JSON file shall have the following format: \n \
                        \
                        [{"path":"root/signal1"}, {"path":"root/signal2"}, ...]',
                        required=True, default="parameters.json")
    parser.add_argument('-f', '--file', help='Specify the filename that the data will be saved to. \
                        By default the filename is created based on the current date and time', required=False, default=None)
    parser.add_argument('-F', '--folder', help='Folder where output files are placed', required=False, type=str, default=".")
    parser.add_argument('-c', '--comment', help='Comment to append to filename', nargs='+', required=False, type=str)
    # parser.add_argument('-H', '--host', help='Host to connect to (Default: %s)' % DEFAULTHOST, required=False,
    #                     default=DEFAULTHOST)
    parser.add_argument('-u', '--url', help='URL to connect to (Default: %s)' % DEFAULTURL, required=False,
                        default=DEFAULTURL)
    parser.add_argument('-s', '--certificate', help='Certificate to use when connecting securely. (Default: %s)' % DEFAULTCERT, required=False,
                        default=DEFAULTCERT)
    parser.add_argument('-d', '--divider', help='Frequency Divider; specifies the amount of downsampling that occurs at the server.\
                                                 The server only then sends every N-th sample. Setting the Frequency Divider to 1 \
                                                 will send at the maximum rate that the server supports. (Default: %d)' % DEFAULTFREQDIV, required=False,
                        type=int, default=DEFAULTFREQDIV)
    parser.add_argument('--trigger',
                        help='Path to the signal that is monitored at the given TRGGERINTERVAL. \
                        The logger is started whenever the trigger condition is met.',
                        required=False, default=None)
    parser.add_argument('--triggerinterval', help='Trigger interval in seconds; the interval at which the trigger parameter is checked. \
                         (default: %.3f s)'%DEFAULTTRIGGERINTERVAL, required=False, default=DEFAULTTRIGGERINTERVAL)
    parser.add_argument('--triggervalue', help='Trigger value; the value the trigger is compared to.', required=False, default=True)
    parser.add_argument('--triggerop', help='Trigger operator; the operator that is used for comparison.', required=False, default="==", choices=['==','<','>','<=','>=','!='],)
    parser.add_argument('-C', '--compress', help='Compress the traces on the fly using the LZMA algorithm. It creates files with the xz extension.', required=False, action='store_true')
    parser.add_argument('--noparamdump', help='Do not dump parameters to file for each trace.', required=False, action='store_true')
    parser.add_argument('--watchdogpulse', help='Send a watchdog parameter update to specified parameter at \
                                                 triggerinterval pulses per second. The value that is sent to the \
                                                 parameter is true. It is expected that the server resets the parameter \
                                                 to false cyclically.', required=False, default=None)

    args = parser.parse_args()
    INPUTFILE = args.parameterfile
    comment = None
    FOLDER=args.folder
    OUTPUTFILE = createFileName(folder=FOLDER, filename=args.file, comment=comment)

    # HOST = args.host
    TRIGGER = args.trigger
    WDG = args.watchdogpulse
    TRIGGERVAL = float(args.triggervalue)
    TRIGGERINTERVAL = args.triggerinterval
    TRIGGEROP = args.triggerop
    if (TRIGGEROP == "<"):
      OP = operator.lt
    elif (TRIGGEROP == ">"):
      OP = operator.gt
    elif (TRIGGEROP == ">="):
      OP = operator.ge
    elif (TRIGGEROP == "<="):
      OP = operator.le
    elif (TRIGGEROP == "=="):
      OP = operator.eq
    elif (TRIGGEROP == "="):
      OP = operator.eq
    elif (TRIGGEROP == "!="):
      OP = operator.ne
    else:
      print("unknown operator %s" %TRIGGEROP)

    infile = open(INPUTFILE, "r")
    J = json.load(infile)
    infile.close()
    parameters = []
    # print("Parameters to log:")
    for i in J:
        # print("%s"%i["path"])
        parameters.append(i["path"])

    logger = DataLogger(args.url, parameters, divider=args.divider, certificate=args.certificate)
    if not logger.connected:
        exit(1)
    if TRIGGER:
        try:
            while True:
                if (OP(logger.req.getParameter(TRIGGER).get().value[0],TRIGGERVAL)):
                    if not logger.working:
                        FILENAME = createFileName(folder=FOLDER, comment=comment)
                        logger.openFileAndWriteHeader(FILENAME, compress = args.compress)
                        logger.start()
                        logger.writeParameters(FILENAME + ".params")
                else:
                    if logger.working:
                        logger.stop()
                        logger.closeFile()
                if WDG:
                    logger.req.setParameter(WDG, True).get()
                time.sleep(TRIGGERINTERVAL)
        except KeyboardInterrupt:
            if logger.working:
                logger.stop()
                logger.closeFile()
            logger.close()
    else:
        logger.openFileAndWriteHeader(OUTPUTFILE, compress = args.compress)
        logger.start()
        if (not args.noparamdump):
            logger.writeParameters(OUTPUTFILE + ".params")
        print("Press CTRL-BREAK (CTRL-C) to finish logging ...")
        while True:
            try:
                if WDG:
                    logger.req.setParameter(WDG, True).get()
                time.sleep(TRIGGERINTERVAL)
            except KeyboardInterrupt:
                break
            except:
                break
        logger.stop()
        logger.close()


if __name__ == '__main__':
    main()
