#!/usr/bin/python 
"""
Acoustic Startle Program
Python version

This program generates sound in one channel (L), followed by a startle stimulus
(noise burst) in the other channel (R).
The conditioning sound can be one of:
tone pip before the startle
tone with gap before the startle
bandpass noise burst
bandpass noise burst with gap before the startle

Requires: PySounds.py which in turn requires pyaudio and nidaq
Modified to use PyQtGraph

Requires: Utility.py - some utilities (fft, wrappers)


For PySounds:
Output hardware is either an National Instruments DAC card or a system sound card
If the NI DAC is available, TDT system 3 hardware is assumed as well for the
attenuators (PA5) and an RP2.1 to input the startle response.
Second channel of RP2.1 is collected as well. Use this for a microphone input
to monitor sound in the chamber.

Python 2.7
PyQt4, Qt Designer (for Gui)
scipy, numpy
pyaudio

Works with Anaconda distribution on Mac OS X and Windows.
"""

# November, 2008
# Paul B. Manis, Ph.D.
# UNC Chapel Hill
# Department of Otolaryngology/Head and Neck Surgery
# Supported by NIH Grants DC000425-22 and DC004551-07 to PBM.
# Copyright Paul Manis, 2008, 2009
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
import sys, re, os
import datetime
import time
import ConfigParser
import gzip
import cPickle
from collections import deque
from PyQt4 import Qt, QtCore, QtGui
import pyqtgraph as pg

import numpy as np
from matplotlib.font_manager import FontProperties
import matplotlib.pyplot as mpl
import MpyqtHelpers as MPH

from random import sample
# our sound handling module (includes hardware detection and signal generation)
import PySounds
from Utility import Utility 

from PyStartle3_gui import Ui_MainWindow

Sounds = PySounds.PySounds() # instance of sound - and connects to the hardware
Utils = Utility()
MPHL = MPH.MPH()

class PyStartle(QtGui.QMainWindow):
    """
    Main class - instantiates GUI and connects to hardware
    """
    
    def __init__(self):
        (self.hardware, self.out_sampleFreq, self.in_sampleFreq) = Sounds.getHardware()
        print "PyStartle is running with output hardware: %s" % (self.hardware)
        """ In the constructor get the application
            started by constructing a basic QApplication with
            its __init__ method, then adding our slot/signal connections
            and finally starting the exec_loop. """""
        QtGui.QDialog.__init__(self)
        self.debugFlag = False # control printing debug statements.
        self.AutoSave = True
        self.configfile = 'pystartle3.cfg'   # specific to this version.
        self.maxptsplot = 20000 # limit the number of points plotted
        self.in_sampleFreq = 44100.0
        self.recentFiles = deque() # makes a que; in python 2.6, can add # of elements
        self.ch1 = []
        self.ch2 = []
        self.ITI = 10.0
        self.ITI_List = []
        self.Annotation = None
        self.Behavior_states = ['Quiet', 'Grooming', 'Exploring', 'Sleeping', 'Other']
        self.Orientations = ['Front', 'Left', 'Right', 'Back']
        self.response_tb = []# response time base
        self.stim_tb = []# stimuluation time base (not implemented yet..)
        self.PostDuration = 0.35 # seconds after startle  ends to record response
        self.PPGo = False
        self.PP_Notch_F1 = 12000.0 # set defaults for the notch - not in gui yet
        self.PP_Notch_F2 = 14000.0
        self.fileDate = ''
        self.Description = "Acoustic Startle Parameters"
        self.tabPages = MPH.TabPlotList() # initialize the tab plot listings.
        self.tabSelected = 0
        self.ExportName = []
        self.PDFfileName = '<none>'
        self.CurrentTab = 0 # set a default current tab - left most entry
        self.Signal_PlotLegend = None
        self.Response_PlotLegend = None
        
        self.ui = Ui_MainWindow() # this is the ONE THING
        self.ui.setupUi(self)
        self.ui.QuitButton.clicked.connect(self.slotQuit)
        self.ui.actionQuit.triggered.connect(self.slotQuit) 
        self.ui.actionOpen.triggered.connect(self.Analysis_Read) 
#        self.ui.CloseDataWindows.clicked.connect(,
#                     self.slotCloseDataWindows)
        self.ui.ToneTest.clicked.connect(self.ToneTest)
        self.ui.NoiseTest.clicked.connect(self.NoiseTest)
        self.ui.PrePulse_Run.clicked.connect(self.PrePulseStart)
        self.ui.PrePulse_Stop.clicked.connect(self.PrePulseStop)
        self.ui.Save_Params.clicked.connect(self.writeini)
        self.ui.Load_Params.clicked.connect(self.readini)
        self.ui.Write_Data.clicked.connect(self.Write_Data)
        self.ui.Analysis_Read.clicked.connect(self.Analysis_Read)
        self.ui.Analysis_ReRead.clicked.connect(self.Analysis_ReRead)
        self.ui.Analysis_Test.clicked.connect(self.Analysis_Test)
        self.ui.Analysis_Analyze.clicked.connect(self.Analyze_Data)
        self.ui.Analysis_lineEdit.editingFinished.connect(self.Analysis_lineEdit)
        self.ui.Annotate_Reset.clicked.connect(self.resetTable)
        self.ui.Annotate_Load.clicked.connect(self.loadAnnotation)
        self.ui.Annotate_Save.clicked.connect(self.saveAnnotation)
        self.ui.Annotate_Dump.clicked.connect(self.dumpTable)
        self.ui.AnnotateVideoDelay.valueChanged.connect(self.updateAnnotateTime)
        self.ui.Startle_Debug.clicked.connect(self.Startle_Debug)
        self.ui.Hardware_Debug.clicked.connect(self.Hardware_Debug)
        self.ui.Igor_Export.clicked.connect(self.IgorExport) 
        self.ui.exportAsSVG.clicked.connect(self.exportAsSVG) 
        self.ui.exportAsPDF.clicked.connect(self.exportAsPDF) 
        self.ui.exportAsPNG.clicked.connect(self.exportAsPNG) 


        self.ui.GraphTabs.show()
        gt = self.ui.GraphTabs
        gt.currentIndex()
        gt.setCurrentIndex(0)
        for i in range(0, gt.count()):
            gt.setCurrentIndex(i) # select our tab
            gt.autoFillBackground()
            tabPalette = gt.palette()
            tabPalette.setColor(Qt.QPalette.Window, Qt.Qt.white) # graphic object color
            tabPalette.setColor(Qt.QPalette.Base, Qt.Qt.white)
        for w in gt.children(): # these are the stacked widgets and the tabbar
            for wc in w.children(): #
                wcn = str(wc.objectName()) # find the graph tabs here
                if len(wcn) > 0:
                    gindex = gt.indexOf(wc)
                    gtext = str(gt.tabText(gindex))
                    self.tabPages.addGraph(str(gt.tabText(gindex)), gindex)
                if wc.isWidgetType() and wcn.startswith('Graph_Tab_'):
                    for wd in wc.children():
                        wdn = str(wd.objectName())
                        if wdn.startswith('Paper_'): # find the "paper" background widget
                            wd.lower()  # and force it behind everything else.
                        else:
                            pass
                        for we in wd.children(): # for should not be indented, must set under "if wdn.startswith(paper) above
                            wen = str(we.objectName())
                            if we.isWidgetType() and not we.inherits("QLabel"): # we execute these, but they don't work????
                                if len(wen) > 0:
                                    self.tabPages.appendPlot(gtext, we)
                                if hasattr(we, 'setFrameShape'):
                                    we.setFrameShape(Qt.QFrame.NoFrame)
                                if hasattr(we, 'setFrameStyle'):
                                    we.setFrameStyle(Qt.QFrame.Plain)
                                if hasattr(we, 'setLineWidth'):
                                    we.setLineWidth(-1)
                                if hasattr(we, 'setMargin'):
                                    we.setMargin(-1)
                                if hasattr(we, 'replot'):
                                        we.replot()
        gt.repaint()
        gt.show()
        gt.setCurrentIndex(self.tabSelected)

# build the table widget ...

        self.updateTable()
            
        # timer calls NextTrial when timed out
        self.TrialTimer=QtCore.QTimer() # get a Q timer
        self.TrialTimer.timeout.connect(self.NextTrial);
        # MPlots.setXYReport(self.ui.X_Cursor, self.ui.Y_Cursor) # link the cursor to the display
        self.readAnalysisTab()
        self.readParameters()
        self.getConfig(self.configfile)
        #self.readini("pystartle.ini") # read the initialization file if it is there.
        self.setMainWindow() # build the plots
        self.statusBar().showMessage("No File" )   
        self.Status('Welcome to PyStartle V2.2beta')

################################################################################
# utility routines for Gui:
# close the windows and exit
#
################################################################################

    def slotQuit(self):
        try:
            if self.hardware == 'nidaq':
                Sounds.HwOFF()
        finally:
            pass
#        self.slotCloseDataWindows() # should close the matplotlib windows... 
        self.saveConfig(self.configfile)
        
        QtCore.QCoreApplication.quit()

