import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from email_utils import send_email

load_dotenv()

scheduler = BackgroundScheduler()
scheduler.start()  # Make sure the scheduler is running

def schedule_reminder(recipient_email, subject, body, send_time):
    # Schedule a reminder using only positional arguments and confirm when sent
    def send_and_confirm():
        send_email(recipient_email, subject, body)
        print(f"Reminder sent to {recipient_email} with subject '{subject}' at {send_time}")
    scheduler.add_job(
        send_and_confirm,
        'date',
        run_date=send_time
    )