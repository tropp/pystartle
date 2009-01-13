#!/usr/bin/env python
"""
Python class Wrapper for Qwt library for simple plots.
Includes the following methods:
PlotClear clears the selected plat
PlotLine is a matlab-like plotting routine for drawing lines, with
optional symbols, colors, etc. This is only to access the most common
plotting attributes for simple data plots, by mapping from the Qwt names
to the matlab names. 
"""
# January, 2009
# Paul B. Manis, Ph.D.
# UNC Chapel Hill
# Department of Otolaryngology/Head and Neck Surgery
# Supported by NIH Grants DC000425-22 and DC004551-07 to PBM.
# Copyright Paul Manis, 2009
#
"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
"""
    Additional Terms:
    The author(s) would appreciate that any modifications to this program, or
    corrections of erros, be reported to the principal author, Paul Manis, at
    pmanis@med.unc.edu, with the subject line "PySounds Modifications". 
    
    Note: This program also relies on the TrollTech Qt libraries for the GUI.
    You must obtain these libraries from TrollTech directly, under their license
    to use the program.
"""

import sys
from PyQt4 import Qt
import PyQt4.Qwt5 as Qwt
from PyQt4.Qwt5.anynumpy import *

class MPlot:
    
    def __init__(self):
        self.colorMap = {'black': Qt.Qt.black,
                         'k': Qt.Qt.black,
                         'blue': Qt.Qt.blue,
                         'b': Qt.Qt.blue,
                         'green':Qt.Qt.green,
                         'g': Qt.Qt.green,
                         'red': Qt.Qt.red,
                         'r': Qt.Qt.red,
                         'yellow': Qt.Qt.yellow,
                         'y': Qt.Qt.yellow,
                         'cyan': Qt.Qt.cyan,
                         'c': Qt.Qt.cyan,
                         'white': Qt.Qt.white,
                         'w': Qt.Qt.white,
                         'magenta': Qt.Qt.magenta,
                         'm': Qt.Qt.magenta
                        }
        self.symbolMap = {'Ellipse': Qwt.QwtSymbol.Ellipse, 'o' : Qwt.QwtSymbol.Ellipse,
                        'Rect' : Qwt.QwtSymbol.Rect, 's' : Qwt.QwtSymbol.Rect,
                        'Diamond' : Qwt.QwtSymbol.Diamond, 'd' : Qwt.QwtSymbol.Diamond,
                        'Triangle' : Qwt.QwtSymbol.Triangle, 't' : Qwt.QwtSymbol.Triangle,
                        'DTriangle' : Qwt.QwtSymbol.DTriangle, 'v' : Qwt.QwtSymbol.DTriangle,
                        'UTriangle' : Qwt.QwtSymbol.UTriangle, '^' : Qwt.QwtSymbol.UTriangle,
                        'LTriangle' : Qwt.QwtSymbol.LTriangle, 'l' : Qwt.QwtSymbol.LTriangle,
                        'RTriangle' : Qwt.QwtSymbol.RTriangle, 'r' : Qwt.QwtSymbol.RTriangle,
                        'Cross' : Qwt.QwtSymbol.Cross, '+' : Qwt.QwtSymbol.Cross, 
                        'X' : Qwt.QwtSymbol.XCross, 'x' : Qwt.QwtSymbol.XCross, 
                        'HLine' : Qwt.QwtSymbol.HLine, '-' : Qwt.QwtSymbol.HLine,
                        'VLine' : Qwt.QwtSymbol.VLine, '|' : Qwt.QwtSymbol.VLine,
                        'Star1' : Qwt.QwtSymbol.Star1, '*' : Qwt.QwtSymbol.Star1,
                        'Star2' : Qwt.QwtSymbol.Star2, '@' : Qwt.QwtSymbol.Star2,
                        'Hexagon' : Qwt.QwtSymbol.Hexagon, 'h': Qwt.QwtSymbol.Hexagon
                        }
        self.defaultBkColor = Qt.Qt.white
        self.xlabel = None
        self.ylabel = None
        self.plotList = []
        
