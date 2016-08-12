#!/usr/bin/env python

# classes pulled from MPlot
# to use with PyQtGraph... 
# these are the ones that are independent of Qwt, only
#
import numpy

class MPH:
    def __init__(self):
        pass

    def labelUp(self, plot, xtext, ytext, title):
        """helper to label up the plot"""
        plot.setLabel('bottom', xtext)
        plot.setLabel('left', ytext)
        plot.setTitle(title)
    
    def semiLogX(self, plothandle, xdata, ydata, ticklist=None, minorTickList=None, range=None):
        if xdata[0] == 0.0:
            si = 1
        else:
            si = 0
        lxd = numpy.log10(xdata[si:])
        plothandle.plot(lxd, ydata[si:])
        if ticklist is not None:
            tl = []
            for t in ticklist:
                tl.append( (numpy.log10(t), str(t)))
        plothandle.getAxis('bottom').setTicks([tl])
        if range is not None and len(range) == 2:
            plothandle.setXRange(numpy.log10(range[0]), numpy.log10(range[1]))


################################################################################
# The TabPlotList class stores and returns information about the plots
# in a graphtab window.
# this should be invoked for each graph tab, or better, a single variable
# in the caller can be used to refer to the entire graph window.
# The basic structure is a dictionary of 'Graph Names' (they'd better
# be unique then); each element of the dictionary consists of the graph
# name as a key, the graph tab number, and list of plots (QwtPlot entries).
# methods are provided for maintaining the list and returning whole or parts of
# the entries.
class TabPlotList:
    def __init__(self, graph = None, tabNumber = 0):
        self.Graph={}
        if graph is not None:
            self.addGraph(graph, tabNumber)

    def addGraph(self, graph, tabNumber):
        self.Graph[graph]=[tabNumber, []]

    def appendPlot(self, graph, plot):
        self.Graph[graph][1].append(plot)

    def removeGraph(self, graph):
        del self.Graph[graph]

    def removePlots(self, graph):
        self.Graph[graph][1] = [] # this JUST initializes the plots list

    def updatePlots(self, graph):
        self.removePlots(graph) # clear out existing list

    def printList(self):
        for gr in self.glist():
            print "Graph:",
            print gr
            print ' Plots:: ',
            for pl in self.list(gr):
                print "   plot:",
                print dir(pl)

# list method is iterable, returns the plots in the current graph window
    def list(self, graph):
        if self.Graph.has_key(graph):
            for index in range(0,len(self.Graph[graph][1])):
                yield self.Graph[graph][1][index]

# glist is iterable, returns keys in graph list
    def glist(self):
        for index in self.Graph.keys():
            yield index

    def getTab(self, graph): # only return the tab associated with the graph
        if self.Graph.has_key(graph):
            return(self.Graph[graph][0])
        else:
            print "key \"%s\" is not in Graph table" % (graph)
            return (-1)

    def setTab(self, tabPtr, graph):
        if self.Graph.has_key(graph):
            tabPtr.setCurrentIndex(self.Graph[graph][0]) # select our tab# get parameters form the gui
        else:
            print "key \"%s\" is not in Graph table" % (graph)
            return (-1)

    def getGraphKeyAtTab(self, tabno):
        for index in self.Graph.keys():
            if self.Graph[index][0] == tabno:
                return index
        return [] # nothing if not found

    def getPlots(self, graph):
        if self.Graph.has_key(graph):
            return self.Graph[graph][1]
        else:
            print "key \"%s\" is not in Graph table" % (graph)
            return []
