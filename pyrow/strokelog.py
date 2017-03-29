#!/usr/bin/env python
#Copyright (c) 2011, Sam Gambrell
#Licensed under the Simplified BSD License.

#This is an example file to show how to make use of pyrow
#Have the rowing machine on and plugged into the computer before starting the program
#The program will record Time, Distance, SPM, Pace, and Force Data for each
#stroke and save it to 'workout.csv'

#NOTE: This code has not been thoroughly tested and may not function as advertised.
#Please report and findings to the author so that they may be addressed in a stable release.

# To Do
# Elapsed time decreases in time based intervals

from . import pyrow, find
import time
import logging

def main():
    #Connecting to erg
    ergs = list(find())
    if len(ergs) == 0:
        exit("No ergs found.")

    erg = pyrow(ergs[0])
    logging.info("Connected to erg.")

    #Open and prepare file
    filename = 'workouts/rowsberrypi_'+time.strftime("%Y%m%d-%H%M%S")+'.csv'
    write_file = open(filename, 'w')
    write_file.write(' lapIdx,Timestamp (sec), ElapsedTime (sec), Horizontal (meters), Cadence (stokes/min), Stroke500mPace (sec/500m),')
    write_file.write(' HRCur (bpm), AverageDriveForce (lbs), PeakDriveForce (lbs), DriveLength (meters), DriveTime (ms), StrokeRecoveryTime (ms), WorkPerStroke (J), WorkoutState, Force Plot\n')

    #Loop until workout has begun
    workout = erg.get_workout()


    workoutstateactive = [1,2,3,4,5,6,7,8,9]
    workoutstateidle = [0,10,11,12,13]

    workoutstatewait = [2,6,7,8,9]
    workoutstatestroke = [1,3,4,5]
    
    logging.info("Waiting for workout to start.")
    while workout['state'] in workoutstateidle:
        time.sleep(1)
        workout = erg.get_workout()
    logging.info( "Workout has begun.")

    #Loop until workout ends
    while workout['state'] in workoutstateactive:

        forceplot = erg.get_force_plot()
        #Loop while waiting for drive
        while forceplot['strokestate'] not in workoutstatewait and workout['state'] in workoutstatestroke:
            #ToDo: sleep?
            forceplot = erg.get_force_plot()
            workout = erg.get_workout()

        #Record force data during the drive
        force = forceplot['forceplot'] #start of pull (when strokestate first changed to 2)
        monitor = erg.get_monitor(extrametrics=True) #get monitor data for start of stroke
        #Loop during drive
        while forceplot['strokestate'] == 2:
            #ToDo: sleep?
            forceplot = erg.get_force_plot()
            force.extend(forceplot['forceplot'])

        forceplot = erg.get_force_plot()
        force.extend(forceplot['forceplot'])


        #Write data to write_file
        workoutdata = str(monitor['intervalcount'])+","
        workoutdata += str(time.time())+","+str(monitor['time'])
        workoutdata += "," + str(monitor['distance']) + "," 
        workoutdata += str(monitor['spm']) + "," + str(monitor['pace']) + ","

        workoutdata += str(monitor['heartrate'])+","
        workoutdata += str(monitor['strokeaverageforce'])+","
        workoutdata += str(monitor['strokepeakforce'])+","
        workoutdata += str(monitor['strokelength'])+","
        workoutdata += str(monitor['strokedrivetime'])+","
        workoutdata += str(monitor['strokerecoverytime'])+","
        workoutdata += str(monitor['workperstroke'])+","
        workoutdata += str(workout['state'])+","
        
        forcedata = ",".join([str(f) for f in force])
        
        write_file.write(workoutdata + forcedata + '\n')

        #Get workout conditions
        workout = erg.get_workout()

    write_file.close()
    logging.info("Workout has ended.")
