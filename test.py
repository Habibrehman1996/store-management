import asyncio
import os
from aiosmtplib import SMTP
from email.mime.text import MIMEText
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

async def test_email():
    try:
        msg = MIMEText("Test email from store management system")
        msg["Subject"] = "Test Email"
        msg["From"] = os.getenv("SMTP_USERNAME")
        msg["To"] = os.getenv("SMTP_USERNAME")
        async with SMTP(
            hostname=os.getenv("SMTP_HOST"),
            port=int(os.getenv("SMTP_PORT")),
            username=os.getenv("SMTP_USERNAME"),
            password=os.getenv("SMTP_PASSWORD"),
            use_tls=False,
            start_tls=True
        ) as smtp:
            await smtp.send_message(msg)
        logger.debug("Test email sent")
        print("Test email sent successfully")
    except Exception as e:
        logger.error(f"Test email failed: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_email())