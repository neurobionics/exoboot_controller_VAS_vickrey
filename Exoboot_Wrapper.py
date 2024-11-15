# Description:
# This script is the main controller for the VAS Vickrey Protocol.
# It is responsible for initializing the exoskeletons, calibrating them, and running the main control loop.
# 
# Original template created by: Emily Bywater 
# Modified for VAS Vickrey protocol by: Nundini Rawal, John Hutchinson
# Date: 06/13/2024

import os, sys, csv, time, socket, threading

from flexsea.device import Device
from rtplot import client

from validator import Validator
from ExoClass_thread import ExobootThread
from GaitStateEstimator_thread import GaitStateEstimator
from exoboot_remote_control import ExobootRemoteServerThread
from LoggingClass import LoggingNexus, FilingCabinet
from curses_HUD.hud_thread import HUDThread

from SoftRTloop import FlexibleSleeper
from constants import *

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "curses_HUD"))
from curses_HUD import hud_thread

thisdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(thisdir)

class MainControllerWrapper:
    """
    Runs Necessary threads on pi to run exoboot

    Allows for high level interaction with flexsea controller
    """
    def __init__(self, subjectID=None, trial_type=None, trial_cond=None, description=None, usebackup=False, continuousmode = False, overridedefaultcurrentbounds=False, streamingfrequency=1000, clockspeed=0.2):
        self.streamingfrequency = streamingfrequency
        self.clockspeed = clockspeed

        # Subject info
        self.subjectID = subjectID
        self.trial_type = trial_type
        self.trial_cond = trial_cond
        self.description = description
        self.usebackup = usebackup
        self.file_prefix = "{}_{}_{}_{}".format(self.subjectID, self.trial_type, self.trial_cond, self.description)

        # Exo alternative modes
        self.continuousmode = continuousmode
        self.overridedefaultcurrentbounds = overridedefaultcurrentbounds

        # FilingCabinet
        self.filingcabinet = FilingCabinet(SUBJECT_DATA_PATH, self.subjectID)
        if self.usebackup:
            loadstatus = self.filingcabinet.loadbackup(self.file_prefix, rule="newest")
            print("Backup Load Status: {}".format("SUCCESS" if loadstatus else "FAILURE"))

        # Get IP for GRPC server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        self.myIP = s.getsockname()[0] + ":50055"
        print("myIP: {}".format(self.myIP))

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
            raise Exception("Invalid sides for devices: Check DEV_ID_TO_SIDE_DICT!")
    
    def run(self):
        """
        Initialize trial information
        Start All Threads
        """
        try:
            # # Initializing the Exo
            side_left, device_left, side_right, device_right = self.get_active_ports()

            # # Start device streaming and set gains:
            device_left.start_streaming(self.streamingfrequency)
            device_right.start_streaming(self.streamingfrequency)
            device_left.set_gains(DEFAULT_KP, DEFAULT_KI, DEFAULT_KD, 0, 0, DEFAULT_FF)
            device_right.set_gains(DEFAULT_KP, DEFAULT_KI, DEFAULT_KD, 0, 0, DEFAULT_FF)

            """Initialize Threads"""
            # Thread events
            self.quit_event = threading.Event()
            self.pause_event = threading.Event()
            self.log_event = threading.Event()
            self.quit_event.set()
            self.pause_event.clear() # Start with threads paused
            self.log_event.clear()
            self.startstamp = time.perf_counter() # Timesync logging between all threads

            # Thread 1/2: Left and right exoboots
            self.exothread_left = ExobootThread(side_left, device_left, self.startstamp, "exothread_left", True, self.quit_event, self.pause_event, self.log_event, self.overridedefaultcurrentbounds, ZERO_CURRENT, MAX_ALLOWABLE_CURRENT)
            self.exothread_right = ExobootThread(side_right, device_right, self.startstamp, "exothread_right", True,  self.quit_event, self.pause_event, self.log_event, self.overridedefaultcurrentbounds, ZERO_CURRENT, MAX_ALLOWABLE_CURRENT)
            self.exothread_left.start()
            self.exothread_right.start()

            # Thread 3: Gait State Estimator
            self.gse_thread = GaitStateEstimator(self.startstamp, device_left, device_right, self.exothread_left, self.exothread_right, daemon=True, continuousmode=self.continuousmode, quit_event=self.quit_event, pause_event=self.pause_event, log_event=self.log_event)
            self.gse_thread.start()

            # Thread 4: Exoboot Remote Control
            self.remote_thread = ExobootRemoteServerThread(self, self.startstamp, self.filingcabinet, name='exoboot_remote_thread', usebackup=False, daemon=True, quit_event=self.quit_event, pause_event=self.pause_event, log_event=self.log_event)
            self.remote_thread.set_target_IP(self.myIP)
            self.remote_thread.start()

            # Thread 5: Curses HUD
            # self.hud = HUDThread(self, "exohud_layout.json", napms=25, pause_event=self.pause_event, quit_event=self.quit_event)
            # self.hud.getwidget("si").settextline(0, "{}, {}, {}, {}".format(self.subjectID, self.trial_type, self.trial_cond, self.description))
            # self.hud.getwidget("ii").settextline(0, str(self.myIP))
            # self.hud.start()

            # LoggingNexus
            self.loggingnexus = LoggingNexus(self.subjectID, self.file_prefix, self.filingcabinet, self.exothread_left, self.exothread_right, self.gse_thread)

            # ~~~Main Loop~~~
            self.softrtloop = FlexibleSleeper(period=1/self.clockspeed)
            # self.pause_event.set()
            while self.quit_event.is_set():
                try:
                    # Print if no hud
                    try:
                        # if not self.hud.isrunning:
                        print("Peak Torque Left: {}\nPeak Torque Right: {}".format(self.loggingnexus.get(self.exothread_left.name, "peak_torque"), self.loggingnexus.get(self.exothread_right.name, "peak_torque")))
                        print("Case Temp Left: {}\nCase Temp Right: {}\n".format(self.loggingnexus.get(self.exothread_left.name, "temperature"), self.loggingnexus.get(self.exothread_right.name, "temperature")))
                        print("Freq Left: {}\nFreq Right: {}\n".format(self.loggingnexus.get(self.exothread_left.name, "thread_freq"), self.loggingnexus.get(self.exothread_right.name, "thread_freq")))
                    except:
                        pass

                    # Update HUD
                    # try:
                    #     exostate_text = "Running" if self.pause_event.is_set() else "Paused"
                    #     self.hud.getwidget("ls").settextline(0, exostate_text)
                    #     self.hud.getwidget("rs").settextline(0, exostate_text)
                    #     self.hud.getwidget("lpt").settextline(0, str(self.loggingnexus.get(self.exothread_left.name, "peak_torque")))
                    #     self.hud.getwidget("rpt").settextline(0, str(self.loggingnexus.get(self.exothread_right.name, "peak_torque")))
                    #     self.hud.getwidget("lct").settextline(0, str(self.loggingnexus.get(self.exothread_left.name, "temperature")))
                    #     self.hud.getwidget("rct").settextline(0, str(self.loggingnexus.get(self.exothread_right.name, "temperature")))
                    #     self.hud.getwidget("lcs").settextline(0, "{:0.2f}".format(self.loggingnexus.get(self.exothread_left.name, "thread_freq")))
                    #     self.hud.getwidget("rcs").settextline(0, "{:0.2f}".format(self.loggingnexus.get(self.exothread_right.name, "thread_freq")))

                    #     self.hud.getwidget("batv").settextline(0, str(self.loggingnexus.get(self.exothread_right.name, "battery_voltage")))
                    #     self.hud.getwidget("bati").settextline(0, str(self.loggingnexus.get(self.exothread_right.name, "battery_current")))

                    #     self.hud.getwidget("bert").settextline(0, "IDK")
                    #     self.hud.getwidget("vicon").settextline(0, "TBI")
                    # except Exception as e:
                    #     print("Exception: ", e)

                    # Log data. Obeys log_event
                    if self.log_event.is_set():
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
            time.sleep(0.25)
            self.quit_event.clear()

            # Stop motors and close device streams
            self.exothread_left.flexdevice.stop_motor() 
            self.exothread_right.flexdevice.stop_motor()

            self.exothread_left.flexdevice.close()
            self.exothread_right.flexdevice.close()
            print("Goodbye")


if __name__ == "__main__":
    assert len(sys.argv) - 1 == 5
    _, subjectID, trial_type, trial_cond, description, usebackup= sys.argv

    # Validate args
    Validator(subjectID, trial_type, trial_cond, description, usebackup)

    # Set controller kwargs
    controller_kwargs = {"subjectID": subjectID,
                         "trial_type": trial_type.upper(),
                         "trial_cond": trial_cond.upper(),
                         "description": description,
                         "usebackup": usebackup in ["true", "True", "1", "yes", "Yes"]}

    # Allow GSE to alter peak torque during strides
    controller_kwargs["continuousmode"] = controller_kwargs["trial_type"] == "PREF" and controller_kwargs["trial_cond"] in ["SLIDER", "DIAL"]

    # Use alternate upper and lower current bounds
    controller_kwargs["overridedefaultcurrentbounds"] = controller_kwargs["trial_type"] == "VICKREY" and controller_kwargs["trial_cond"] in ["WNE", "NPO"]

    MainControllerWrapper(**controller_kwargs).run()