#
# just close the data plot windows (matplotlib windows)
#
    def slotCloseDataWindows(self):
        for i in range(1,5):
            try:
                mpl.close(i)
            except AttributeError:
                pass

    def getCurrentTab(self):
       self.CurrentTab = self.ui.AcquisitionTabs.currentIndex()
       return(self.CurrentTab)

    def setCurrentTab(self, tab = 0):
       self.ui.AcquisitionTabs.setCurrentIndex(tab)
    
    def setGraphTab(self, tab=0):
        self.ui.GraphTabs.setCurrentIndex(tab)
    
    # graph tab selection  (just keep track of what's on top)
    def getGraphTabSelected(self):
        self.tabSelected = self.ui.GraphTabs.currentIndex()

    def IgorExport(self):
        # set up to pass the right info to MPlots.IgorExport
        self.getGraphTabSelected()
        #topPlot = self.tabPages.getGraphKeyAtTab(self.tabSelected)
        # MPlots.IgorExport(self.ui.GraphTabs.currentWidget(), topPlot)
        
    def PrintGraph(self):
        pass
        # MPlots.printGraph(self.ui.GraphTabs.currentWidget()) # send it.
    
    def exportAsSVG(self):
        pass
        # MPlots.exportSVG(self.ui.GraphTabs.currentWidget())
    
    def exportAsPDF(self):
        pass
        # MPlots.exportPDF(self.ui.GraphTabs.currentWidget())

    def exportAsPNG(self):
        pass
        # MPlots.exportPNG(self.ui.GraphTabs.currentWidget())

    def useGracePlot(self):
        self.getGraphTabSelected()
        #topPlot = self.tabPages.getGraphKeyAtTab(self.tabSelected)
        #MPlots.gracePlot(self.ui.GraphTabs.currentWidget(), topPlot)
    
    def Startle_Debug(self):
        self.debugFlag = self.ui.Startle_Debug.isChecked()

    def Hardware_Debug(self):
        flag = self.ui.Hardware_Debug.isChecked()
        if flag:
            Sounds.debugOn()
        else:
            Sounds.debugOff()
                    
# update status window

    def Status(self, text, clear = 0):
        self.ui.Status_Window.insertItem(0, '[' +
                        datetime.datetime.now().ctime() + ']  ' + text)
        item = self.ui.Status_Window.item(0) # get top item object
        self.ui.Status_Window.setCurrentItem(item)
        self.ui.Status_Window.update() # force an update with every line
    
        
    def setMainWindow(self, text=None):
        
        if text is not None:
            self.setWindowTitle("PyStartle [%s]" % (text))
        else:
            self.startleWidget = pg.GraphicsLayoutWidget()
            self.Expanded_Signal_Plot = pg.PlotItem()
            MPHL.labelUp(self.Expanded_Signal_Plot, 'time (ms)', 'Amp', 'Startle')
            self.Discrimination_Plot = pg.PlotItem()
            MPHL.labelUp(self.Discrimination_Plot, 'Trial', 'Discrim Score', 'Discrimination')
            self.startleWidget.addItem(self.Expanded_Signal_Plot)
            self.startleWidget.nextRow()
            self.startleWidget.addItem(self.Discrimination_Plot)
            self.ui.startleLayout.addWidget(self.startleWidget)
        
            self.signalsWidget = pg.GraphicsLayoutWidget()
            self.LSpectrum_Plot = pg.PlotItem()
            MPHL.labelUp(self.LSpectrum_Plot, 'F (kHz)', 'Amp', 'L Spectrum')
            self.signalsWidget.addItem(self.LSpectrum_Plot)
            self.RSpectrum_Plot = pg.PlotItem()
            MPHL.labelUp(self.RSpectrum_Plot, 'F (kHz)', 'Amp', 'R Spectrum')
            self.signalsWidget.addItem(self.RSpectrum_Plot)
            self.signalsWidget.nextRow()
            self.Response_Plot1 = pg.PlotItem()
            MPHL.labelUp(self.Response_Plot1, 'T (ms)', 'Ch1 Amp', 'Response Plot 1')
            self.signalsWidget.addItem(self.Response_Plot1)
            self.Response_Plot2 = pg.PlotItem()
            MPHL.labelUp(self.Response_Plot2, 'T (ms)', 'Ch2 Amp', 'Response Plot 2')
            self.signalsWidget.addItem(self.Response_Plot2)
            self.ui.signalsLayout.addWidget(self.signalsWidget)

            self.StimWidget = pg.GraphicsLayoutWidget()
            self.stimPlot = pg.PlotItem()
            self.specPlot = pg.PlotItem()
            MPHL.labelUp(self.stimPlot, 'Time (ms)', 'Amplitude', 'Stimulus')
            MPHL.labelUp(self.specPlot, 'F (kHz)', 'dB SPL', 'Spectrum')
            self.StimWidget.addItem(self.stimPlot)
            self.StimWidget.nextRow()
            self.StimWidget.addItem(self.specPlot)
            self.ui.StimulusLayout.addWidget(self.StimWidget)

            
# figure title for matplotlib window... 
    def putTitle(self, infotext):
        pa, fname = os.path.split(self.fileName)
        titletext = 'File: %s  R:[' % (fname)
        for i in self.reclist:
            titletext = titletext + '%d ' % (i)
        titletext = titletext + '] B:[ '
        for i in self.blocklist:
            titletext = titletext + '%d ' % (i)
        titletext = titletext + '] ' + infotext
        mpl.gcf().text(0.5, 0.95, titletext, horizontalalignment='center',
                  fontproperties=FontProperties(size=12))

################################################################################
# Read the gui data into our local parameters
################################################################################
    def readParameters(self):
        self.AutoSave = self.ui.AutoSave.isChecked()
# from the Levels and  Durations tab:
        self.CN_Level = self.ui.Condition_Level.value()
        self.CN_Dur = self.ui.Condition_Dur.value()
        self.CN_Var = self.ui.Condition_Var.value()
        self.PP_Level = self.ui.PrePulse_Level.value()
        self.PP_OffLevel = self.ui.PrePulse_Off_Level.value()
        self.PP_Dur = self.ui.PrePulse_Dur.value()
        self.PS_Dur = self.ui.PreStartle_Dur.value()
        self.ST_Dur = self.ui.Startle_Dur.value()
        self.ST_Level = self.ui.Startle_Level.value()
        self.StimEnable = self.ui.Stimulus_Enable.isChecked()
        self.WavePlot = self.ui.Waveform_PlotFlag.isChecked()
        self.ShowSpectrum = self.ui.OnlineSpectrum_Flag.isChecked()
        self.OnLineAnalysis = self.ui.OnlineAnalysis_Flag.isChecked()
# from the Waveforms tab:        
        self.PP_Freq = self.ui.PrePulse_Freq.value()
        self.PP_HP = self.ui.PrePulse_HP.value()
        self.PP_LP = self.ui.PrePulse_LP.value()
        self.PP_Mode = self.ui.Waveform_PrePulse.currentIndex()
        self.CN_Mode = self.ui.Waveform_Conditioning.currentIndex()
        self.PP_GapFlag = self.ui.PrePulse_GapFlag.isChecked()
        self.PP_Notch_F1 = self.ui.PrePulse_Notch_F1.value()
        self.PP_Notch_F2 = self.ui.PrePulse_Notch_F2.value()
        self.PP_MultiFreq = str(self.ui.PrePulse_MultiFreq.text())  
# from the Timing and Trials tab:
        self.ITI_Var = self.ui.PrePulse_ITI_Var.value()
        self.ITI = self.ui.PrePulse_ITI.value()
        self.Trials = int(self.ui.PrePulse_Trials.value())
        self.NHabTrials = int(self.ui.PrePulse_NHabTrials.value())
# from the analysis tab:
        self.readAnalysisTab()
        
    def readAnalysisTab(self): # we call this elsewhere, - define for convenience
        self.Analysis_Start = self.ui.Analysis_Start.value()
        self.Analysis_Duration = self.ui.Analysis_Duration.value()
        self.Analysis_HPF = self.ui.Analysis_HPF.value()
        self.Analysis_LPF = self.ui.Analysis_LPF.value()
        self.Analysis_Baseline = self.ui.Analysis_Baseline.value()
        self.Analysis_BaselineStd = self.ui.Analysis_BaselineStd.value()
        self.Analysis_WaveformStd = self.ui.Analysis_WaveformStd.value()
        self.Analysis_WaveformMinStd = self.ui.Analysis_WaveformMinStd.value()
        
    def ToneTest(self):
        self.readParameters()
        w = Sounds.StimulusMaker(mode='tone', freq = (self.PP_Freq, 0),
                               duration = self.PP_Dur, samplefreq = 44100)
        self.plotSignal(np.linspace(0., self.PP_Dur, len(w)), w, w, plotResponse=False)

    def NoiseTest(self):
        self.readParameters()
        w = Sounds.StimulusMaker(mode = 'bpnoise', freq=(self.PP_HP, self.PP_LP),
                               duration=self.PP_Dur, samplefreq = 44100)
        self.plotSignal(np.linspace(0., self.PP_Dur, len(w)), w, w, plotResponse=False)
        
################################################################################
#
#   PrePulseRun controls the stimulus presentation and timing.
#   It is the main event loop during stimulation/acquisition.
#
# note : we use QTimer for the timing. One instance is generated with the
# main init routine above. We then start this and run it as a separate thread
# Allows gui interaction during data acquisition/stimulation and ability to
# stop the presentation cleanly.
################################################################################

    def PrePulseStart(self):
        if self.PPGo:
            print "already running"
            return;
        self.Status ("Starting Run")
