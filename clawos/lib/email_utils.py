import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.header import Header
from email import encoders
import mimetypes
import os
import config

# 硬编码配置
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
SMTP_USER = ""
SMTP_PASS = ""
ENABLE_EMAIL = True

def send_text_email(to_email, subject, content):
    """Send a plain text email."""
    smtp = get_smtp_config()
    if not smtp['user'] or not smtp['pass']:
        print("Email not configured")
        return False
    
    try:
        message = MIMEText(content, 'plain', 'utf-8')
        message['From'] = smtp['user']
        message['To'] = to_email
        message['Subject'] = Header(subject, 'utf-8')

        port = smtp['port']
        if smtp.get('ssl') == 'ssl' or port == 465:
            server = smtplib.SMTP_SSL(smtp['host'], port, timeout=30)
        else:
            server = smtplib.SMTP(smtp['host'], port, timeout=30)
            if smtp.get('ssl') == 'tls':
                server.starttls()

        server.login(smtp['user'], smtp['pass'])
        server.sendmail(smtp['user'], [to_email], message.as_string())
        server.quit()
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return False

def send_verification_email(to_email, code):
    """
    Send a verification code to the specified email.
    
    Args:
        to_email: Recipient email address
        code: Verification code
        
    Returns:
        True if sent successfully, False otherwise
    """
    subject = f"您的验证码: {code}"
    content = f"您的验证码是: {code}\n\nThis code will expire in 5 minutes."
    
    if not ENABLE_EMAIL:
        print(f"DEBUG (Mock Email): Verification Code for {to_email}: {code}")
        return True
        
    try:
        message = MIMEText(content, 'plain', 'utf-8')
        message['From'] = f"<{SMTP_USER}>"
        message['To'] = to_email
        message['Subject'] = Header(subject, 'utf-8')

        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
        
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [to_email], message.as_string())
        server.quit()
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        print(f"DEBUG: Verification Code for {to_email}: {code}")
        return False

def send_html_email(to_email, subject, html_content):
    """
    Send an HTML email.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content for email body
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not ENABLE_EMAIL:
        print(f"DEBUG (Mock HTML Email): {subject} -> {to_email}\n{html_content}")
        return True
        
    try:
        message = MIMEMultipart('alternative')
        message['From'] = f"Admin System <{SMTP_USER}>"
        message['To'] = to_email
        message['Subject'] = Header(subject, 'utf-8')
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html', 'utf-8')
        message.attach(html_part)

        port = smtp['port']
        if smtp.get('ssl') == 'ssl' or port == 465:
            server = smtplib.SMTP_SSL(smtp['host'], port, timeout=30)
        else:
            server = smtplib.SMTP(smtp['host'], port, timeout=30)
            if smtp.get('ssl') == 'tls':
                server.starttls()

        server.login(smtp['user'], smtp['pass'])
        server.sendmail(smtp['user'], [to_email], message.as_string())
        server.quit()
        print(f"HTML email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send HTML email to {to_email}: {e}")
        return False

def send_email_with_attachment(to_email, subject, body, attachment_paths=None):
    """
    Send email with optional attachments.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body content (plain text)
        attachment_paths: List of file paths to attach
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not ENABLE_EMAIL:
        print(f"DEBUG (Mock Email with Attachment): {subject} -> {to_email}")
        print(f"Attachments: {attachment_paths}")
        print(f"Body: {body}")
        return True
    
    smtp = get_smtp_config()
    if not smtp['user'] or not smtp['pass']:
        print("Email not configured")
        return False
    
    try:
        message = MIMEMultipart('mixed')
        message['From'] = smtp['user']
        message['To'] = to_email
        message['Subject'] = Header(subject, 'utf-8')
        
        # Attach body
        body_part = MIMEText(body, 'plain', 'utf-8')
        message.attach(body_part)
        
        # Attach files
        if attachment_paths:
            for file_path in attachment_paths:
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
                        part.add_header(
                            'Content-Disposition',
                            'attachment',
                            filename=filename
                        )
                        message.attach(part)
                else:
                    print(f"Warning: File not found: {file_path}")
        
        port = smtp['port']
        if smtp.get('ssl') == 'ssl' or port == 465:
            server = smtplib.SMTP_SSL(smtp['host'], port, timeout=30)
        else:
            server = smtplib.SMTP(smtp['host'], port, timeout=30)
            if smtp.get('ssl') == 'tls':
                server.starttls()

        server.login(smtp['user'], smtp['pass'])
        server.sendmail(smtp['user'], [to_email], message.as_string())
        server.quit()
        print(f"Email with attachments sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return False


if __name__ == "__main__":
    # Test sending email
    from config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS, ENABLE_EMAIL
    
    print("Email Utils - Test Mode")
    print(f"SMTP Server: {SMTP_SERVER}")
    print(f"Port: {SMTP_PORT}")
    print(f"User: {SMTP_USER}")
    print(f"Enabled: {ENABLE_EMAIL}")
    
    # Test mock email
    print("\n--- Testing send_text_email ---")
    send_text_email("test@example.com", "Test Subject", "Test content")
    
    print("\n--- Testing send_verification_email ---")
    send_verification_email("test@example.com", "123456")
    
    print("\n--- Testing send_html_email ---")
    send_html_email("test@example.com", "HTML Test", "<h1>Hello</h1><p>This is a test.</p>")


# Load config from file
EMAIL_CONFIG_FILE = os.path.join(config.DATA_DIR, 'email_config.json')

def get_email_config():
    try:
        if os.path.exists(EMAIL_CONFIG_FILE):
            with open(EMAIL_CONFIG_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def get_smtp_config():
    cfg = get_email_config()
    return {
        'host': cfg.get('smtp_host', 'smtp.qq.com'),
        'port': int(cfg.get('smtp_port', 465)),
        'user': cfg.get('smtp_user', ''),
        'pass': cfg.get('smtp_pass', ''),
        'ssl': cfg.get('smtp_ssl', 'ssl'),
        'from_name': cfg.get('smtp_from', 'ClawOS')
    }
