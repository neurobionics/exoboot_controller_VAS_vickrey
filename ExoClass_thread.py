# Description:
# This script creates an ExoObject Class to pair with the main VAS controller python file for the VAS Vickrey Protocol.
# It is responsible for initializing the exoskeletons, calibrating them, and running methods critical to the main control loop.
#
# Original template created by: Emily Bywater
# Modified for VAS Vickrey protocol by: Nundini Rawal
# Date: 06/13/2024

import os, csv, time, copy, threading
import numpy as np
from typing import Type, Tuple

from constants import DEV_ID_TO_ANK_ENC_SIGN_DICT, DEV_ID_TO_MOTOR_SIGN_DICT, TR_COEFS_PREFIX, EXOTHREAD_FIELDS
from constants import MAX_ALLOWABLE_CURRENT, BIAS_CURRENT, EFFICIENCY, Kt, ENC_CLICKS_TO_DEG, SPINE_TIMING_PARAMS_DICT, GYRO_GAIN, ACCEL_GAIN

from thermal import ThermalModel
from BaseExoThread import BaseThread
from utils import MovingAverageFilter, TrueAfter
from SoftRTloop import FlexibleSleeper
from AssistanceGenerator_new import AssistanceGenerator
from TransmissionRatioGenerator import TransmissionRatioGenerator


