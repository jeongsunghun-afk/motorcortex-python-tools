#!/usr/bin/python3

#
#   Developer : Philippe Piatkiewitz (philippe.piatkiewitz@vectioneer.com)
#   All rights reserved. Copyright (c) 2019-2022 VECTIONEER.
#

import os
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import motorcortex
from jinja2 import FileSystemLoader, Environment
import time
from motorcortex_tools import *
from motorcortex_tests.act_measure_friction import measureActuatorFriction
from weasyprint import HTML, CSS
import webbrowser

try:
    plt.style.use('templates/styles/plotstyle.mplstyle')
    print("Loaded plotsyle")
except:
    print("Could not load plotstyle")

URL = "wss://192.168.2.100:5568:5567"
TEMPLATESFOLDER="templates"
OUTPUTFOLDER = "results/"
PLOTFOLDER = "plots/"
if not os.path.exists(OUTPUTFOLDER+PLOTFOLDER):
    os.makedirs(OUTPUTFOLDER+PLOTFOLDER)

class TestEnvironment:
    def __init__(self, url = URL,
             outputfolder = "results/",
             plotfolder = "plots/", certificate="mcx.cert.crt"):
        self.url = url
        self.certificate = certificate
        self.outputfolder = outputfolder
        self.plotfolder = plotfolder
        self.connect(self.url, certificate)
        
    def connect(self, url = URL, certificate="mcx.cert.crt"):
        motorcortex_types = motorcortex.MessageTypes()
        parameter_tree = motorcortex.ParameterTree()
        # Open request connection
        req, sub = motorcortex.connect(url, motorcortex_types, parameter_tree,
                                       certificate=certificate, timeout_ms=1000, login="", password="")
        tree = req.getParameterTree().get()
        self.req = req
        self.sub = sub
        
    def close(self):
        self.sub.close()
        self.req.close()

class SystemData():
    def __init__(self):
        # references to common signals
        self.pathToStateCommand = "root/Logic/stateCommand"
        self.pathToActuator = "root/Control/actuatorControlLoop"
        self.pathToSignalGenerator = "root/Control/signalGenerator"
        self.pathToIsEngaged = "root/Logic/isAtEngaged"
        self.pathToPauseMode = "root/Control/gotoPauseMode"
        # requirements
        self.maxFriction = 2.0 # kN
        self.stateCommands = { "Off": 0, "Engage": 2}

        # Velocity Accelration Jerk test
        self.vaj_criteria={"velocity": 1,
                           "acceleration":0,
                           "jerk":0}

    def gotoEngage(self, req):
        print("Engaging Actuator")
        req.setParameter(self.pathToStateCommand, self.stateCommands["Engage"]).get()
        waitFor(req, self.pathToIsEngaged, timeout=10)
        req.setParameter(self.pathToPauseMode, False).get()

    def gotoOff(self, req):
        print("Disengaging actuator")
        req.setParameter(self.pathToStateCommand, self.stateCommands["Off"]).get()

def main():
    # initialize the communication with the controller
    testEnv = TestEnvironment(url = URL,
             outputfolder = OUTPUTFOLDER,
             plotfolder = PLOTFOLDER)
    system = SystemData()

    if (not testEnv.req):
        print("Exiting")
        exit(0)

    # send the system to engaged before starting the tests
    system.gotoEngage(testEnv.req)

    results = []
    ## Append you tests here:
    results.append(measureActuatorFriction(testEnv))

    system.gotoOff(testEnv.req)
    # close communication
    testEnv.close()

    # Render all results
    file_loader = FileSystemLoader(TEMPLATESFOLDER)
    env = Environment(loader=file_loader)
    template = env.get_template("base.html")
    output = template.render(tests = results)
    fd = open(OUTPUTFOLDER + "/output.html","w")
    fd.write(output)
    fd.close()

    # Generate a PDF
    print("Generating PDF")
    timestring = time.strftime("%Y-%m-%d_%H-%M-%S")
    pdfname = OUTPUTFOLDER + "/%s-output.pdf"%timestring
    HTML(OUTPUTFOLDER + "/output.html").write_pdf(pdfname)

    # (OPTIONAL) Open the PDF in the browser
    print("Opening Document")
    webbrowser.open(os.getcwd()+"/"+pdfname)

    exit(0)


if __name__ == '__main__':
    main()

