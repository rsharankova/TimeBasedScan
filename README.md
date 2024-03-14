# TimeBasedScan

Files in directory:
 - scanner.py: device scanner class. Contains acsys-python based loops for setting & reading ACNET devices
 - GUI.py: simple GUI that generates sinewave patterns for device ramps and calls on scanner class functions to execute the scan
 - Reading_devices_xxx.csv: collection of Linac devices to be read out and saved
 - run_scanner.py: command line execution of scanner class functions
 - analysis.py: data analysis scripts. To be implemented.

How to run a scan with the GUI:
1) Fill in the following fields:
 - Select Reading_devices_xxx.csv from browser
 - List devices to be scanned (comma separated)
 - Fetch button will retrieve current value of the setting property
 - Amplitude: list of desired sine amplitudes, one per scan device
 - Number of periods: how many sine periods in a single superperiod (e.g. 15)
 - Points per superperiod: how many points to divide the superperiod in. Has to be sufficiently larger than the number of periods to get a smooth sine and should not divide exactly by the number of periods (e.g. 299)
 - Number of superperiods: how many times to repeat the full pattern (e.g. 1)
 - Sampling event: LCLK or TCLK. E.g. $0A
 - Number of measurements: how many times to read devices at the same setting
2) Select setting role from dropdown
3) Get new ticket if need be using LOGIN button
4) Press GENERATE SETUP FILE
5) Press START SCAN to start the ramp. Data will be saved automatically at the end of the scan

How to record N pulses without settings:
1) Fill in the following fields:
   - Select Reading_devices_xxx.csv from file browser
   - Number of measrements: how many measurements to record. Defaults to 1
   - Press START SCAN. N measurements 
