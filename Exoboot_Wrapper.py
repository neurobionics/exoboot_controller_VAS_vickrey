# Description:
# This script is the main controller for the VAS Vickrey Protocol.
# It is responsible for initializing the exoskeletons, calibrating them, and running the main control loop.
# 
# Original template created by: Emily Bywater 
# Modified for VAS Vickrey protocol by: Nundini Rawal, John Hutchinson
# Date: 06/13/2024

import os, sys, csv, time, threading

from flexsea.device import Device
from rtplot import client 

from LoggingClass import LoggingNexus
from ExoClass_thread import ExobootThread
from GaitStateEstimator_thread import GaitStateEstimator
from exoboot_remote_control import ExobootRemoteServerThread

from SoftRTloop import FlexibleSleeper
from constants import PI_IP, DEV_ID_TO_SIDE_DICT, DEFAULT_KP, DEFAULT_KI, DEFAULT_KD, DEFAULT_FF, RTPLOT_IP

thisdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(thisdir)

class MainControllerWrapper:
    """
    Runs Necessary threads on pi to run exoboot

    Allows for high level interaction with flexsea controller
    """
    def __init__(self, subjectID, trial_type, trial_cond, description, streamingfrequency=1000, clockspeed=0.2):
        self.subjectID = subjectID
        self.trial_type = trial_type.upper()
        self.trial_cond = trial_cond.upper()
        self.description = description

        self.streamingfrequency = streamingfrequency
        self.clockspeed = clockspeed

        # Trial type and cond validation
        self.valid_trial_typeconds = {'VICKREY': ["WNE", "EPO", "NPO"],
                             'VAS': [],
                             'JND': ['SPLITLEG', 'SAMELEG'],
                             'PREF': ['SLIDER', 'BTN'],
                             'THERMAL': []}
        
        if not self.trial_type in self.valid_trial_typeconds.keys():
            raise Exception("Invalid trial type: {} not in {}".format(self.trial_type, self.valid_trial_typeconds.keys()))
    
        valid_conds = self.valid_trial_typeconds[trial_type]
        if valid_conds and self.trial_cond not in valid_conds:
            raise Exception("Invalid trial cond: {} not in {}".format(trial_cond, valid_conds))
        
        self.file_prefix = "{}_{}_{}_{}".format(self.subjectID, self.trial_type, self.trial_cond, self.description)

    @staticmethod
    def get_active_ports():
        """
        To use the exos, it is necessary to define the ports they are going to be connected to. 
        These are defined in the ports.yaml file in the flexsea repo
        """
        # port_cfg_path = '/home/pi/VAS_exoboot_controller/ports.yaml'
        device_1 = Device(port="/dev/ttyACM0", firmwareVersion="7.2.0", baudRate=230400, logLevel=3)
        device_2 = Device(port="/dev/ttyACM1", firmwareVersion="7.2.0", baudRate=230400, logLevel=3)
        
        # Establish a connection between the computer and the device    
        device_1.open()
        device_2.open()

        # Get side from side_dict
        side_1 = DEV_ID_TO_SIDE_DICT[device_1.id]
        side_2 = DEV_ID_TO_SIDE_DICT[device_2.id]

        print("Device 1: {}, {}".format(device_1.id, side_1))
        print("Device 2: {}, {}".format(device_2.id, side_2))

        # Always assign first pair of outputs to left side
        if side_1 == 'left':
            return side_1, device_1, side_2, device_2
        elif side_1 == 'right':
            return side_2, device_2, side_1, device_1
        else:
            raise Exception("Invalid sides for devices: Probably not possible?")
    
    def run(self):
        """
        Initialize trial information
        Start All Threads
        TODO Print good info
        """
        try:
            # Initializing the Exo
            side_left, device_left, side_right, device_right = self.get_active_ports()
            
            # Start device streaming and set gains:
            device_left.start_streaming(self.streamingfrequency)
            device_right.start_streaming(self.streamingfrequency)
            device_left.set_gains(DEFAULT_KP, DEFAULT_KI, DEFAULT_KD, 0, 0, DEFAULT_FF)
            device_right.set_gains(DEFAULT_KP, DEFAULT_KI, DEFAULT_KD, 0, 0, DEFAULT_FF)

            """Initialize Threads"""
            # Thread events
            self.pause_event = threading.Event()
            self.quit_event = threading.Event()
            self.pause_event.clear() # Start with threads paused
            self.quit_event.set()
            self.startstamp = time.perf_counter()

            # Thread 1/2: Left and right exoboots
            self.exothread_left = ExobootThread(side_left, device_left, self.startstamp, name='exothread_left', daemon=True, pause_event=self.pause_event, quit_event=self.quit_event)
            self.exothread_right = ExobootThread(side_right, device_right, self.startstamp, name='exothread_right', daemon=True, pause_event=self.pause_event, quit_event=self.quit_event)
            self.exothread_left.start()
            self.exothread_right.start()

            # Thread 3: Gait State Estimator
            self.gse_thread = GaitStateEstimator(self.startstamp, device_left, device_right, self.exothread_left, self.exothread_right, daemon=True, pause_event=self.pause_event, quit_event=self.quit_event)
            self.gse_thread.start()

            # Thread 4: Exoboot Remote Control
            self.remote_thread = ExobootRemoteServerThread(self, self.startstamp, self.trial_type, pause_event=self.pause_event, quit_event=self.quit_event)
            self.remote_thread.set_target_IP(PI_IP)
            self.remote_thread.start()

            # LoggingNexus
            self.loggingnexus = LoggingNexus(self.file_prefix, self.exothread_left, self.exothread_right, self.gse_thread, pause_event=self.pause_event)

            # ~~~Main Loop~~~
            self.softrtloop = FlexibleSleeper(period=1/self.clockspeed)
            self.pause_event.set()
            while self.quit_event.is_set():
                try:
                    # TODO add curses fancy terminal
                    print("Peak Torques L/R: ", self.gse_thread.peak_torque_left, '/', self.gse_thread.peak_torque_right)

                    # Data logging
                    if self.pause_event.is_set():
                        self.loggingnexus.log()

                    # SoftRT pause
                    self.softrtloop.pause()

                except KeyboardInterrupt:
                    print("Closing all threads")
                    self.quit_event.clear()

        except Exception as e:
            print("Exception: ", e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

        finally:            
            # Routine to close threads safely
            self.pause_event.set()
            time.sleep(0.5)
            self.quit_event.clear()

            # Stop motors and close device streams
            self.exothread_left.flexdevice.stop_motor() 
            self.exothread_right.flexdevice.stop_motor()

            self.exothread_left.flexdevice.close()
            self.exothread_right.flexdevice.close()
            print("Goodbye")

if __name__ == "__main__":
    subjectID = sys.argv[1]
    trial_type = sys.argv[2]
    trial_cond = sys.argv[3]
    description = sys.argv[4]
    MainControllerWrapper(subjectID, trial_type, trial_cond, description, streamingfrequency=1000).run()