#
# open and build the file
#
        dt = time.strftime('%Y%m%d%H%M')
        self.fn = dt + "_Startle.txt"
        self.readParameters() # get the parameters for stimulation
        self.TrialCounter = 0
        self.SpecMax = 0
        self.totalTrials = int(self.Trials+self.NHabTrials)
        itil = self.ITI + self.ITI_Var*(np.random.rand(1, self.totalTrials)-0.5)
        self.ITI_List = itil.reshape(np.max(itil.shape))   # CHECK THIS
        stimd = self.CN_Dur + self.CN_Var*(np.random.rand(1,self.totalTrials)-0.5)
        self.Dur_List = stimd.reshape(np.max(stimd.shape))
        self.Gap_List = self.totalTrials*[False]
        trialslist = int(self.Trials/2)*[False, True]
        s = sample(trialslist, int(self.Trials))
        self.Gap_List[int(self.NHabTrials):] = s
        if self.AutoSave:
            self.writeDataFileHeader(self.fn) # wait to write header until we have all the values.
        self.Gap_StartleMagnitude = np.zeros(self.Trials)
        self.Gap_Counter = 0
        self.noGap_StartleMagnitude = np.zeros(self.Trials)
        self.noGap_Counter = 0
        self.PPGo = True
        if self.debugFlag:
            print "PrePulseStart: timer starting"
        self.TrialTimer.setSingleShot(True)
        self.TrialTimer.start(10) # start right away

# catch the stop button press 
    def PrePulseStop(self):
        if self.debugFlag:
            print "PrePulseStop: hit detected"
        Sounds.setAttens() # attenuators down
        # Sounds.HwOff() # turn hardware off
        self.PPGo=False # signal the prepulse while loop that  we are stopping
        self.statusBar().showMessage("Stimulus/Acquisition Events stopped")

# callback routine to stop timer when thread times out.
    def NextTrial(self):
        if self.debugFlag:
            print "NextTrial: entering"
        self.TrialTimer.stop()
        if self.TrialCounter <= self.Trials and self.PPGo:
            self.statusBar().showMessage("Rep: %d of %d, ITI=%7.2f" % (self.TrialCounter+1,
                                                            self.totalTrials,
                                                            self.ITI_List[self.TrialCounter]))
            DoneTime = self.ITI_List[self.TrialCounter] # get this before we start stimulus so stim time is included
            self.TrialTimer.start(int(1000.0*DoneTime))
            self.Stim_Dur = self.Dur_List[self.TrialCounter] # randomize the durations a bit too
            self.runOnePP()
            if self.WavePlot == True:
                self.plotSignal(np.linspace(0., self.Stim_Dur, len(self.wave_outL)), self.wave_outL, self.wave_outR, self.out_sampleFreq)
            if self.AutoSave:
                self.AppendData(self.fn)
            self.TrialCounter = self.TrialCounter + 1
        else:
            self.PPGo = False
            self.statusBar().showMessage("Test Complete")
        if self.debugFlag:
            print "NextTrial: exiting"

################################################################################
# runOnePP - "run one prepulse" trial.
# Generate one stimulus set based on the choice. Builds both channels.
# Presents the stimuli if the flag is set.
################################################################################
# the modes parse as follows (same modes apply for CN/PS, and for PP)
# 0 is silence
# 1 is tone
# 2 is bandpass noise
# 3 is notch noise (not implemented yet)
# 4 is multi tones (not implemented yet)
# 5 is AM tones (not implemented yet)
# 6 is AM Noise (not implemented yet)
# 
# The conditioning (CN) and the prepulse (PP) can be any of the above
# the pre-startle (post prepulse) is always the same as the conditioning.
# The conditioning stimulus always runs the whole duration (including through the end of the startle)
# If the conditioning stimulus is not the same as the prepulse, then the conditiioning
# will be interrupted by a gap during the prepulse period, and the prepulse will be calculated,
# shaped, and added during the prepulse period.
#
    def runOnePP(self):
        if self.debugFlag:
            print "runOnePP: Entering"
        (self.hardware, self.out_sampleFreq, self.in_sampleFreq) = Sounds.getHardware()
        if self.CN_Mode == 0:
            cnmode = 'silence'
            cnfreq = (self.PP_Freq, 0) # anything will do
        if self.CN_Mode == 1 or self.CN_Mode == 4 or self.CN_Mode == 5:
            cnmode = 'tone'
            cnfreq = (self.PP_Freq, 0)
        if self.CN_Mode == 2 or self.CN_Mode == 6:
            cnmode = 'bpnoise'
            cnfreq = (self.PP_HP, self.PP_LP)
        if self.CN_Mode == 3:
            cnmode = 'notchnoise' # Note: notch is embedded into a bandpass noise
            cnfreq = (self.PP_HP, self.PP_LP, self.PP_Notch_F1, self.PP_Notch_F2)
        # generate the conditioning stimulus and the post-prepulse stimulus
        self.wave_outL = Sounds.StimulusMaker(mode = cnmode, duration = (self.Stim_Dur+self.PP_Dur+self.PS_Dur+self.ST_Dur),
                                  freq = cnfreq, samplefreq = self.out_sampleFreq, delay=0, level = self.CN_Level)
        # now tailor the conditioning stimulus
        # this is regulated by the current Gap_List value
        w_pp = [] # default with no prepulse
        if self.Gap_List[self.TrialCounter]: # only make a prepulse if it is set
            if self.PP_Mode == 0 or self.PP_GapFlag: # insert a gap
                self.wave_outL = Sounds.insertGap(self.wave_outL, delay = self.Stim_Dur,
                                  duration = self.PP_Dur, samplefreq = self.out_sampleFreq) # inserts the gap
            if self.PP_Mode == 1 or self.PP_Mode ==4 or self.PP_Mode == 5: # now insert a tone
                w_pp = Sounds.StimulusMaker(mode = 'tone', duration = self.PP_Dur, freq = (self.PP_Freq, 0),
                                          delay=self.Stim_Dur, samplefreq = self.out_sampleFreq, level = self.PP_Level)
                w_pp =np.append(w_pp, np.zeros(len(self.wave_outL)-len(w_pp))) # pad
            if self.PP_Mode == 2 or self.PP_Mode == 6:  # 2 is bandpass noise
                w_pp = Sounds.StimulusMaker(mode = 'bpnoise', duration = self.PP_Dur, freq = (self.PP_HP, self.PP_LP),
                                    delay=self.Stim_Dur, samplefreq = self.out_sampleFreq, level = self.PP_Level)
                w_pp =np.append(w_pp, np.zeros(len(self.wave_outL)-len(w_pp))) # pad  
            if self.PP_Mode == 3: # 3 Notched noise
                w_pp = Sounds.StimulusMaker(mode = 'notchnoise', duration = self.Stim_Dur,
                                    freq = (self.PP_HP, self.PP_LP, self.Notch_F1, self.Notch_F2),
                                    samplefreq = self.out_sampleFreq, delay=self.Stim_Dur,
                                    level = self.PP_Level)
                w_pp =np.append(w_pp, np.zeros(len(self.wave_outL)-len(w_pp))) # pad 
        if len(w_pp) > 0:
            self.wave_outL = self.wave_outL + w_pp
        # generate the startle sound. Note that it overlaps the end of the conditioning sound...
        self.wave_outR = Sounds.StimulusMaker(mode = 'bpnoise', delay = (self.Stim_Dur+self.PP_Dur+self.PS_Dur),
                                       duration = self.ST_Dur, samplefreq=self.out_sampleFreq,
                                       freq = (1000.0, 32000.0), level = self.ST_Level,
                                       channel = 1)
        lenL = len(self.wave_outL)
        lenR = len(self.wave_outR)
        if lenR > lenL:
            self.wave_outL =np.append(self.wave_outL, np.zeros(lenR-lenL))
        if lenL > lenR:
            self.wave_outR =np.append(self.wave_outR, np.zeros(lenL-lenR))
        if self.debugFlag:
            print "runOnePP: present stimulus"
        if self.StimEnable == True:
            Sounds.playSound(self.wave_outL, self.wave_outR, self.out_sampleFreq,
                             self.PostDuration)
            (self.ch1, self.ch2) = Sounds.retrieveInputs()
       # print 'ch1 len: ', len(self.ch1)
        if self.debugFlag:
            print "runOnePP: exiting"

################################################################################
#
# plot the signal and it's power spectrum
#     
    def plotSignal(self, X, wL, wR, samplefreq=44100, plotResponse = True):
        npts = len(wL)
        t = np.linspace(0.,npts/float(samplefreq), npts)
        skip = int(npts/self.maxptsplot)
        if skip < 1:
            skip = 1

        self.stimPlot.plot(t[0::skip], wL[0::skip], pen=pg.mkPen('y'), clear=True)
        if len(wR) == len(wL):
            self.stimPlot.plot(t[0::skip], wR[0::skip], pen=pg.mkPen('c'))
        else:
            nptsL = len(wL)
            tL = np.linspace(0.,nptsL/float(samplefreq), npts)
            skipL = int(nptsL/self.maxptsplot)
            if skipL < 1:
                skipL = 1
            self.stimPlot.plot(tL[0::skipL], wR[0::skipL], pen=pg.mkPen('c'))
            
        # MPlots.PlotLine(self.ui.qwt_Stimulus_Plot, t[0::skip], wL[0::skip], color = 'y')
        # MPlots.PlotLine(self.ui.qwt_Stimulus_Plot, t[0::skip], wR[0::skip], color = 'c')
        # spectrum of signal
        if self.ShowSpectrum:
            (spectrum, freqAzero) = Utils.pSpectrum(wR, samplefreq)
            s = self.specPlot.plot(freqAzero[1:]/1000., spectrum[1:], pen=pg.mkPen('b'))
            s.setLogMode(True, False)  # not sure about using x, y keywords; throws error
            self.specPlot.setXRange(0, 25., padding=0)
        if not plotResponse:
            return
