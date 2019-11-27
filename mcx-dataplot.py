#!/usr/bin/python3

#
#   Developer : Philippe Piatkiewitz (philippe.piatkiewitz@vectioneer.com)
#   All rights reserved. Copyright (c) 2019 VECTIONEER.
#

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import argparse
import lzma
from datetime import datetime
import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

def convert_date(timestamp):
    return datetime.fromtimestamp(float(timestamp))

def main():
    # Parse the command line
    parser = argparse.ArgumentParser(prog='mcx-dataplot', description='mcx-dataplot')
    parser.add_argument('-l', '--list', help='List the signals contained in the file and exit', action='store_true')
    parser.add_argument('--output', help='filename of the output plot file', default=None)
    parser.add_argument('file', metavar='FILENAME',
                        help='Inputfile in CSV format or xv (LZMA) compressed CSV. First line is a list of signal names. First column is interpreted as x-axis by default.',
                        default="data.csv")
    parser.add_argument('-s', '--signals', help='''List of signals to plot. Example: -s 1,2:3 4:5.
                                                Where "," adds the next signal to the same axis.
                                                ":" indicates creation of an additional y-axis in the same plot and
                                                <SPACE> creates a new subplot.''', nargs='+', type=str, required=False,
                        default=None)
    parser.add_argument('-x', '--xaxis', help='Column to use as x-axis', type=int, default=0)
    parser.add_argument('--drawstyle',
                        help='interpolation type. One of "default", "steps", "steps-pre", "steps-mid", "steps-post"',
                        default='default')
    parser.add_argument('--yrange', help='Range of the y-axis', nargs='+', default=None, type=float)
    parser.add_argument('--nodateconv', help='Do not convert the first column to a date.', action='store_true')
    args = parser.parse_args()
    FILENAME = args.file
    PLOTCOLS = args.signals
    XAXIS = args.xaxis
    DRAWSTYLE = args.drawstyle
    AXISOFFSET = 50
    OUTPUT = args.output

    # Prepare some plot style
    font = {'size': 6}
    plt.rc('font', **font)

    # Read the input file
    if (FILENAME[-2:] == "xz"):
        fd = lzma.open(FILENAME, "rt")
    else:
        fd = open(FILENAME, "r")
    colnames = [x.strip() for x in fd.readline().split(",")]
    if (args.list or (not PLOTCOLS)):
        cnt = 0
        for signal in colnames:
            print("%2d " % cnt + signal)
            cnt = cnt + 1
        return

    fd.seek(0)
    if args.nodateconv:
        P = pd.read_csv(fd,
                        sep=',',
                        header=0,
                        skip_blank_lines=False,
                        )
    else:
        P = pd.read_csv(fd,
                        sep=',',
                        header=0,
                        skip_blank_lines=False,
                        converters={0: convert_date},
                        )

    # Determine current color list
    prop_cycle = plt.rcParams['axes.prop_cycle']
    colors = prop_cycle.by_key()['color']

    # Generate plots
    fig = plt.figure(figsize=(16, 9), tight_layout=True)
    numplots = len(PLOTCOLS)
    plotID = 1
    ax = None
    for signallist in PLOTCOLS:
        columns = signallist.split(':')
        #signalsInThisPlot = []
        ax = plt.subplot(numplots, 1, plotID, sharex=ax)
        coloridx = 0
        newax = None
        axOffs = 0
        for col in columns:
            if newax is None:
                newax = ax
            else:
                newax = ax.twinx()
                newax.yaxis.set_ticks_position('right')
                newax.spines['right'].set_position(('outward', axOffs))
                newax.tick_params('y', colors=colors[coloridx])
                axOffs += AXISOFFSET
            colsOnThisAx = list(map(int, col.split(',')))
            for signal in colsOnThisAx:
                if XAXIS!=signal:
                    P.plot(x=P.columns[XAXIS], y=P.columns[signal], ax=newax, linewidth=1, alpha=0.9, drawstyle=DRAWSTYLE, color=colors[coloridx])
                else:
                    print("Cannot plot column %d against itself, skipping plot."%signal)
                coloridx = coloridx + 1
                if coloridx >= len(colors):
                    coloridx = 0
        newax.legend(framealpha=0.3)
        if (P.dtypes[XAXIS] == 'datetime64[ns]'):
            locator = mdates.AutoDateLocator(maxticks=20)
            formatter = mdates.AutoDateFormatter(locator)
            newax.xaxis.set_major_locator(locator)
            newax.xaxis.set_major_formatter(formatter)
        if (args.yrange):
            plt.ylim(bottom=args.yrange[0])
            if (len(args.yrange) > 1):
                plt.ylim(top=args.yrange[1])
        if plotID == 1:
            plt.title(FILENAME)
        newax.grid("on")
        plotID += 1

    plt.xlabel(colnames[XAXIS])
    fig.tight_layout()
    if OUTPUT:
        plt.savefig(OUTPUT)
    else:
        plt.show()

if __name__ == '__main__':
    main()
