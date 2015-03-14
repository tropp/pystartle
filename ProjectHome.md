Python-based acoustic startle stimulus presentation and data collection. Requires NIDAQ hardware for stimulus generation and Tucker-Davis (TDT) System III for acquisition.

This code is in development, and multiple versions are present in the source directory.

Requires Qt libraries from Trolltech, Numpy, Scipy, (or the Enthought distribution), Qwt, and PyQwt.
Requires win32com (for active-X interface to the TDT system).
Requires an nidaq.h wrapper (in the nidaq subdirectory).

Note: the program runs using system audio if the nidaq hardware is not found; however simultaneous input/output is not available, so this is only useful for demonstration purposes.