#        ds = self.ch1.shape
        self.response_tb = np.arange(0,len(self.ch1))/self.in_sampleFreq
        self.Response_Plot1.plot(self.response_tb[0::skip],
            1000.0*self.ch1[0::skip], pen=pg.mkPen('g'))
        # MPlots.PlotReset(self.ui.qwt_Response_Plot2, textName='Response_Plot2')
        self.Response_Plot2.plot(self.response_tb[0::skip], 1000.0*self.ch2[0::skip], pen=pg.mkPen('r'))
        if self.ShowSpectrum:
            (Lspectrum, Lfreqs) = Utils.pSpectrum(1000.0*self.ch2, samplefreq/1000.) # rate  (1/ms) is converted to Hz
#            maxFreq = 0.5*samplefreq
            self.LSpectrum_Plot.plot(Lfreqs[1:], 1000.0*Lspectrum[1:], pen=pg.mkPen('y'))
            self.LSpectrum_Plot.setLogMode(True, False)
            self.LSpectrum_Plot.setXRange(0.01, 22.0)

        tdelay = self.Stim_Dur + self.PP_Dur + self.PS_Dur
        
        # analyze the response signal
        dprime, ratio = self.Response_Analysis(timebase= self.response_tb, signal = self.ch1,
                               samplefreq = samplefreq, delay=tdelay,
                               SpecPlot = self.RSpectrum_Plot,
                               SignalPlot = self.Expanded_Signal_Plot,
                               ResponsePlot = self.Discrimination_Plot,
                               ntrials = self.Trials,
                               trialcounter = self.TrialCounter,
                               gaplist = self.Gap_List)

        if self.TrialCounter > 0:
            self.ui.Discrimination_Score_Label.setText("Rd: %7.3f" % (dprime))
            self.ui.Rd_Dial.setValue(int(100*dprime))
        
    def getSelectionIndices(self, x, xstart, xend):
        astart = np.where(x >= xstart)
        aend = np.where (x <= xend)
        s0 = set(np.transpose(astart).flat)
        s1 = set(np.transpose(aend).flat)
        xpts = list(s1.intersection(s0))
        return (xpts)
    
    def Write_Data(self):
        self.writeDataFileHeader('test.dat')
        
    def writeDataFileHeader(self, filename):
        # make a dictionary of all the parameters
        filedict = {}
        filedict_gap = {}
        filedict['CN_Level'] =  self.CN_Level
        filedict['CN_Dur'] = self.CN_Dur
        filedict['CN_Var'] = self.CN_Var
        filedict['PP_Level'] = self.PP_Level
        filedict['PP_OffLevel'] = self.PP_OffLevel 
        filedict['PP_Dur'] = self.PP_Dur
        filedict['PS_Dur'] = self.PS_Dur 
        filedict['ST_Dur'] = self.ST_Dur 
        filedict['ST_Level'] = self.ST_Level
        filedict['StimEnable'] = self.StimEnable
        filedict['WavePlot'] = self.WavePlot
        
        filedict_gap['GapList'] = self.Gap_List # save the sequencing information

# from the Waveforms tab:        
        filedict['PP_Freq'] = self.PP_Freq 
        filedict['PP_HP'] = self.PP_HP
        filedict['PP_LP'] = self.PP_LP
        filedict['PP_Mode'] = self.PP_Mode
        filedict['CN_Mode'] = self.CN_Mode
        filedict['PP_Notch_F1'] = self.PP_Notch_F1
        filedict['PP_Notch_F2'] = self.PP_Notch_F2
        filedict['PP_MultiFreq'] = self.PP_MultiFreq
        filedict['PP_GapFlag'] = self.PP_GapFlag
# from the Timing and Trials tab:
        filedict['ITI_Var'] = self.ITI_Var 
        filedict['ITI'] = self.ITI
        filedict['Trials'] = self.Trials
        filedict['NHabTrials'] = self.NHabTrials
# analysis parameters        
        filedict['Analysis_Start'] = self.Analysis_Start 
        filedict['Analysis_Duration'] = self.Analysis_Duration
        filedict['Analysis_HPF'] = self.Analysis_HPF
        filedict['Analysis_LPF'] = self.Analysis_LPF          
        print "Writing File: %s" % (filename)
        hdat = open(filename, 'w')
        hdat.write("%s \n" % (filedict))
        hdat.write("%s \n" % (filedict_gap)) # write in separate lines
        hdat.close()
        
    def AppendData(self, filename):
        hdat = open(filename, 'a')
        datainfo = {}
        datainfo['Points'] = len(self.response_tb)
        datainfo['inSampleFreq'] = self.in_sampleFreq
        datainfo['outSampleFreq'] = self.out_sampleFreq
        datainfo['GapMode'] = self.Gap_List[self.TrialCounter]
        datainfo['ITI'] = self.ITI_List[self.TrialCounter]
        datainfo['CNDur'] = self.Dur_List[self.TrialCounter]
        hdat.write("%s \n" % (datainfo))
        for i in range(0, len(self.response_tb)):
            hdat.write("%f %f %f\n" % (self.response_tb[i], 1000*self.ch1[i],
                                       1000*self.ch2[i]))
        hdat.close()

    def Analysis_Test(self):
        self.readParameters()
        self.readAnalysisTab()
        npts = 10000
        samplefreq = 24410.0
        rate = 1000.0/samplefreq
        signal = np.random.normal(0, 1, npts)
        (Rspectrum, Rfreqs) = Utils.pSpectrum(signal, float(rate/1000.0)) # rate  (1/ms) is converted to Hz
        fa = Utils.SignalFilter(signal, self.Analysis_LPF, self.Analysis_HPF, samplefreq)
        (fRspectrum, fRfreqs) = Utils.pSpectrum(fa, float(rate/1000.0)) # rate  (1/ms) is converted to Hz
        mpl.plot(Rfreqs, Rspectrum, pen=pg.mkPen('w'))
        mpl.plot(fRfreqs, fRspectrum, pen=pg.mkPen('r'))
        mpl.show()
        
