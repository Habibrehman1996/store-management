import os
from twilio.rest import Client
import aiosmtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

async def send_whatsapp_notification(message: str):
    logger.debug("Starting WhatsApp notification process")
    try:
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_PHONE_NUMBER")
        to_number = os.getenv("ADMIN_PHONE_NUMBER")
        logger.debug(f"Twilio config: SID={sid[:4] + '...' if sid else None}, From={from_number}, To={to_number}")
        if not all([sid, token, from_number, to_number]):
            logger.error("Missing Twilio configuration variables")
            raise ValueError("Missing Twilio configuration")
        
        client = Client(sid, token)
        twilio_message = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number
        )
        logger.info(f"WhatsApp message sent: SID {twilio_message.sid}")
    except Exception as e:
        logger.error(f"WhatsApp notification failed: {str(e)}", exc_info=True)
        raise

async def send_email_notification(subject: str, body: str, recipient_email: str = None):
    logger.debug("Starting email notification process")
    try:
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = os.getenv("SMTP_PORT")
        smtp_user = os.getenv("SMTP_USERNAME")
        smtp_pass = os.getenv("SMTP_PASSWORD")
        logger.debug(f"SMTP config: Host={smtp_host}, Port={smtp_port}, User={smtp_user}")
        if not all([smtp_host, smtp_port, smtp_user, smtp_pass]):
            logger.error("Missing SMTP configuration variables")
            raise ValueError("Missing SMTP configuration")
        
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = recipient_email if recipient_email else smtp_user
        logger.debug(f"Sending email to {msg['To']} with subject {subject}")
        
        async with aiosmtplib.SMTP(
            hostname=smtp_host,
            port=int(smtp_port),
            username=smtp_user,
            password=smtp_pass,
            use_tls=False,
            start_tls=True
        ) as smtp:
            await smtp.send_message(msg)
        logger.info("Email sent successfully")
    except Exception as e:
        logger.error(f"Email notification failed: {str(e)}", exc_info=True)
        raise