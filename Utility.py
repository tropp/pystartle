"""
Utils.py - general utility routines
- power spectrum
- elliptical filtering
- handling very long input lines for dictionaries

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

import sys, re, os
from pylab import * # includes numpy

# compute the power spectrum.
# simple, no windowing etc...

class Utility:
    def __init__(self):
        self.debugFlag = False
    

    def pSpectrum(self, data=None, samplefreq=44100):
        npts = len(data)
    # we should window the data here
        if npts == 0:
            print "? no data in pSpectrum"
            return
    # pad to the nearest higher power of 2
        (a,b) = frexp(npts)
        if a <= 0.5:
            b = b = 1
        npad = 2**b -npts
        if self.debugFlag:
            print "npts: %d   npad: %d   npad+npts: %d" % (npts, npad, npad+npts)    
        padw =  append(data, zeros(npad))
        npts = len(padw)
        spfft = fft(padw)
        nUniquePts = ceil((npts+1)/2.0)
        spfft = spfft[0:nUniquePts]
        spectrum = abs(spfft)
        spectrum = spectrum / float(npts) # scale by the number of points so that
                           # the magnitude does not depend on the length 
                           # of the signal or on its sampling frequency  
        spectrum = spectrum**2  # square it to get the power    
        spmax = amax(spectrum)
        spectrum = spectrum + 1e-12*spmax
        # multiply by two (see technical document for details)
        # odd nfft excludes Nyquist point
        if npts % 2 > 0: # we've got odd number of points fft
            spectrum[1:len(spectrum)] = spectrum[1:len(spectrum)] * 2
        else:
            spectrum[1:len(spectrum) -1] = spectrum[1:len(spectrum) - 1] * 2 # we've got even number of points fft
        freqAzero = arange(0, nUniquePts, 1.0) * (samplefreq / npts)
        return(spectrum, freqAzero)
    
# filter signal with elliptical filter
    def SignalFilter(self, signal, LPF, HPF, samplefreq):
        if self.debugFlag:
            print "sfreq: %f LPF: %f HPF: %f" % (samplefreq, LPF, HPF)
        flpf = float(LPF)
        fhpf = float(HPF)
        sf = float(samplefreq)
        sf2 = sf/2
        wp = [fhpf/sf2, flpf/sf2]
        ws = [0.5*fhpf/sf2, 2*flpf/sf2]
        if self.debugFlag:
            print "signalfilter: samplef: %f  wp: %f, %f  ws: %f, %f lpf: %f  hpf: %f" % (
               sf, wp[0], wp[1], ws[0], ws[1], flpf, fhpf)
        filter_b,filter_a=scipy.signal.iirdesign(wp, ws,
                gpass=1.0,
                gstop=60.0,
                ftype="ellip")
        w=scipy.signal.lfilter(filter_b, filter_a, signal) # filter the incoming signal
        if self.debugFlag:
            print "sig: %f-%f w: %f-%f" % (min(signal), max(signal), min(w), max(w))
        return(w)
        
    # do an eval on a long line (longer than 512 characters)
    # assumes input is a dictionary that is too long
    # parses by breaking the string down and then reconstructing each element
    #
    def long_Eval(self, line):
        sp = line.split(',')
        u = {}
        for di in sp:
            try:
                r = eval('{' + di.strip('{}') + '}')
                u[r.keys()[0]] = r[r.keys()[0]]
            except:
                continue
        return(u)