################################################################################
#   Analysis routines
#
################################################################################
    def Analysis_Read(self, filename=None):
        
        print 'filename: ', filename
        self.a_t = [] 
        self.a_ch1 = [] 
        self.a_ch2 = [] 
        self.gapmode = []
        self.delaylist = []
        self.ITI_List = []
        
        self.readParameters() # to be sure we have "showspectrum"
        self.readAnalysisTab()
        if filename == None or not filename:
            fd = QtGui.QFileDialog(self)
            self.inFileName = str(fd.getOpenFileName(self, "Get input file", "",
                                                     "data files (*.txt)"))
        else:
            self.inFileName = filename
        print self.inFileName
        try:
            hstat = open(self.inFileName,"r")
            (p, f)  = os.path.split(self.inFileName)
            self.setMainWindow(text=f)
        except IOError:
            self.Status( "%s not found" % (self.inFileName))
            return
        if self.inFileName not in self.recentFiles:
            self.recentFiles.appendleft(self.inFileName)
        lineno = 0
        state = 0 # initial state
                    # states:
                    # 0 - nothing read
                    # 1 = first line read
                    # 2 = record "header" line read
                    # 3 = reading data
        parse =  re.compile("(^([\-0-9.]*) ([\-0-9.]*) ([\-0-9.]*))")
        reccount = 1

        header_linecount = 0
        lineno = 0
        for line in hstat:
            lineno = lineno + 1
            if state == 0:
                if header_linecount == 0:  # first line has parameters for stimulus etc. 
                    self.statusBar().showMessage("Reading Header" )   
                    self.paramdict = Utils.long_Eval(line)
                    header_linecount = 1
                    continue
                if header_linecount == 1:  # second header line is a dict with gap list status falgs
                    self.paramdict_gap = Utils.long_Eval(line)
                    state = 1
                    header_linecount = 0
                continue
            if state == 1:  # third line begins the data - stimulus parameters are here, so extract
                self.headerdict =  Utils.long_Eval(line)
                self.npts = self.headerdict['Points']
                self.samplefreq = 1.0/float(self.headerdict['SampleRate'])
                if self.headerdict.has_key('GapMode'): # build gap mode array
                    self.gapmode.append(self.headerdict['GapMode'])
                else:
                    self.gapmode.append(False)
                if self.headerdict.has_key('CNDur'): # build duration  (delay to startle) array
                    self.delaylist.append(self.headerdict['CNDur'] +
                                          self.paramdict['PP_Dur'] + self.paramdict['PS_Dur'])
                if self.headerdict.has_key('ITI'): # build an ITI list.
                    self.ITI_List.append(self.headerdict['ITI'])
                reccount += 1
                self.statusBar().showMessage("Reading Trial %d" % (reccount) )   
                state = 2
                i = 0
                t = np.zeros(self.npts)
                ch1 = np.zeros(self.npts)
                ch2 = np.zeros(self.npts)
                continue
            if state == 2:  # waveforms
                    mo = parse.search(line)
                    t[i] = float(mo.group(2))
                    ch1[i] = float(mo.group(3))
                    ch2[i] = float(mo.group(4))
                    i = i + 1
                    if i >= self.npts:
                        self.a_t.append(np.array(t))
                        # filter the data as it comes in
                        self.a_ch1.append(np.array(ch1))
                        self.a_ch2.append(np.array(ch2))
                        state = 1 # reset the state to read the next points list
        hstat.close()
        self.statusBar().showMessage("Done Reading")   
        if self.loadAnnotation(): # see if there is an associated annotation file.
            self.updateAnnotateTime()
        self.Analyze_Data()

    def Analysis_ReRead(self):
        if self.recentFiles is not []:
            self.Analysis_Read(filename=self.recentFiles[0]) # get the top most file
        
    def Analyze_Data(self):
        ds = len(self.a_t)
        if ds == 0:
            print "Analyze_Data: No data in file."
            return
        self.setGraphTab(3)
        self.readParameters() # to be sure we have "showspectrum"
        self.readAnalysisTab()
        self.getRejectTrials()
        rejectwindow = self.Analysis_Baseline
        srate = 1000.0/float(self.headerdict['SampleRate']) # sample rate is in msec/point.
        sfreq = 1.0/srate
        # note: must clip to the part of the dataset that we need - e.g., the post-startle section        
        stdur = int(self.Analysis_Duration/srate) #  points after startle
        # prepare to plot all traces
        rows = int(np.sqrt(ds))
        cols = int(ds/rows)
        if rows*cols < ds:
            cols += 1
        
        # first filter the data set (only the response channel, not the microphonse)
        self.fa_ch1 = [] # list of channel data (elements are numpy arrays)
        for k in range(0, ds):
            fa = Utils.SignalFilter(self.a_ch1[k], self.Analysis_LPF, self.Analysis_HPF,
                 float(self.headerdict['SampleRate']))
            self.fa_ch1.append((fa).astype('float32'))
        
        sum_nogap = np.zeros(stdur)
        sum_gap = np.zeros(stdur)
        N_gap = 0
        N_nogap = 0
        tb = np.arange(0,(self.Analysis_Duration/srate),srate)*1000.0 # in msec.
        NTrials = int(self.paramdict['Trials'])
        self.Startle_Analyze(trialcounter=0, ntrials=NTrials) # with trial counter set to 0, initializes analysis
        self.SpecMax = 0
        bli = np.array([])
        sigi = np.array([])
        for i in range(0, ds):
            thislen = self.a_t[i].shape
            if thislen[0] <= 0:
                break
            ststart = int(self.delaylist[i]/srate) # delay is in msec
            stend = ststart+stdur
            if i < int(self.paramdict['NHabTrials']):
                continue
            rjend = ststart + int(rejectwindow/srate)
            rpts = range(ststart, rjend)
            if rjend > self.fa_ch1[i].shape[0]: # check for truncated records
                break
            bli = np.append(bli, np.std(self.fa_ch1[i][rpts]))
            sigi = np.append(sigi, np.std(self.fa_ch1[i][ststart:stend]))
        avgbl = np.mean(bli)
        avgsig = np.mean(sigi)
        print "\nAverage BL: %f, Average sig: %f on %d trials" % (avgbl, avgsig, len(bli))

        ds = i # only include plots that are complete.
        k = 0
        plt = [[]]*(ds)
        # for i in range(0, rows):
        #     for j in range(0, cols):
        #         if k >= ds:
        #             continue
        #         if self.gapmode[k]:
        #             pline = 'r' # with prepulse, red
        #         else:
        #             pline = 'c' # with nogap, cyan
        #         if k < self.paramdict['NHabTrials']: # force to grey
        #             pline = 'darkgray'
        #         ststart = int(self.delaylist[k]/srate) # delay is in msec
        #         stend = ststart+stdur
        #         if stend > shape(self.a_t[k])[0]: # Handle truncated data sets.
        #             break
        #         k = k + 1
        
        nSuccessfulTrials = 0
        for i in range(int(self.paramdict['NHabTrials']), ds):  # start after habituation trias
            if self.a_t[i].shape[0] == 0: # no data ? 
                break
            ststart = int(self.delaylist[i]/srate) # delay is in msec
            stend = ststart+stdur
            rjend = ststart + int(rejectwindow/srate)
            if rjend > self.a_t[i].shape[0]:
                break # protect against truncated record by stopping analysis
            rpts = range(ststart, rjend)
            #print "Analyze: rpts = %d-%d" % (min(rpts), max(rpts))
            bl = np.std(self.fa_ch1[i][rpts])
            sig = np.std(self.fa_ch1[i][ststart:stend])
            if i in self.RejectedTrials:
                print "Rejecting Trial: %d  based on Behavior/Orientation/Location" % (i)
                self.reColor(plt[i], self.gapmode[i])
                continue
            if bl > self.Analysis_BaselineStd * avgbl:
                print "Rejecting Trial: %d  baseline stdev is too big: %f" % (i, bl)
                self.reColor(plt[i], self.gapmode[i])
                continue
            if sig > self.Analysis_WaveformStd * avgsig:
                print "Rejecting Trial: %d  signal stdev is too big: %f" % (i, sig)
                self.reColor(plt[i], self.gapmode[i])
                continue
            if sig < self.Analysis_WaveformMinStd * avgsig:
                print "Rejecting Trial: %d  signal stdev is too SMALL: %f" % (i, sig)
                self.reColor(plt[i], self.gapmode[i])
                continue
            # trial by trial - updates dprime
            nSuccessfulTrials += 1
            dprime, ratio = self.Response_Analysis(signal=self.fa_ch1[i][ststart:stend],
                                  samplefreq=sfreq,
                                  ResponsePlot=None, # self.Discrimination_Plot,
                                  SignalPlot = self.Expanded_Signal_Plot,
                                  SpecPlot = self.RSpectrum_Plot,
                                  trialcounter=i,
                                  ntrials=NTrials,
                                  gaplist = self.gapmode, okTrials=nSuccessfulTrials)
            if self.gapmode[i]:
                try:
                    sum_gap = sum_gap + np.array(self.fa_ch1[i][ststart:stend])
                    N_gap += 1
                except:
                    pass
            else:
                try:
                    sum_nogap = sum_nogap + np.array(self.fa_ch1[i][ststart:stend])
                    N_nogap += 1
                except:
                    pass
        # final signal plots
        self.sum_gap = 1000.0*sum_gap/float(N_gap)
        self.sum_nogap = 1000.0*sum_nogap/float(N_nogap)
        self.plotWaveform(self.Expanded_Signal_Plot, tb, ststart, stend)
        self.plotResponse(self.Discrimination_Plot)

    def plotWaveform(self, signalPlot, tb, ststart, stend):
        t_startle = tb[0:(stend - ststart)]/1000.0
        tbase = np.arange(0, max(t_startle))
        zline = 0.0 * tbase
        if self.Signal_PlotLegend is not None:
            self.Signal_PlotLegend.scene().removeItem(self.Signal_PlotLegend)
        signalPlot.plot(tbase, zline, pg.mkPen((75, 75, 75, 128)), clear=True)
        self.Signal_PlotLegend = signalPlot.addLegend()
        signalPlot.plot(t_startle, self.sum_gap, pen=pg.mkPen('r'), name='Gap')
        signalPlot.plot(t_startle, self.sum_nogap, pen=pg.mkPen('w'), name='No_Gap')
        self.setGraphTab(0)

    def plotResponse(self, ResponsePlot):
        if self.Response_PlotLegend is not None:
            self.Response_PlotLegend.scene().removeItem(self.Response_PlotLegend) # remove the old legend
        self.Response_PlotLegend = ResponsePlot.addLegend()  # add a new one
        ResponsePlot.plot(self.Gap_StartleMagnitude, pen=pg.mkPen('r'),
                                   symbol = 'o', name='Gap', clear=True)
        ResponsePlot.plot(self.noGap_StartleMagnitude, pen=pg.mkPen('w'),
                                   symbol = '+', name='No Gap')
    def reColor(self, plt, mode):
        if mode:
          plt.setPen(pg.mkPen((128, 0, 0, 256)))
        else:
          plt.setPen(pg.mkPen((0, 128, 128, 256)))


    def Response_Analysis(self, timebase=None, signal=None,
                               samplefreq=44100, delay=0, SpecPlot=None,
                               SignalPlot=None, ResponsePlot=None,
                               trialcounter=0,
                               ntrials=1,
                               gaplist=None,
                               rejectwindow = 10,
                               okTrials=0):
        """
        response analysis for a single trace...
        """
                               
        if self.debugFlag:
            print "Response_Analysis: entering"

        #print 'show spectrum, specplot, signalplot, responsePlot: ', self.ShowSpectrum, SpecPlot, SignalPlot, ResponsePlot
        if self.ShowSpectrum and SpecPlot is not None:
            if self.debugFlag:
                print "signal pts: %d min: %f max: %f" % (len(signal), min(signal), max(signal))
            (Rspectrum, Rfreqs) = Utils.pSpectrum(1000.0*signal, samplefreq) # rate  (1/ms) is converted to Hz
            if max(Rspectrum) > self.SpecMax:
                self.SpecMax = max(Rspectrum)
            maxFreq = 1000.0
            SpecPlot.plot(Rfreqs[1:], 1000.0*Rspectrum[1:], pen=pg.mkPen('y'), clear=True)
            SpecPlot.setXRange(10.0, maxFreq)

        if timebase is None:
            timebase = np.arange(0, len(signal))/samplefreq
        ana_windowstart = (delay + self.Analysis_Start)
        ana_windowend = (delay + self.Analysis_End)
        apts = range(0, len(signal))
        t0 = timebase[apts[0]] - self.Analysis_Start/1000.0
        if SignalPlot is not None:
            if gaplist[trialcounter]:
                pline = pg.mkPen('r') # with prepulse, red
            else:
                pline = pg.mkPen('g')  # without - green 
            SignalPlot.plot(timebase[apts]-t0, 1000.0*signal[apts], pen=pline, clear=True)
        dprime, ratio = self.Startle_Analyze(timebase=timebase, signal=signal,
                                      startdelay=0.0,
                                      rejectwindow = 10,
                                      trialcounter=trialcounter,
                                      ntrials=ntrials,
                                      gaplist=gaplist)
        if ResponsePlot is not None:
            self.plotResponse(ResponsePlot)

        self.ui.Discrimination_Score_Label.setText(('d \' = %9.3f' % dprime))
        return dprime, ratio

    def Startle_Analyze(self, timebase=None,
                        signal=None,
                        startdelay=0,
                        rejectwindow = 10,
                        trialcounter=0,
                        ntrials=1,
                        gaplist=None):
        dprime = 0.0
        ratio = 0.0
        if trialcounter == 0: # initialize the trials.
            self.Gap_mean = 0.0
            self.Gap_std = 0.0
            self.noGap_mean = 0.0
            self.noGap_std = 0.0
            self.Gap_Counter = 0
            self.Gap_StartleMagnitude = np.array([])
            self.noGap_StartleMagnitude = np.array([])
            self.noGap_Counter = 0
            self.SpecMax = 0.0

            return dprime, ratio

        self.readAnalysisTab()
        apts = self.getSelectionIndices(timebase, startdelay/1000.0,
                                        (startdelay+self.Analysis_End)/1000.0)
        apts = range(0, len(timebase))
        rpts = self.getSelectionIndices(timebase, 0, rejectwindow)
        if trialcounter > 0 : # once we are past the habituation phase
            if gaplist[trialcounter]:  # for trials with gaps
                try:
                    self.Gap_StartleMagnitude =np.append(self.Gap_StartleMagnitude,
                         np.sqrt(np.mean(signal[apts]**2.0)))
                    self.Gap_mean = np.mean(self.Gap_StartleMagnitude)
                    if self.Gap_Counter >= 1 :
                        self.Gap_std = np.std(self.Gap_StartleMagnitude)
                    self.Gap_Counter = self.Gap_Counter + 1
                except:
                    print 'Startle_Analyze: error in gaplist True, trial %d' % (trialcounter)
            else:
                try:
                    self.noGap_StartleMagnitude =np.append(self.noGap_StartleMagnitude,
                         np.sqrt(np.mean(signal[apts]**2.0)))
                    self.noGap_mean = np.mean(self.noGap_StartleMagnitude)
                    if self.noGap_Counter >= 1 :
                        self.noGap_std = np.std(self.noGap_StartleMagnitude)
                    self.noGap_Counter = self.noGap_Counter + 1
                except:
                    print 'Startle_Analyze: error in gaplist False, trial %d' % (trialcounter)
