# Description:
# This script is the main controller for the VAS Vickrey Protocol.
# It is responsible for initializing the exoskeletons, calibrating them, and running the main control loop.
# 
# Original template created by: Emily Bywater 
# Modified for VAS Vickrey protocol by: Nundini Rawal, John Hutchinson
# Date: 06/13/2024

import os, sys, time, socket, threading

from flexsea.device import Device
from rtplot import client

from ExoClass_thread import ExobootThread
from LoggingClass import LoggingNexus, FilingCabinet
from GaitStateEstimator_thread import GaitStateEstimator
from exoboot_remote.exoboot_remote_control import ExobootRemoteServerThread
from curses_HUD.hud_thread import HUDThread

from SoftRTloop import FlexibleSleeper
from constants import DEV_ID_TO_SIDE_DICT, DEFAULT_KP, DEFAULT_KI, DEFAULT_KD, DEFAULT_FF, RTPLOT_IP, TRIAL_CONDS_DICT

thisdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(thisdir)

class MainControllerWrapper:
    """
    Runs Necessary threads on pi to run exoboot

    Allows for high level interaction with flexsea controller
    """
    def __init__(self, subjectID, trial_type, trial_cond, description, usebackup, streamingfrequency=1000, clockspeed=0.2):
        # Settings
        self.streamingfrequency = streamingfrequency
        self.clockspeed = clockspeed

        # Subject info
        self.subjectID = subjectID
        self.trial_type = trial_type.upper()
        self.trial_cond = trial_cond.upper()
        self.description = description
        self.usebackup = usebackup in ["true", "True", "1", "yes", "Yes"]
        self.file_prefix = "{}_{}_{}_{}".format(self.subjectID, self.trial_type, self.trial_cond, self.description)

        # Thread events
        self.pause_event = threading.Event()
        self.log_event = threading.Event()
        self.quit_event = threading.Event()
        self.pause_event.clear()
        self.log_event.clear()
        self.quit_event.set()
        self.startstamp = time.perf_counter() # Timesync logging between all threads

        # Intiailize subject
        self.init_subject()

        # Init FilingCabinet
        self.filingcabinet = FilingCabinet("subject_data", self.subjectID)

        # Initializing Flexsea devices
        # side_left, device_left, side_right, device_right = self.get_active_ports()
        side_left, device_left = self.get_active_port_single("/dev/ttyACM0")
        
        # Start device streaming and set gains:
        device_left.start_streaming(self.streamingfrequency)
        # device_right.start_streaming(self.streamingfrequency)
        device_left.set_gains(DEFAULT_KP, DEFAULT_KI, DEFAULT_KD, 0, 0, DEFAULT_FF)
        # device_right.set_gains(DEFAULT_KP, DEFAULT_KI, DEFAULT_KD, 0, 0, DEFAULT_FF)

        # Init Exothreads
        self.exothread_left = ExobootThread(side_left, device_left, self.startstamp, name='exothread_left', daemon=True, pause_event=self.pause_event, quit_event=self.quit_event, log_event=self.log_event)
        # self.exothread_right = ExobootThread(side_right, device_right, self.startstamp, name='exothread_right', daemon=True, pause_event=self.pause_event, quit_event=self.quit_event, log_event=self.log_event)
        self.gse_thread = GaitStateEstimator(self.startstamp, device_left, self.exothread_left, daemon=True, pause_event=self.pause_event, quit_event=self.quit_event, log_event=self.log_event)

        # Init LoggingNexus with Exothreads
        self.loggingnexus = LoggingNexus(self.subjectID, self.file_prefix, self.filingcabinet, self.exothread_left, self.exothread_right, self.gse_thread, log_event=self.log_event)

        # Init remote_control
        self.remote_thread = ExobootRemoteServerThread(self, self.startstamp, self.filingcabinet, usebackup=self.usebackup, pause_event=self.pause_event, quit_event=self.quit_event, log_event=self.log_event)
        self.remote_thread.set_target_IP(self.myIP)

        # Init HUD
        # self.hud = HUDThread(self, "exohud_layout.json", napms=10, pause_event=self.pause_event, quit_event=self.quit_event)
        # self.hud.getwidget("si").settextline(0, "{}, {}, {}, {}".format(self.subjectID, self.trial_type, self.trial_cond, self.description))
        # self.hud.getwidget("ii").settextline(0, str(self.myIP))

    @staticmethod
    def get_active_ports():
        """
        To use the exos, it is necessary to define the ports they are going to be connected to. 
        These are defined in the ports.yaml file in the flexsea repo
        """
        # port_cfg_path = '/home/pi/VAS_exoboot_controller/ports.yaml'
        # TODO remove explicit port references
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
            raise Exception("Invalid sides for devices: Check DEV_ID_TO_SIDE_DICT!")
        
    @staticmethod
    def get_active_port_single(port):
        """
        To use the exos, it is necessary to define the ports they are going to be connected to. 
        These are defined in the ports.yaml file in the flexsea repo
        """
        # port_cfg_path = '/home/pi/VAS_exoboot_controller/ports.yaml'
        # TODO remove explicit port references
        device = Device(port=port, firmwareVersion="7.2.0", baudRate=230400, logLevel=3)   
        device.open()
        side= DEV_ID_TO_SIDE_DICT[device.id]
        print("Device: {}, {}".format(device.id, side))

        return side, device
    
    def init_subject(self):
        """
        Initialize subject info and get IP
        """
        # TODO finish dummymode
        # if self.subjectID == "DUMMY":
        #     self.dummymode = True
        # else:
        #     self.dummymode = False

        # Validate trial_type and trial_cond
        self.valid_trial_typeconds = TRIAL_CONDS_DICT
        try:
            if not self.trial_type in self.valid_trial_typeconds.keys():
                raise Exception("Invalid trial type: {} not in {}".format(self.trial_type, self.valid_trial_typeconds.keys()))

            valid_conds = self.valid_trial_typeconds[self.trial_type]
            if valid_conds and self.trial_cond not in valid_conds:
                raise Exception("Invalid trial cond: {} not in {}".format(trial_cond, valid_conds))
        except:
            print("\nINCORRECT ARGUMENTS\n")
            print("How to run: python Exoboot_Wrapper.py subjectID trial_type trial_cond description")
            print("See constants for all trial_type/trial_cond pairs")
        
        self.file_prefix = "{}_{}_{}_{}".format(self.subjectID, self.trial_type, self.trial_cond, self.description)

        # Get own IP address for GRPC
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        self.myIP = s.getsockname()[0] + ":50051"
        print("myIP: {}".format(self.myIP))

    def run(self):
        """
        Main controller loop.
        Receives incoming commands/logging requests from exoboot_remote
        Updates exoboot state estimates
        Logs exothread data
        Updates HUD
        """
        # Set Events
        self.pause_event.set()
        self.log_event.set()
        self.quit_event.set()

        # Start Threads
        self.exothread_left.start()
        self.exothread_right.start()
        self.gse_thread.start()
        self.remote_thread.start()
        # self.hud.start()

        print("Spooling Belts...")
        self.exothread_left.spool_belt()
        self.exothread_right.spool_belt()

        self.softrtloop = FlexibleSleeper(period=1/self.clockspeed)
        print("Looping...")
        try:
            while self.quit_event.is_set():
                # Log data. Obeys log_event
                self.loggingnexus.log()

                # SoftRT pause
                self.softrtloop.pause()

        except Exception as e:
            print("Exception: ", e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

        finally:
            print("Closing Please Wait...")
            # Routine to close threads
            self.pause_event.set()
            time.sleep(0.25)
            self.quit_event.clear()

            # Stop motors and close device streams
            self.exothread_left.flexdevice.stop_motor() 
            self.exothread_right.flexdevice.stop_motor()

            self.exothread_left.flexdevice.close()
            self.exothread_right.flexdevice.close()
            print("Goodbye")


if __name__ == "__main__":
    try:
        assert len(sys.argv) - 1 == 5
    except:
        print("\nNOT ENOUGH ARGUMENTS\n")
        print("How to run: python Exoboot_Wrapper.py subjectID trial_type trial_cond description, usebackup")
        print("trial_type, trial_cond pairs in constants.py")
        exit(1)

    _, subjectID, trial_type, trial_cond, description, usebackup = sys.argv
    mainwrapper = MainControllerWrapper(subjectID, trial_type, trial_cond, description, usebackup, streamingfrequency=1000).run()