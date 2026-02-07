# Email Configuration (from xiandan/config_dev/config.py)

# SMTP Server Settings
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
SMTP_USER = "mrytsr@qq.com"
SMTP_PASS = "rykouxobfexacaff"

# Enable email sending (True = real send, False = mock/debug mode)
ENABLE_EMAIL = True

# Rate Limiting (optional)
EMAIL_RATE_LIMIT = 10  # emails per minute