# now calculate the d'
            if self.noGap_std != 0 and self.Gap_std != 0 :
                dprime = (self.noGap_mean-self.Gap_mean)/(np.sqrt(self.noGap_std**2 + self.Gap_std**2))
                ratio = self.Gap_mean/self.noGap_mean
            #print "Startle_Analyze: gap: %f +/- %f,, nogap: %f +/- %f  :::: dprime = %f" % (
            #       self.Gap_mean, self.Gap_std, self.noGap_mean, self.noGap_std, dprime)
        
        return dprime, ratio

    def Analysis_lineEdit(self):
        txt = self.ui.Analysis_lineEdit.text() # get the text
        if len(txt) > 0:
            self.ui.Analysis_lineEdit.setText('') # then clear it immediately
            print "Line is: %s" % str(txt)
        
################################################################################
#
# Read the parameter initialization file. This is a simple text file with defined fields
# and numeric arguments. 
# The elements of the file can be in any order.
# unrecognized tags are ignored at your peril.
################################################################################

    def readini(self, filename= None):    
        if filename == None:
            fd = QtGui.QFileDialog(self)
            self.fileName = str(fd.getOpenFileName(self, "Get Parameter File", "",
                                                   "Parameter Files (*.ini)"))
        else:
            self.fileName = filename

        config = ConfigParser.RawConfigParser()
        config.read(self.fileName)
        (p, f)  = os.path.split(self.fileName)

        self.CurrentTab = config.getint('State', 'currenttab')
        self.setCurrentTab(self.CurrentTab)
        self.fileDate = config.get('State', 'Date')
        self.setMainWindow(text = f + " " + self.fileDate)
        self.StimEnable  = config.getboolean('Flags', 'stimEnable')
        self.ui.Stimulus_Enable.setChecked(self.StimEnable)
        self.WavePlot = config.getboolean('Flags', 'WavePlot')
        self.ui.Waveform_PlotFlag.setChecked(self.WavePlot)
        self.ShowSpectrum = config.getboolean('Flags', 'ShowSpectrum')
        self.ui.OnlineSpectrum_Flag.setChecked(self.ShowSpectrum)
        
        self.CN_Level = config.getfloat('Conditioning', 'CN_Level')
        self.ui.Condition_Level.setValue(self.CN_Level)
        self.CN_Dur = config.getfloat('Conditioning', 'CN_Dur')
        self.ui.Condition_Dur.setValue(self.CN_Dur)
        self.CN_Var = config.getfloat('Conditioning', 'CN_Var')
        self.ui.Condition_Var.setValue(self.CN_Var)
        self.CN_Mode = config.getint('Conditioning', 'CN_Mode')
        self.ui.Waveform_Conditioning.setCurrentIndex(self.CN_Mode)

        self.PP_Level = config.getfloat('Prepulse', 'PP_Level')
        self.ui.PrePulse_Level.setValue(self.PP_Level)
        self.PP_OffLevel = config.getfloat('Prepulse', 'PP_OffLevel')
        self.ui.PrePulse_Off_Level.setValue(self.PP_OffLevel)
        self.PP_Dur = config.getfloat('Prepulse', 'PP_Dur')
        self.ui.PrePulse_Dur.setValue(self.PP_Dur)
        self.PP_Mode = config.getint('Prepulse', 'PP_Mode')
        self.ui.Waveform_PrePulse.setCurrentIndex(self.PP_Mode)
        self.PP_Freq = config.getfloat('Prepulse', 'PP_Freq')
        self.ui.PrePulse_Freq.setValue(self.PP_Freq)
        self.PP_HP = config.getfloat('Prepulse', 'PP_HP')
        self.ui.PrePulse_HP.setValue(self.PP_HP)
        self.PP_LP = config.getfloat('Prepulse', 'PP_LP')
        self.ui.PrePulse_LP.setValue(self.PP_LP)
        self.PP_Notch_F1 = config.getfloat('Prepulse', 'PP_Notch_F1')
        self.ui.PrePulse_Notch_F1.setValue(self.PP_Notch_F1)
        self.PP_Notch_F2 = config.getfloat('Prepulse', 'PP_Notch_F2')
        self.ui.PrePulse_Notch_F2.setValue(self.PP_Notch_F2)
        self.PP_MultiFreq = config.get('Prepulse', 'PP_MultiFreq')
        self.ui.PrePulse_MultiFreq.setText(self.PP_MultiFreq)
        self.PP_GapFlag = config.getboolean('Prepulse', 'PP_GapFlag')
        self.ui.PrePulse_GapFlag.setChecked(self.PP_GapFlag)
        
        self.ITI = config.getfloat('Trials', 'ITI')        
        self.ui.PrePulse_ITI.setValue(self.ITI)
        self.ITI_Var = config.getfloat('Trials', 'Var')
        self.ui.PrePulse_ITI_Var.setValue(self.ITI_Var)
        self.Trials = int(config.getint('Trials', 'NTrials'))
        self.ui.PrePulse_Trials.setValue(self.Trials)
        self.NHabTrials = int(config.getint('Trials', 'NHabTrials'))
        self.ui.PrePulse_NHabTrials.setValue(self.NHabTrials)
        
        self.ST_Dur = config.getfloat('Startle', 'Dur')
        self.ui.Startle_Dur.setValue(self.ST_Dur)
        self.ST_Level = config.getfloat('Startle', 'Level')
        self.ui.Startle_Level.setValue(self.ST_Level)
        
