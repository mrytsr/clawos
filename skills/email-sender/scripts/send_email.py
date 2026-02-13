#!/usr/bin/env python3
"""
Email Sender Script
Send emails via SMTP
"""

import argparse
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.header import Header
from email import encoders
import mimetypes
import os

# Default SMTP settings
DEFAULT_SMTP_SERVER = "smtp.qq.com"
DEFAULT_SMTP_PORT = 465

# Get from environment or use defaults
SMTP_SERVER = os.environ.get("SMTP_SERVER", DEFAULT_SMTP_SERVER)
SMTP_PORT = int(os.environ.get("SMTP_PORT", DEFAULT_SMTP_PORT))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
ENABLE_EMAIL = os.environ.get("ENABLE_EMAIL", "false").lower() == "true"


def send_email(to_email, subject, content, content_type="text", attachments=None):
    """
    Send email via SMTP
    
    Args:
        to_email: Recipient email
        subject: Email subject
        content: Email body
        content_type: "text" or "html"
        attachments: List of file paths
    
    Returns:
        True if sent successfully
    """
    print(f"[Email] Sending to: {to_email}")
    print(f"  Subject: {subject}")
    
    # Mock mode
    if not ENABLE_EMAIL:
        print(f"[Email] MOCK MODE - Email would be sent:")
        print(f"  To: {to_email}")
        print(f"  Subject: {subject}")
        print(f"  Content: {content[:100]}...")
        if attachments:
            print(f"  Attachments: {attachments}")
        return True
    
    try:
        # Build message
        if content_type == "html":
            message = MIMEMultipart('alternative')
            message.attach(MIMEText(content, 'html', 'utf-8'))
        else:
            message = MIMEText(content, 'plain', 'utf-8')
        
        message['From'] = f"System <{SMTP_USER}>"
        message['To'] = to_email
        message['Subject'] = Header(subject, 'utf-8')
        
        # Add attachments
        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    ctype, encoding = mimetypes.guess_type(file_path)
                    if ctype is None or encoding:
                        ctype = 'application/octet-stream'
                    maintype, subtype = ctype.split('/', 1)
                    
                    with open(file_path, 'rb') as fp:
                        part = MIMEBase(maintype, subtype)
                        part.set_payload(fp.read())
                        encoders.encode_base64(part)
                        
                        filename = os.path.basename(file_path)
                        part.add_header('Content-Disposition', 'attachment', filename=filename)
                        message.attach(part)
                else:
                    print(f"[Email] Warning: File not found: {file_path}")
        
        # Send
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
        
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [to_email], message.as_string())
        server.quit()
        
        print(f"[Email] ✅ Sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"[Email] ❌ Failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Send Email via SMTP")
    parser.add_argument("--to", required=True, help="Recipient email")
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument("--content", required=True, help="Email body")
    parser.add_argument("--type", default="text", choices=["text", "html"], help="Content type")
    parser.add_argument("--attach", action="append", default=[], help="Attachment file paths")
    
    args = parser.parse_args()
    
    success = send_email(
        args.to,
        args.subject,
        args.content,
        args.type,
        args.attach if args.attach else None
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
