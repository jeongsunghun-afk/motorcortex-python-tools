#!/usr/bin/python3

#
#   Developer : Philippe Piatkiewitz (philippe.piatkiewitz@vectioneer.com)
#   All rights reserved. Copyright (c) 2019 VECTIONEER.
#

import time

import matplotlib.pyplot as plt
import numpy as np
from jinja2 import Template
from motorcortex_tools import *


def measureActuatorFriction(env, pathToActuator="root/Control/actuatorControlLoops/actuatorControlLoop01",
                                 pathToSignalGenerator="root/Control/jointReferenceGenerator/signalGenerator01",
                                 pathToSignalGeneratorEnable="root/Control/jointReferenceGenerator/enable",
                                 amplitude=1, frequencyHz=0.1,
                                 plotForceRange=5.0, centerPlotAtForce=None, title=None, ID=0):
    template = Template("""
    <h2>{{title}}</h2>
    <p>Actuator friction is measured over the total stroke and is measured at very
     slow speeds to minimize dynamic forces acting on the actuator. </p>
    <table>
        <tr><th>Test Conditions</th></tr>
        <tr><td>Date & Time</td><td>{{datetime}}</td></tr>
        <tr><td>amplitude</td><td class="numeric">{{amplitude}}</td></tr>
        <tr><td>frequency</td><td class="numeric">{{frequencyHz}} Hz</td></tr>
        <tr><th>Measurement</th></tr>
        <tr><td>Static Torque at midstroke</td><td class="numeric">{{'%0.3f' % fstat_at_midstroke}} Nm</td></tr>
        <tr><td>Torque at midstroke</td><td class="numeric">{{'%0.3f' % friction_at_midstroke}} Nm</td></tr>
    </table>
    <img src="{{plot}}">
    """)

    pathToPosition = pathToActuator + "/actualPosition"
    pathToForce = pathToActuator + "/actualTorque"

    req = env.req
    print("Measure Static Torque")
    NumSamples = 20
    sum = 0
    for cnt in range(0, NumSamples):
        sum = sum + req.getParameter(pathToForce).get().value[0]
        time.sleep(0.05)
    staticForceInMidstroke = sum / NumSamples
    if centerPlotAtForce:
        centerPlotAt = centerPlotAtForce
    else:
        centerPlotAt = staticForceInMidstroke
        
        
    print("Start Motion")
    # Set the signal type 
    req.setParameter(pathToSignalGenerator+"/signalType", 4).get()
    req.setParameter(pathToSignalGenerator+"/amplitude", amplitude).get()
    req.setParameter(pathToSignalGenerator+"/frequency", frequencyHz*2*np.pi).get()
    req.setParameter(pathToSignalGeneratorEnable, True).get()
    time.sleep(req.getParameter(pathToSignalGenerator+"/newSettingFadeTime").get().value[0])
    waitFor(req, pathToSignalGenerator + "/enableIsOn", timeout=10)
        
    print("Starting Datalogger")
    logger = DataLogger(env.url, [pathToPosition, pathToForce], certificate=env.certificate, divider=10)
    logger.start()

    # Wait 
    print("Waiting for measurement to complete")
    time.sleep(1/frequencyHz)

    print("Stopping Datalogger")
    logger.stop()
    logger.close()

    print("Stopping Signal Generator")
    req.setParameter(pathToSignalGeneratorEnable, False).get()
    waitFor(req, pathToSignalGenerator + "/enableIsOff", timeout=10)
    req.setParameter(pathToSignalGenerator+"/signalType", 0).get()

    print("Done")
    # generate the plot
    x = np.array(logger.traces[pathToPosition]["y"][0]).transpose()
    y = np.array(logger.traces[pathToForce]["y"][0]).transpose()
    meany = np.mean(y)
    minx = np.min(x)
    maxx = np.max(x)
    xrange = maxx - minx
    midx = minx + xrange * 0.5
    delta = 0.01
    idxaroundmin = np.where((x > midx - delta) & (x < midx + delta))
    yaroundmid = y[idxaroundmin]
    friction_at_midstroke = np.max(yaroundmid) - np.min(yaroundmid)
    fig = plt.figure()
    plt.plot(x, y), plt.xlabel("position (rad)"), plt.ylabel("torque (Nm)")
    ax = plt.gca()
    ax.set_ylim([centerPlotAt - 0.5 * plotForceRange, centerPlotAt + 0.5 * plotForceRange])
    plt.title("Friction")
    plt.savefig(env.outputfolder + env.plotfolder + "friction%03d.png" % ID)

    titlestr = ""
    if (title):
        titlestr = " - %s" % title
    output = template.render(title="Actuator Friction" + titlestr,
                             datetime=time.strftime("%Y-%m-%d %H:%M:%S"),
                             friction_at_midstroke=friction_at_midstroke,
                             fstat_at_midstroke=staticForceInMidstroke,
                             amplitude=amplitude,
                             frequencyHz=frequencyHz,
                             plot=env.plotfolder + "friction%03d.png" % ID)
    return output
