#!/usr/bin/env python
#Copyright (c) 2011, Sam Gambrell
#Licensed under the Simplified BSD License.

#This is an example file to show how to make use of pyrow
# The code waits until an erg is connected.
# Then it continues to record individual workouts until a keyboard interrupt

#NOTE: This code has not been thoroughly tested and may not function as advertised.
#Please report and findings to the author so that they may be addressed in a stable release.

# To Do
# Elapsed time decreases in time based intervals

from YamJam import yamjam
from . import pyrow, find
import time
import logging
from usb.core import USBError

workoutstateactive = [1,2,3,4,5,6,7,8,9]
workoutstateidle = [0,10,11,12,13]

workoutstatewait = [2,6,7,8,9]
workoutstatestroke = [1,3,4,5]

try:
    CFG = yamjam()['pyrow']
    email_host = CFG['email_host']
    email_port = CFG['email_port']
    email_use_tls = CFG['email_use_tls']
    email_host_user = CFG['email_host_user']
    email_host_password = CFG['email_host_password']
    email_fromaddress = CFG['email_fromaddress']
    email_recipients = CFG['email_recipients']
except KeyError:
    email_host = ''
    email_port = ''
    email_use_tls = ''
    email_host_user = ''
    email_host_password = ''
    email_fromaddress = ''
    email_recipients = ''
    
import smtplib, os, re, sys, glob, string, datetime
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders

    
def send_email(filename):
    msgsubject = 'Workout from Rowsberry Pi'
    htmlmsgtext = """This is a workout recorded with Rowsberry Pi</br>
                     Yup. Yup. Yup.</br>"""
    msgtext = htmlmsgtext.replace('<b>','').replace('</b>','').replace('<br>',"\r").replace('</br>',"\r").replace('<br/>',"\r").replace('</a>','')
    msgtext = re.sub('<.*?>','',msgtext)

    msg = MIMEMultipart()
    msg.preamble = 'This is a multi-part message in MIME format.\n'
    msg.epilogue = ''

    body = MIMEMultipart('alternative')
    body.attach(MIMEText(msgtext))
    body.attach(MIMEText(htmlmsgtext, 'html'))
    msg.attach(body)

    part = MIMEBase('application', "octet-stream")
    part.set_payload( open(filename,"rb").read() )
    Encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(filename))
    msg.attach(part)

    msg.add_header('From', email_fromaddress)
    msg.add_header('To',email_recipients)
    msg.add_header('Subject', msgsubject)

    # The actual email sendy bits
    server = smtplib.SMTP('%s:%s' % (email_host,email_port))
    server.set_debuglevel(True)
    if email_use_tls:
        server.starttls()
        server.login(email_host_user,email_host_password)

    if not isinstance(email_recipients,list):
        email_recipients = [email_recipients]
    server.sendmail(msg['From'], email_recipients, msg.as_string())

    server.quit() #bye bye

    
def strokelog(erg,workout):
    #Open and prepare file
    filename = 'workouts/rowsberrypi_'+time.strftime("%Y%m%d-%H%M%S")+'.csv'
    print "starting to log to file "+filename
    write_file = open(filename, 'w')
    write_file.write(' lapIdx,Timestamp (sec), ElapsedTime (sec), Horizontal (meters), Cadence (stokes/min), Stroke500mPace (sec/500m),')
    write_file.write(' HRCur (bpm), AverageDriveForce (lbs), PeakDriveForce (lbs), DriveLength (meters), DriveTime (ms), StrokeRecoveryTime (ms), WorkPerStroke (J), WorkoutState, Force Plot\n')

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
        while forceplot['strokestate'] in workoutstatewait:
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

    print "closing file"
    write_file.close()
    return write_file.name

def main():
    #Connecting to erg
    try:
        while True:
            l = 0
            while l == 0:
                ergs = list(find())
                l = len(ergs)
                time.sleep(1)
                
            erg = pyrow(ergs[0])
            logging.info("Connected to erg.")


            #Loop until workout has begun
            workout = erg.get_workout()

            try:
                while True:
                    logging.info("Waiting for workout to start.")
                    while workout['state'] in workoutstateidle:
                        time.sleep(1)
                        workout = erg.get_workout()

                    logging.info("Workout has begun.")
                    filename = strokelog(erg,workout)
                    logging.info("Written to file "+filename)
                    logging.info("Workout has ended.")
                    # email sending
                    if email_host != '':
                        print "sending email"
                        send_email(filename)
                    workout = erg.get_workout()
            except KeyboardInterrupt:
                logging.info("Workout interrupted.")
    except USBError:
        logging.info("USB Erg Disconnected")
