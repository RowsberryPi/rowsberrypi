import logging
import os
import re
import smtplib
import time
from email.encoders import encode_base64
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from YamJam import yamjam
from pyrow.performance_monitor import PerformanceMonitor
from usb.core import USBError

logging.basicConfig(level=logging.DEBUG)

workoutstateactive = [1, 2, 3, 4, 5, 6, 7, 8, 9]
workoutstateidle = [0, 10, 11, 12, 13]

workoutstatewait = [2, 6, 7, 8, 9]
workoutstatestroke = [1, 3, 4, 5]

try:
    CFG = yamjam()['rowsberrypi']
    email_host = CFG['email_host']
    email_port = CFG['email_port']
    email_use_tls = CFG['email_use_tls']
    email_host_user = CFG['email_host_user']
    email_host_password = CFG['email_host_password']
    email_from_address = CFG['email_from_address']
    email_recipients = CFG['email_recipients']
except KeyError:
    email_host = ''
    email_port = ''
    email_use_tls = ''
    email_host_user = ''
    email_host_password = ''
    email_from_address = ''
    email_recipients = ''


def send_email(filename):
    msgsubject = 'Workout from Rowsberry Pi'
    htmlmsgtext = """This is a workout recorded with Rowsberry Pi</br>
                     Yup. Yup. Yup.</br>"""
    msgtext = htmlmsgtext.replace('<b>', '').replace('</b>', '').replace('<br>', "\r").replace(
        '</br>', "\r").replace('<br/>', "\r").replace('</a>', '')
    msgtext = re.sub('<.*?>', '', msgtext)

    msg = MIMEMultipart()
    msg.preamble = 'This is a multi-part message in MIME format.\n'
    msg.epilogue = ''

    body = MIMEMultipart('alternative')
    body.attach(MIMEText(msgtext))
    body.attach(MIMEText(htmlmsgtext, 'html'))
    msg.attach(body)

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(open(filename, 'rb').read())
    encode_base64(part)
    part.add_header('Content-Disposition',
                    'attachment; filename="{}"'.format(os.path.basename(filename)))
    msg.attach(part)

    msg.add_header('From', email_from_address)
    msg.add_header('To', email_recipients)
    msg.add_header('Subject', msgsubject)

    # The actual email sendy bits
    server = smtplib.SMTP('%s:%s' % (email_host, email_port))
    server.set_debuglevel(True)
    if email_use_tls:
        server.starttls()
        server.login(email_host_user, email_host_password)

    if not isinstance(email_recipients, list):
        email_recipients = [email_recipients]
    server.sendmail(msg['From'], email_recipients, msg.as_string())

    server.quit()  # bye bye


def stroke_log(erg, workout):
    # Open and prepare file
    filename = 'workouts/rowsberrypi_' + time.strftime("%Y%m%d-%H%M%S") + '.csv'
    logging.debug('starting to log to file %s', filename)
    write_file = open(filename, 'w')
    write_file.write(
        'lapIdx,'
        'Timestamp (sec),'
        'ElapsedTime (sec),'
        'Horizontal (meters),'
        'Cadence (stokes/min),'
        'Stroke500mPace (sec/500m),'
        'HRCur (bpm),'
        'AverageDriveForce (lbs),'
        'PeakDriveForce (lbs),'
        'DriveLength (meters),'
        'DriveTime (ms),'
        'StrokeRecoveryTime (ms),'
        'WorkPerStroke (J),'
        'WorkoutState,'
        'Force Plot\n'
    )

    # Loop until workout ends
    while workout.get_status() in workoutstateactive:

        forceplot = erg.get_force_plot()
        # Loop while waiting for drive
        while forceplot.get_stroke_state() not in workoutstatewait and \
                        workout.get_status() in workoutstatestroke:
            # ToDo: sleep?
            forceplot = erg.get_force_plot()
            workout = erg.get_workout()

        # Record force data during the drive
        force = forceplot['forceplot']  # start of pull (when strokestate first changed to 2)
        monitor = erg.get_monitor(extrametrics=True)  # get monitor data for start of stroke
        # Loop during drive
        while forceplot['strokestate'] in workoutstatewait:
            # ToDo: sleep?
            forceplot = erg.get_force_plot()
            force.extend(forceplot['forceplot'])

        forceplot = erg.get_force_plot()
        force.extend(forceplot.get_force_plot())

        # Write data to write_file
        workoutdata = [
            monitor.get_workout_int_count(),
            time.time(),
            monitor.get_time(),
            monitor['distance'],
            monitor['spm'],
            monitor['pace'],
            monitor['heartrate'],
            monitor['strokeaverageforce'],
            monitor['strokepeakforce'],
            monitor['strokelength'],
            monitor['strokedrivetime'],
            monitor['strokerecoverytime'],
            monitor['workperstroke'],
            workout['state']
        ]

        force_data = ",".join([str(f) for f in force])

        write_file.write(workoutdata + force_data + '\n')

        # Get workout conditions
        workout = erg.get_workout()

    logging.debug("Closing file.")
    write_file.close()
    return write_file.name


def main():
    # Connecting to erg
    try:
        while True:
            l = 0
            while l == 0:
                ergs = list(PerformanceMonitor.find())
                l = len(ergs)
                time.sleep(1)

            erg = PerformanceMonitor(ergs[0])
            logging.info("Connected to erg.")

            # Loop until workout has begun
            workout = erg.get_workout()

            try:
                while True:
                    logging.info("Waiting for workout to start.")
                    while workout['state'] in workoutstateidle:
                        time.sleep(1)
                        workout = erg.get_workout()

                    logging.info("Workout has begun.")
                    filename = stroke_log(erg, workout)
                    logging.info("Written to file " + filename)
                    logging.info("Workout has ended.")
                    # email sending
                    if email_host != '':
                        logging.info("Sending email.")
                        send_email(filename)
                    workout = erg.get_workout()
            except KeyboardInterrupt:
                logging.info("Workout interrupted.")
    except USBError:
        logging.info("USB Erg Disconnected.")