# write a file that can be read by readini above. 
            
    def writeini(self, filename=None):
                # now save the program status... ;) to reload later
        if filename == None:
            fd = QtGui.QFileDialog(self)
            self.fileName = str(fd.getSaveFileName())
        else:
            self.fileName = filename  
        self.readParameters() # get the latest from the gui
        self.fileDate = time.strftime("%d-%b-%Y")
        
        config = ConfigParser.RawConfigParser()
        config.add_section('State')
        config.set('State', 'currenttab', self.CurrentTab)
        config.set('State', 'Date', self.fileDate)
        config.add_section('Flags')
        config.set('Flags', 'stimEnable', self.StimEnable)
        config.set('Flags', 'WavePlot', self.WavePlot)
        config.set('Flags', 'ShowSpectrum', self.ShowSpectrum)
        
        config.add_section('Conditioning')
        config.set('Conditioning', 'CN_Level', self.CN_Level)
        config.set('Conditioning', 'CN_Dur', self.CN_Dur)
        config.set('Conditioning', 'CN_Var', self.CN_Var )
        config.set('Conditioning', 'CN_Mode', self.CN_Mode)

        config.add_section('Prepulse')
        config.set('Prepulse', 'PP_Level', self.PP_Level)
        config.set('Prepulse', 'PP_OffLevel', self.PP_OffLevel)
        config.set('Prepulse', 'PP_Dur', self.PP_Dur)
        config.set('Prepulse', 'PP_Mode', self.PP_Mode)
        config.set('Prepulse', 'PP_Freq', self.PP_Freq)
        config.set('Prepulse', 'PP_HP', self.PP_HP)
        config.set('Prepulse', 'PP_LP', self.PP_LP)
        config.set('Prepulse', 'PP_Notch_F1', self.PP_Notch_F1)
        config.set('Prepulse', 'PP_Notch_F2', self.PP_Notch_F2)
        config.set('Prepulse', 'PP_MultiFreq', self.PP_MultiFreq)
        config.set('Prepulse', 'PP_GapFlag', self.PP_GapFlag)
        
        config.add_section('Trials')
        config.set('Trials', 'ITI', self.ITI)        
        config.set('Trials', 'Var', self.ITI_Var)
        config.set('Trials', 'NTrials', int(self.Trials))
        config.set('Trials', 'NHabTrials', int(self.NHabTrials))
        
        config.add_section('Startle')
        config.set('Startle', 'Dur', self.ST_Dur)
        config.set('Startle', 'Level', self.ST_Level)

        configfile = open(self.fileName, "w")
        config.write(configfile)
        configfile.close()
        

# basic configuration file for analysis... 
    
    def saveConfig(self, filename):
        config = ConfigParser.RawConfigParser()
        config.add_section('Analysis')
        config.set('Analysis', 'start', self.Analysis_Start)
        config.set('Analysis', 'end', self.Analysis_End)
        config.set('Analysis', 'LPF', self.Analysis_LPF)
        config.set('Analysis', 'HPF', self.Analysis_HPF)
        config.add_section('RecentFiles')
        nf = len(self.recentFiles)
        if nf > 8:
            nf = 8
        config.set('RecentFiles', 'nfiles', nf)
        for i in range(0, nf):
            config.set('RecentFiles', ('File.%d' % (i)), self.recentFiles.popleft())
        config.add_section('State')
        config.set('State', 'currenttab', self.getCurrentTab())

        configfile = open(filename, 'wb')
        config.write(configfile)
        configfile.close()
    
    
    def getConfig(self, filename):
        config = ConfigParser.RawConfigParser()
        config.read(filename)

        self.Analysis_Start = config.getfloat('Analysis', 'start')
        self.Analysis_End = config.getfloat('Analysis', 'end')
        self.Analysis_LPF = config.getfloat('Analysis', 'LPF')
        self.Analysis_HPF = config.getfloat('Analysis', 'HPF')
        self.recentFiles = deque()
        nf = config.getint('RecentFiles', 'nfiles')
        for i in range(0, nf):
            f = config.get('RecentFiles', ('File.%d' % (i)))
            self.recentFiles.appendleft(f)
        ct = config.getint('State', 'currenttab')
        self.setCurrentTab(ct)