#        self.lineMap = {NoLine         = PenStyle(Qt.NoPen) 
#SolidLine      = PenStyle(Qt.SolidLine)
#DashLine       = PenStyle(Qt.DashLine)
#DotLine        = PenStyle(Qt.DotLine)
#DashDotLine    = PenStyle(Qt.DashDotLine)
#DashDotDotLine = PenStyle(Qt.DashDotDotLine)
#}

    def setXYReport(self, xlabel, ylabel):
        if xlabel != None:
            self.xlabel = xlabel
        else:
            self.xlabel = None
        if ylabel != None:
            self.ylabel = ylabel
        else:
            self.ylabel = None
             
    def PlotTracking(self, theplot):
        """Initialize tracking
        """        
        theplot.connect(Spy(theplot.canvas()),
                     Qt.SIGNAL("MouseMove"),
                     self.showCoordinates)
        
    def showCoordinates(self, position, thecanvas):
        pl = thecanvas.plot() # the plot from the canvas    
        if self.xlabel != None:
            self.xlabel.setText('x:%.6g' % (
                pl.invTransform(Qwt.QwtPlot.xBottom, position.x())))
            self.ylabel.setText('y:%.6g' % (
                pl.invTransform(Qwt.QwtPlot.yLeft, position.y())))
        
    def PlotZooming(self, theplot):
        """Initialize zooming
        """
        if not hasattr(theplot, 'zoomer'): # only attach the zoomer to the plot at the start
            theplot.zoomer = Qwt.QwtPlotZoomer(Qwt.QwtPlot.xBottom,
                                        Qwt.QwtPlot.yLeft,
                                        Qwt.QwtPicker.DragSelection,
                                        Qwt.QwtPicker.AlwaysOff,
                                        theplot.canvas())
            theplot.zoomer.setRubberBandPen(Qt.QPen(Qt.Qt.red))
            theplot.zoomer.initMousePattern(2)
        theplot.setAxisAutoScale(Qwt.QwtPlot.yLeft) # make sure we are autoscaled
        theplot.setAxisAutoScale(Qwt.QwtPlot.xBottom)
        theplot.zoomer.setZoomBase() # make sure we reset the base to be save
        


    def getColor(self, color):
        if color == None:
            qcolor = Qt.Qt.black
        else:
            try:
                qcolor = self.colorMap[color]
            except:
                qcolor = self.defaultBkColor
        return(qcolor)
        
    def getSymbol(self, symbol):
        qsymbol = None
        try:
            qsymbol = self.symbolMap[symbol]
        except:
            pass
        return(qsymbol)
    
    def setDefaultBkColor(self, bkcolor):
        self.defaultBkColor = self.getColor(bkcolor)
    
    def getPlotList(self): # provide plot list to main program for management
        return(self.plotList)
        
    def PlotReset(self, plot, bkcolor=None, mouse=True, zoom=True, xlabel=None, ylabel=None):
        if plot not in self.plotList:
            self.plotList.append(plot)
        plot.clear()
        if bkcolor != None:
            plot.setCanvasBackground(self.getColor(bkcolor))
        else:
            plot.setCanvasBackground(self.defaultBkColor)
        if xlabel != None:
            plot.setAxisTitle(Qwt.QwtPlot.xBottom, xlabel)
        if ylabel != None:
            plot.setAxisTitle(Qwt.QwtPlot.yLeft, ylabel)
        plot.replot()
        if mouse:
            self.PlotTracking(plot)
        if zoom:
            self.PlotZooming(plot) # attach a zoomer
        
    def PlotLine(self, plot, x, y, color='k', linestyle = '-', linethick = 1,
                 symbol=None, symbolsize = 9, symbolcolor = None, symbolthick = 1):
        cu = Qwt.QwtPlotCurve()
        cu.setPen(Qt.QPen(self.getColor(color)))
        if linestyle == '':
            cu.setStyle(Qwt.QwtPlotCurve.NoCurve)
        else:
            cu.setStyle(Qwt.QwtPlotCurve.Lines)
            
        if symbol == None or self.getSymbol(symbol) == None:
            pass
        else:
            scolor = self.getColor(color)
            cu.setSymbol(Qwt.QwtSymbol(self.getSymbol(symbol),
                    Qt.QBrush(scolor),
                    Qt.QPen(scolor, symbolthick),
                    Qt.QSize(int(symbolsize), int(symbolsize))))

        cu.attach(plot)
        cu.setData(x, y)
        if hasattr(plot, 'zoomer'): # need to make sure zoomer base is correct
            plot.zoomer.setZoomBase() # note - calls pending replot anyway
        else:
            plot.replot()
        
        
    # showCoordinates()    
        
class Spy(Qt.QObject):
    
    def __init__(self, parent):
        Qt.QObject.__init__(self, parent)
        parent.setMouseTracking(True)
        parent.installEventFilter(self)

    # __init__()
    
    def eventFilter(self, _, event):
        if event.type() == Qt.QEvent.MouseMove:
            self.emit(Qt.SIGNAL("MouseMove"), event.pos(), self.parent())
        return False

    # eventFilter()

# class Spy