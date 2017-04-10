import logging
import os
from os.path import expanduser
import re
import smtplib
import time
from email.encoders import encode_base64
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from pyrow.performance_monitor import PerformanceMonitor
from usb.core import USBError
from yaml import load

logging.basicConfig(level=logging.DEBUG)

WORKOUT_STATE_ACTIVE = [1, 2, 3, 4, 5, 6, 7, 8, 9]
WORKOUT_STATE_IDLE = [0, 10, 11, 12, 13]

WORKOUT_STATE_WAIT = [2, 6, 7, 8, 9]
WORKOUT_STATE_STROKE = [1, 3, 4, 5]


def load_config():
    try:
        config_file_path = os.path.abspath(os.path.join(expanduser('~'), 'config.yaml'))
        with open(config_file_path, 'r') as config_file:
            return load(config_file)['rowsberrypi']
    except KeyError:
        logging.error('Unable to load email config.')
        return None


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

    config = load_config()

    msg.add_header('From', config['email_from_address'])
    msg.add_header('To', config['email_recipients'])
    msg.add_header('Subject', msgsubject)

    # The actual email sendy bits
    server = smtplib.SMTP('%s:%s' % (config['email_host'], config['email_port']))
    server.set_debuglevel(True)
    if config['email_use_tls']:
        server.starttls()
        server.login(config['email_host_user'], config['email_host_password'])

    email_recipients = config['email_recipients']
    if not isinstance(email_recipients, list):
        email_recipients = [email_recipients]
    server.sendmail(msg['From'], email_recipients, msg.as_string())

    server.quit()  # bye bye


def stroke_log(erg, workout):
    # Open and prepare file
    filename = os.path.abspath(
        os.path.join(
            expanduser('~'),
            'workouts/rowsberrypi_' + time.strftime("%Y%m%d-%H%M%S") + '.csv'
        )
    )
    logging.debug('starting to log to file %s', filename)
    write_file = open(filename, 'w')

    write_file.write(
        ' lapIdx,'
        'Timestamp (sec),'
        ' ElapsedTime (sec),'
        ' Horizontal (meters),'
        ' Cadence (stokes/min),'
        ' Stroke500mPace (sec/500m),'
        ' HRCur (bpm),'
        ' AverageDriveForce (lbs),'
        ' PeakDriveForce (lbs),'
        ' DriveLength (meters),'
        ' DriveTime (ms),'
        ' StrokeRecoveryTime (ms),'
        ' WorkPerStroke (J),'
        ' WorkoutState,'
        ' Force Plot\n'
    )

    # Loop until workout ends
    while workout.get_status() in WORKOUT_STATE_ACTIVE:

        force_plot = erg.get_force_plot()
        # Loop while waiting for drive
        while force_plot.get_stroke_state() not in WORKOUT_STATE_WAIT and \
                workout.get_status() in WORKOUT_STATE_STROKE:
            # ToDo: sleep?
            force_plot = erg.get_force_plot()
            workout = erg.get_workout()

        # Record force data during the drive
        force = force_plot.get_force_plot()  # start of pull (when strokestate first changed to 2)
        monitor = erg.get_monitor(extrametrics=True)  # get monitor data for start of stroke
        # Loop during drive
        while force_plot.get_stroke_state() in WORKOUT_STATE_WAIT:
            # ToDo: sleep?
            force_plot = erg.get_force_plot()
            force.extend(force_plot.get_force_plot())

        force_plot = erg.get_force_plot()
        force.extend(force_plot.get_force_plot())

        # Write data to write_file
        workout = [
            monitor.get_workout_int_count(),
            time.time(),
            monitor.get_time(),
            monitor.get_distance(),
            monitor.get_spm(),
            monitor.get_pace_500(),
            monitor.get_heartrate(),
            monitor.get_stroke_average_force(),
            monitor.get_stroke_peak_force(),
            monitor.get_stroke_length(),
            monitor.get_stroke_drive_time(),
            monitor.get_stroke_recovery_time(),
            monitor.get_work_per_stroke(),
            workout.get_workout_state()
        ]

        force_data = ",".join([str(f) for f in force])
        workout_data = ','.join([str(w) for w in workout])

        write_file.write(workout_data + force_data + '\n')

        # Get workout conditions
        workout = erg.get_workout()

    logging.debug("Closing file.")
    write_file.close()
    return write_file.name


def main():
    # Connecting to erg
    try:
        while True:
            num_ergs = 0
            while num_ergs == 0:
                ergs = PerformanceMonitor.find()
                num_ergs = len(ergs)
                time.sleep(1)

            erg = PerformanceMonitor(ergs[0])
            logging.info("Connected to erg.")

            # Loop until workout has begun
            workout = erg.get_workout()

            try:
                while True:
                    logging.info("Waiting for workout to start.")
                    while workout.get_workout_state() in WORKOUT_STATE_IDLE:
                        time.sleep(1)
                        workout = erg.get_workout()

                    logging.info("Workout has begun.")
                    filename = stroke_log(erg, workout)
                    logging.info("Written to file " + filename)
                    logging.info("Workout has ended.")
                    # email sending
                    if load_config() is not None:
                        logging.info("Sending email.")
                        send_email(filename)
                    workout = erg.get_workout()
            except KeyboardInterrupt:
                logging.info("Workout interrupted.")
    except USBError:
        logging.info("USB Erg Disconnected.")


if __name__ == '__main__':
    main()