#-------------Annoatation section -------------------
#  The annotation table is used to input data from the animal's behavior as monitored
#  on a video camera. There is one annotation for each trial, which includes
#  the animal's behavioral state, the quadrant location, the head orientation, and
#  possibly some text notes. The time is pulled form the data file, and an offset
#  time (the time in seconds to the first startle stimulus in the video) can be
#  added to help estimate where to "scrub" the video for the next behavioral state.

    def updateTable(self, reset = False):
        """ Here we create a new QTable and put the widgets we need into the cells.
            Note we use any selection of a widget to call changeStates, to change all
            of the subsequent settings (in remaining trials) of the animal's state.
            This is a convienience for the user. """
        tw = self.ui.Annotate_Table
        tw.clear()
        if self.Annotation is None:
            self.Annotation = StartleRun()
            self.Annotation.create(ntrials=24)
        tw.setRowCount(len(self.Annotation))
        for i in range(0, len(self.Annotation)):
            tw.setRowHeight(i, 22)
        tw.setColumnCount(5)
        tw.setHorizontalHeaderLabels(['Time', 'State', 'Quadrant', 'Orientation', 'Notes'])
        tw.setAlternatingRowColors(True)
        tw.setSelectionBehavior(Qt.QTableWidget.SelectItems)
        tw.setSelectionMode(Qt.QTableWidget.SingleSelection)
        tw.showGrid()       
        selected = None
        row = 0
        for trial in self.Annotation.trials():
            if reset:
                trial.state = 'Quiet'
                trial.quadrant = 'Front'
                trial.orientation = 'Front'
                trial.notes = ''
            item = self.makeStateWidget(row, 1, state = trial.state)
            item.activated.connect(self.changeStates)
            # self.connect(item, QtCore.SIGNAL("activated(int)"),
            #          self.changeStates)
            tw.setCellWidget(row, 1, item)
            item = self.makeOrientWidget(row, 2, orient=trial.quadrant)
            item.activated.connect(self.changeStates)
            # self.connect(item, QtCore.SIGNAL("activated(int)"),
            #          self.changeStates)
            tw.setCellWidget(row, 2, item)
            item = self.makeOrientWidget(row, 3, orient=trial.orientation)
            item.activated.connect(self.changeStates)
            # self.connect(item, QtCore.SIGNAL("activated(int)"),
            #          self.changeStates)
            tw.setCellWidget(row, 3, item)
            notes = Qt.QString(trial.notes)
            tw.setItem(row, 4, Qt.QTableWidgetItem(notes))

            row = row + 1
        self.updateAnnotateTime()
        tw.resizeColumnsToContents()
        tw.setColumnWidth(0, 60)
        tw.setColumnWidth(4, 200)
        # tw.resizeRowsToContents()
        if selected is not None:
            selected = setSelected(True)
            tw.setCurrentItem(selected)
            tw.scrollToItem(selected)

    def resetTable(self):
        """ button to reset table to quiet, front, front, but not disturb times """
        
    def changeStates(self, state):
        """ based on the state of the current widget in "sender", we try to
            set the remainder of the widgets in that column to the same state """
        item = self.sender()
        if item is None or not isinstance(item, Qt.QComboBox):
            return # not us somehow  - be silent
        row = 0
        # now set all of the rest of the values in this column to the same value...
        tw = self.ui.Annotate_Table
        row = item.table_Row
        col = item.table_Col
        irow = 0
        ref_index = item.currentIndex()
        for trial in self.Annotation.trials():
            if irow <= row:
                irow = irow + 1
                continue
            w = tw.cellWidget(irow, col) # get the widget in that location
            w.setCurrentIndex(ref_index)
            irow = irow + 1
        self.Annotation.setDirty(True)
        
    def updateAnnotateTime(self):
        """ Here we adjust the times in the time column to include the video delay """
        tw = self.ui.Annotate_Table
        viddelay = self.ui.AnnotateVideoDelay.value()
        print 'new viddelay: ', viddelay
        if len(self.ITI_List) > 0:
            cumulativeTime = np.cumsum(self.ITI_List)-self.ITI_List[0]
        else:
            cumulativeTime = np.arange(0,self.Annotation.ntrials()*self.ITI, self.ITI)
            selected = None
        for row in range(0, len(self.ITI_List)):
            tw.setItem(row, 0, Qt.QTableWidgetItem('%s' %
                    str(datetime.timedelta(seconds=int(cumulativeTime[row]+viddelay)))))

    def retrieveTable(self):
        """ Load the data displayed in the table back into the annotation data """
        if self.Annotation is None:
            return
        self.readConditions()
        if not self.Annotation.isDirty():
            return # no changes...
        row = 0
        tw = self.ui.Annotate_Table
        for trial in self.Annotation.trials():
            w0 = tw.takeItem(row, 0)
            if w0 is not None:
                trial.time = w0.text()
            else:
                trial.time = 'no time'
            w1 = tw.cellWidget(row, 1)
            trial.state = w1.currentText()
            w2 = tw.cellWidget(row,2)
            trial.quadrant = w2.currentText()
            w3 = tw.cellWidget(row,3)
            trial.orient = w3.currentText()
            no = tw.takeItem(row, 4)
            if no is None:
                notes = ''
            else:
                notes = no.text()
            trial.notes = notes
            row = row + 1
            
    def dumpTable(self):
        """ print out a human-readable copy of the table at the terminal """
        self.retrieveTable()
        row = 0
        print "Trial\tTime\t    State\t\tQuadrant\tOrientation\tNotes"
        for tr in self.Annotation.trials(): 
            print "%6d\t%s\t%10s\t%8s\t%8s\t%s" % (row+1, tr.time, tr.state, tr.quadrant, tr.orient, tr.notes)
            row = row + 1

    def saveAnnotation(self):
        self.retrieveTable()
        (p, f) = os.path.split(self.inFileName)
        print p
        print f
        (fb, e) = os.path.splitext(f)
        fn = p + '/' + fb + '.ann' # make filename for annotation file
        error = None
        fh = None
        try:
            fh = gzip.open(unicode(fn), "wb")
            cPickle.dump(self.Annotation, fh, 2)
        except (IOError, OSError), e:
            error = 'Failed to save: %s' % e
            print error
        finally:
            if fh is not None:
                fh.close()
            if error is not None:
                return False, error
            self.Annotation.setDirty(False)
            print "saved in %s" % (fn)
            return(True, "Annotation Saved to %s" % Qt.QFileInfo(fn))
            
    def loadAnnotation(self):
        (p, f) = os.path.split(self.inFileName)
        (fb, e) = os.path.splitext(f)
        fn = p + '/' + fb + '.ann' # make filename for annotation file
        fh = None
        try:
            fh = gzip.open(unicode(fn), "rb")
            self.Annotation.clear()
            self.Annotation = cPickle.load(fh)
        except:
            raise(IOError, "Annotation file not found: %s" % fn)
        finally:
            if fh is not None:
                fh.close()
            return(False)
            self.Annotation.setDirty(False)
            self.updateTable()
            self.updateConditions()
            return(True, "Annotation Loaded from %s" % (Qt.QFileInfo(fn)))
        
    def makeStateWidget(self, row = 1, col=1, state='Quiet'):
        box = ComboItem()
        sw = box.createEditor(row=row, col=col, combolist=self.Behavior_states)
        ind = sw.findText(state)
        sw.setCurrentIndex(ind)
        return(sw)
        
    def makeOrientWidget(self, row = 1, col=1,  orient = 'Front'):
        box = ComboItem()
        orwidget = box.createEditor(row=row, col=col, combolist=self.Orientations)
        ind = orwidget.findText(orient)
        orwidget.setCurrentIndex(ind)
        return(orwidget)
    
    def readConditions(self): 
        """ read the checkboxes on the screen and fill the dictionary with booleans """
        condx={}
        condx['Use'] = self.ui.Behavior_Use.isChecked()
        condx['Quiet'] = self.ui.Behavior_Quiet.isChecked()
        condx['Grooming'] = self.ui.Behavior_Grooming.isChecked()
        condx['Exploring'] = self.ui.Behavior_Exploring.isChecked()
        condx['Sleeping'] = self.ui.Behavior_Sleeping.isChecked()
        condx['Other'] = self.ui.Behavior_Other.isChecked()
        condx['Q_Front'] = self.ui.Quadrant_Front.isChecked()
        condx['Q_Left'] = self.ui.Quadrant_Left.isChecked()
        condx['Q_Right'] = self.ui.Quadrant_Right.isChecked()
        condx['Q_Back'] = self.ui.Quadrant_Back.isChecked()
        condx['O_Front'] = self.ui.Orient_Front.isChecked()
        condx['O_Left'] = self.ui.Orient_Left.isChecked()
        condx['O_Right'] = self.ui.Orient_Right.isChecked()
        condx['O_Back'] = self.ui.Orient_Back.isChecked()
        self.Annotation.setConditions(condx) # store it ...
    
    def updateConditions(self):
        """ Update the checkboxes from the Annotation, restore the conditions to the checkboxes."""
        condx = self.Annotation.conditions()
        if condx is {}:
            return
        self.ui.Behavior_Use.setChecked(condx['Use'])
        self.ui.Behavior_Quiet.setChecked(condx['Quiet'])
        self.ui.Behavior_Grooming.setChecked(condx['Grooming'])
        self.ui.Behavior_Exploring.setChecked(condx['Exploring'])
        self.ui.Behavior_Sleeping.setChecked(condx['Sleeping'])
        self.ui.Behavior_Other.setChecked(condx['Other'])
        self.ui.Quadrant_Front.setChecked(condx['Q_Front'])
        self.ui.Quadrant_Left.setChecked(condx['Q_Left'])
        self.ui.Quadrant_Right.setChecked(condx['Q_Right'])
        self.ui.Quadrant_Back.setChecked(condx['Q_Back'])
        self.ui.Orient_Front.setChecked(condx['O_Front'])
        self.ui.Orient_Left.setChecked(condx['O_Left'])
        self.ui.Orient_Right.setChecked(condx['O_Right'])
        self.ui.Orient_Back.setChecked(condx['O_Back'])

    def getRejectTrials(self):
        self.retrieveTable() # get the current table
        self.readConditions() # and the logical conditions
        self.RejectedTrials = []
        condx = self.Annotation.conditions()
        if not condx['Use']: # not using behavior
            return
        nt = 0
        for trial in self.Annotation.trials():
            for s in self.Behavior_states: # check all the behavioral states
                if not condx[s] and trial.state == s:
                    self.RejectedTrials.append(nt)
                    break
            for s in self.Orientations: # check all the Quadrant positions
                if not condx['Q_' + s] and trial.quadrant == s:
                    self.RejectedTrials.append(nt)
                    break
            for s in self.Orientations: # check all the orientations
                if not condx['O_' + s] and trial.orientation == s:
                    self.RejectedTrials.append(nt)
                    break
            nt = nt + 1

#-------------------------------------------------------------------------------
# a little class to handle the trials and load/save the data state.
class TrialData(object):
    """ Holds information about performance on ONE trial """
    def __init__(self, trial=1, timestamp=0.0, state='Quiet', quadrant='Front', orientation='Front', notes=''):
        self.trial = trial
        self.timestamp = timestamp
        self.state = state
        self.quadrant = quadrant
        self.orientation = orientation
        self.notes = notes

#-------------------------------------------------------------------------------

class StartleRun(object):
    """ Holds the data from a run of N trials
        also includes routines to make """
    MAGIC_NUMBER = 0x2995A
    FILE_VERSION = 100
    
    def __init__(self):
        self.__fname = Qt.QString() # file that data came from
        self.__ntrials = 0
        self.__trials = [] # list of trials
        self.__trialFromID = {} #
        self.__date = Qt.QDate.currentDate() # instantiation
        self.__dirty = False
        self.__conditions = {}
    
    def __len__(self):
        return len(self.__trials)
    
    def __iter__(self):
        for x in range(0, self.__ntrials):
            yield(x)
            
    def clear(self):
        self.__fname = Qt.QString()
        self.__trials = []
        self.__ntrials = 0
        self.__trialFromID = {}
        self.__date = Qt.QDate.currentDate() # instantiation
        self.__dirty = False
        self.__conditions = {}
    
    def create(self, ntrials = 1, filename = None):
        """ initialize the data set """
        if filename is not None:
            self.__fname = Qt.QString(filename)
        self.__ntrials = ntrials
        for i in range(0, ntrials):
            self.__trials.append(TrialData(trial=i)) # create a new trial structure
        self.__date = Qt.QDate.currentDate()
        self.__dirty = True
    
    def setDirty(self, dirty=True):
        self.__dirty = dirty
    
    def isDirty(self):
        return(self.__dirty)
    
    def setConditions(self, conditions):
        """ conditions is a dictionary of boolean values used to control the analysis """
        self.__conditions = conditions
        self.__dirty = True
    
    def conditions(self):
        return(self.__conditions)
        
    def ntrials(self):
        return(self.__ntrials)
    def trials(self):
        return(self.__trials)
    def date(self):
        return(self.__date)
    
    def getAllStates(self):
        pass
    def getAllDirections(self):
        pass
    def getAllOrientations(self):
        pass
    def dumpTable(self):
        pass
    

#-------------------------------------------------------------------------------


class ComboItem(Qt.QTableWidgetItem):
    """ This class makes a combobox to put into a table cell. The box includes
        data about the row and column of the table cell, since that seems to be
        hard to get otherwise. """
    def __init__(self):
        Qt.QTableWidgetItem.__init__(self, 1001)
        self.cb = Qt.QComboBox()
        self.cb.setFont(Qt.QFont('Arial', 11, Qt.QFont.Normal))

    def createEditor(self, row, col, combolist):
        for s in combolist:
            self.cb.addItem(s)
        self.cb.setCurrentIndex(0)
        self.cb.table_Row = row
        self.cb.table_Col = col
        return(self.cb)
    
# the following routines are not used - I included them because I copied the
# code from somewhere else.
    def setContentFromEditor(self, w):
        # the user changed the value of the combobox, so synchronize the
        # value of the item (its text), with the value of the combobox
        if w.inherits("QComboBox"):
            self.setText(w.currentText())
        else:
            Qt.QTableItem.setContentFromEditor(self, w)

    def getItemText(self):
        return(self.cb.itemText(self.cb.currentIndex()))
        
################################################################################
#
# main entry
#

if __name__ == "__main__":
# check the hardware first
    app = QtGui.QApplication(sys.argv)
    MainWindow = PyStartle()
    MainWindow.show()
    sys.exit(app.exec_())
    