class ExobootThread(BaseThread):
    def __init__(self, side, flexdevice, startstamp, name='exobootthread', daemon=True, pause_event=Type[threading.Event], quit_event=Type[threading.Event]):
        """
        TODO make overview
        """
        super().__init__(name=name, daemon=daemon, pause_event=pause_event, quit_event=quit_event)
        # Necessary Inputs for Exo Class
        self.side = side
        self.flexdevice = flexdevice # In ref to flexsea Device
        
        # Motor and ankle signs
        """TEST TO ENSURE CORRECT DIRECTIONS BEFORE RUNNING IN FULL"""
        self.motor_sign = DEV_ID_TO_MOTOR_SIGN_DICT[self.flexdevice.id]
        self.ank_enc_sign = DEV_ID_TO_ANK_ENC_SIGN_DICT[self.flexdevice.id]

        # Zeroes from homing procedure
        self.motor_angle_zero = 0
        self.ankle_angle_zero = 0

        # Set Transmission Ratio and Motor-Angle Curve Coefficients	from pre-performed calibration
        self.coefs_filename = "{}{}.csv".format(TR_COEFS_PREFIX, self.side)
        self.tr_gen = TransmissionRatioGenerator(self.coefs_filename, max_allowable_angle=180, min_allowable_angle=0, min_allowable_TR=10, granularity=10000)
        
        # Instantiate AssistanceGenerator (DOES NOT HAVE PROFILE ON INITIALIZATION)
        self.assistance_generator = AssistanceGenerator()
        
        # Instantiate Thermal Model and specify thermal limits
        self.thermalModel = ThermalModel(temp_limit_windings=100,soft_border_C_windings=10,temp_limit_case=70,soft_border_C_case=10)
        self.case_temperature = 0
        self.winding_temperature = 0
        self.max_case_temperature = 80
        self.max_winding_temperature = 115
        self.exo_safety_shutoff_flag = False

        # Peak torque set over exoboot remote
        self.peak_torque:float = 0

        # State estimate set by GSE
        self.HS = time.perf_counter()
        self.current_time = 0
        self.stride_period = 1.0
        self.in_swing = False

        # Logging fields
        self.fields = EXOTHREAD_FIELDS
        self.data_dict = dict.fromkeys(self.fields)

        # LoggingNexus
        self.startstamp = startstamp
        self.loggingnexus = None        

    def getval(self, what):
        """
        Return value from data_dict given what
        """
        return self.data_dict[what]

    def spool_belt(self):
        self.flexdevice.command_motor_current(self.motor_sign * BIAS_CURRENT)
        # self.fxs.send_motor_command(self.flexdevice, self.motor_sign*BIAS_CURRENT)
        time.sleep(0.5)
        print("Belt spooled for: ", self.flexdevice.id)
        
    def zeroProcedure(self):
        """
        Collects standing angle and is used to zero all future collected angles
        
        Subject must stand sufficiently still (>95%) in order to register the angle as the zero
        """
        filename = os.path.join('Autogen_zeroing_coeff_files','offsets_Exo{}.csv'.format(self.side.capitalize()))

        # conduct zeroing/homing procedure and log offsets
        print("Starting ankle zeroing/homing procedure for: \n", self.side)
        
        # ismoving thresholds
        motor_vel_threshold = 100
        ankle_vel_threshold = 1

        # Motor current command
        pullCurrent = 1000  # mA
        holdCurrent = pullCurrent * self.motor_sign
        holdingCurrent = True

        filt_size = 2500
        isafter = TrueAfter(after=filt_size)
        ismoving = MovingAverageFilter(initial_value=0, size=filt_size)
        motor_angles_history = MovingAverageFilter(initial_value=0, size=filt_size)
        ankle_angles_history = MovingAverageFilter(initial_value=0, size=filt_size)

        self.flexdevice.command_motor_current(holdCurrent)
        while holdingCurrent:
            # Get angles from direct read
            data = self.flexdevice.read()
            current_ank_angle = self.ank_enc_sign * data['ank_ang'] * ENC_CLICKS_TO_DEG
            current_mot_angle = self.motor_sign * data['mot_ang'] * ENC_CLICKS_TO_DEG
            current_ank_vel = data['ank_vel'] / 10
            current_mot_vel = data['mot_vel']

            # Update ismoving filter with moving/not moving
            ismoving.update(1) if abs(current_mot_vel) > motor_vel_threshold or abs(current_ank_vel) > ankle_vel_threshold else ismoving.update(0)

            # Update history
            motor_angles_history.update(current_mot_angle)
            ankle_angles_history.update(current_ank_angle)

            # If no movement 95% of the time and after grace period
            if ismoving.average() > 0.95 and isafter.isafter():
                self.motor_angle_zero = motor_angles_history.average()
                self.ankle_angle_zero = ankle_angles_history.average()
                holdingCurrent = False

            # Post updates
            isafter.step()

        # Stop hold current command
        self.flexdevice.command_motor_current(0)

        # Finished collecting zeroes
        print("{} motor_zero: {} deg".format(self.side, self.motor_angle_zero))
        print("{} anklezero: {} deg".format(self.side, self.ankle_angle_zero))
        with open(filename, "w") as file:
            writer = csv.writer(file, delimiter=",")
            writer.writerow([self.motor_angle_zero, self.ankle_angle_zero])
            file.close()

        # Send 0 current
        self.flexdevice.command_motor_current(0)

    def read_sensors(self):
        data = self.flexdevice.read() #(allData=True)

        # Temp and Time
        self.data_dict['state_time'] = data['state_time'] / 1000 #converting to seconds
        self.data_dict['temperature'] = data['temperature']

        # Accelerometer
        # Note based on the MPU reading script it says the accel = raw_accel/accel_sace * 9.80605 -- so if the value of accel returned is multiplyed  by the gravity term then the accel_scale for 4g is 8192
        self.data_dict['accel_x'] = data['accelx'] * ACCEL_GAIN  #This is in the walking direction {i.e the rotational axis of the frontal plane}
        self.data_dict['accel_y'] = -1 * data['accely'] * ACCEL_GAIN # This is in the vertical direction {i.e the rotational axis of the transverse plane}
        self.data_dict['accel_z'] = data['accelz'] * ACCEL_GAIN # This is the rotational axis of the sagital plane

        # Gyro
        # Note based on the MPU reading script it says the gyro = radians(raw_gyro/gyroscale) for the gyrorange of 1000DPS the gyroscale is 32.8
        self.data_dict['gyro_x'] = -1 * data['gyrox'] * GYRO_GAIN
        self.data_dict['gyro_y'] = data['gyroy'] * GYRO_GAIN
        # Remove -1 for EB-51
        self.data_dict['gyro_z'] = data['gyroz'] * GYRO_GAIN

        # Ankle Encoder
        ankle_angle = (self.ank_enc_sign * data['ank_ang'] * ENC_CLICKS_TO_DEG) #- self.ankle_angle_zero
        self.data_dict['ankle_angle'] = ankle_angle
        self.data_dict['ankle_velocity'] = data['ank_vel'] / 10

        # Motor Encoder
        self.data_dict['motor_angle'] = self.motor_sign * data['mot_ang'] * ENC_CLICKS_TO_DEG
        self.data_dict['motor_velocity'] = data['mot_vel']

        # TODO clamp motor current to not get bad readings
        motor_current = data['mot_cur']
        self.data_dict['motor_current'] = motor_current
        self.data_dict['motor_voltage'] = data['mot_volt']
        self.data_dict['battery_voltage'] = data['batt_volt']
        self.data_dict['battery_current'] = data['batt_curr']

        ## ====Calculate Delivered Ankle Torque from Measured Current====
        actual_mot_torque_left = motor_current * Kt / 1000 * self.motor_sign # Nm
        N = self.tr_gen.get_TR(ankle_angle)
        self.data_dict['N'] = N
        self.data_dict['act_ank_torque'] = N * EFFICIENCY * actual_mot_torque_left

    def torque_2_current(self, torque, N) -> int:
        """
        Calculate equivalent current command given torque and TR
        Returns current (int) in mA
        """ 
        des_current = torque / (N * EFFICIENCY * Kt)   # output in mA
        
        return int(des_current)
    
    def thermal_safety_checker(self):
        """Ensure that winding temperature is below 100°C (115°C is the hard limit).
        Ensure that case temperature is below 75°C (80°C is the hard limit).
        Uses Jianpings model to project forward the measured temperature from Dephy ActPack.
        
        Returns:
        exo_safety_shutoff_flag (bool): flag that indicates if the exo has exceeded thermal limits. 
        Used to toggle whether the device should be shut off.
        """
            
        # measured temp by Dephy from the actpack is the case temperature
        measured_temp = self.getval('temperature')
        motor_current = self.getval('motor_current')
        freq = self.getval('thread_freq')
            
        # determine modeled case & winding temp
        self.thermalModel.T_c = measured_temp
        self.thermalModel.update(dt=(1 / freq), motor_current=motor_current)
        winding_temperature = self.thermalModel.T_w

        self.data_dict['winding_temp'] = winding_temperature

        # Shut off exo if thermal limits breached
        if measured_temp >= self.max_case_temperature:
            # self.exo_safety_shutoff_flag = True
            print("Case Temperature has exceed 75°C soft limit. Exiting Gracefully")
        if winding_temperature >= self.max_winding_temperature:
            # self.exo_safety_shutoff_flag = True
            print("Winding Temperature has exceed 115°C soft limit. Exiting Gracefully")

        # using Jianping's thermal model to project winding & case temperature
        # using the updated case temperature and setting shut-off flag
        # self.case_temperature = measured_temp
        # exo_safety_shutoff_flag = self.get_modelled_temps(motor_current)
    
    def set_state_estimate(self, HS, stride_period, peak_torque, in_swing):
        """
        Sets gait estimate to track stride

        Called by GSE periodically when it has new estimate/ HS/inswing event
        """
        self.HS = HS
        self.stride_period = stride_period
        self.peak_torque = peak_torque
        self.in_swing = in_swing

    def log_state_estimate(self):
        self.data_dict['HS'] = self.HS
        self.data_dict['current_time'] = self.current_time
        self.data_dict['stride_period'] = self.stride_period
        self.data_dict['peak_torque'] = self.peak_torque
        self.data_dict['in_swing'] = self.in_swing

    # Threading run() functions
    def on_pre_run(self):
        """
        Runs once before main loop
        """
        # Exoboot spooling/zeroing routine
        self.spool_belt()
        self.zeroProcedure()

        # Load profile timings and create generic profile
        self.assistance_generator.load_timings(SPINE_TIMING_PARAMS_DICT)
        self.assistance_generator.set_my_generic_profile(granularity=10000)

        # Period Tracker setup
        self.period_tracker = MovingAverageFilter(size=500)
        self.prev_end_time = time.perf_counter()

        # Soft real time loop
        loop_freq = 500 # Hz
        self.softRTloop = FlexibleSleeper(period=1/loop_freq)

    def on_pre_pause(self):
        """
        Runs once when paused
        """
        # Send bias current
        self.flexdevice.command_motor_current(self.motor_sign * BIAS_CURRENT)
        
        print("{} is paused".format(self.name))

    def pre_iterate(self):
        """
        Set Startstamp and read sensor data
        """
        # Set starting time stamp
        self.data_dict['pitime'] = time.perf_counter() - self.startstamp

        # Read sensors
        self.read_sensors()
        self.log_state_estimate()

    def iterate(self):
        """
        Sends motor commands based on current_time estimate

        Runs in main loop when not paused
        """
        self.current_time = time.perf_counter() - self.HS

        # Acquire Torque command based on gait estimate            
        torque_command = self.assistance_generator.generic_torque_generator(self.current_time, self.stride_period, self.peak_torque, self.in_swing)
        self.data_dict['torque_command'] = torque_command

        # Convert torque to current
        current_command = self.torque_2_current(torque_command, self.getval('N'))
        self.data_dict['current_command'] = current_command
        
        # Clamp current between bias and max allowable current
        vetted_current = max(min(current_command, MAX_ALLOWABLE_CURRENT), BIAS_CURRENT)
        
        # Shut off exo if thermal limits breached
        if self.exo_safety_shutoff_flag:
            print("Safety shutoff flag: quit_event cleared")
            self.flexdevice.command_motor_current(0)
            self.quit_event.clear()
        else:
            self.flexdevice.command_motor_current(self.motor_sign * vetted_current)

    def post_iterate(self):
        """
        Loop period tracking and soft real time pause
        """
        # Update Period Tracker and config
        end_time = time.perf_counter()
        self.period_tracker.update(end_time - self.prev_end_time)
        self.prev_end_time = end_time
        my_freq = 1/self.period_tracker.average()
        self.data_dict['thread_freq'] = my_freq

        # Perform thermal safety check on actpack
        self.thermal_safety_checker()

        # Send GSE data for logging
        if self.loggingnexus and self.pause_event.is_set():
            self.loggingnexus.append(self.name, self.data_dict)

        # soft real-time loop
        self.softRTloop.pause()