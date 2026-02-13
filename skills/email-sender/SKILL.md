---
name: email-sender
description: "Send emails via SMTP. Use when user needs to send emails for: verification codes, notifications, reports, alerts, or any email delivery. Supports plain text, HTML, and attachments. Perfect for: sending verification codes, delivering reports, sending alerts, or any email communication."
---

# Email Sender Skill

## Quick Start

Send a simple email:

```bash
python scripts/email.py --to "user@example.com" --subject "Hello" --content "Email content"
```

## Parameters

| Parameter | Description | Required |
|-----------|-------------|----------|
| `--to` | Recipient email address | Yes |
| `--subject` | Email subject | Yes |
| `--content` | Email body content | Yes |
| `--type` | Content type: text/html | text |
| `--attach` | Attachment file paths | No |

## Examples

```bash
# Plain text email
python scripts/send_email.py --to "user@example.com" --subject "测试" --content "这是一封测试邮件"

# HTML email
python scripts/send_email.py --to "user@example.com" --subject "HTML Test" --content "<h1>Hello</h1><p>This is HTML</p>" --type html

# With attachment
python scripts/send_email.py --to "user@example.com" --subject "Report" --content "See attached" --attach "/path/to/file.pdf"

# Multiple attachments
python scripts/email.py --to "user@example.com" --subject "Files" --content "Multiple files" --attach "a.pdf" --attach "b.pdf"
```

## API Configuration

Uses SMTP configuration from environment or config:
- SMTP_SERVER: smtp.qq.com (default)
- SMTP_PORT: 465
- SMTP_USER: email address
- SMTP_PASS: authorization code
- ENABLE_EMAIL: true/false (false = mock mode)
