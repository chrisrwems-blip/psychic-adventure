"""SMTP email sending service with auto-detection of common providers."""
import json
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent.parent.parent / "email_settings.json"

PROVIDER_PRESETS = {
    "gmail.com": {"host": "smtp.gmail.com", "port": 587},
    "googlemail.com": {"host": "smtp.gmail.com", "port": 587},
    "outlook.com": {"host": "smtp.office365.com", "port": 587},
    "hotmail.com": {"host": "smtp.office365.com", "port": 587},
    "live.com": {"host": "smtp.office365.com", "port": 587},
    "yahoo.com": {"host": "smtp.mail.yahoo.com", "port": 587},
    "icloud.com": {"host": "smtp.mail.me.com", "port": 587},
    "me.com": {"host": "smtp.mail.me.com", "port": 587},
    "aol.com": {"host": "smtp.aol.com", "port": 587},
}

# Office 365 hosted domains often use smtp.office365.com
O365_HOSTS = {"smtp.office365.com", "smtp-mail.outlook.com"}


def detect_smtp_settings(email: str) -> dict:
    """Auto-detect SMTP settings from email address."""
    domain = email.split("@")[-1].lower()

    if domain in PROVIDER_PRESETS:
        preset = PROVIDER_PRESETS[domain]
        return {
            "host": preset["host"],
            "port": preset["port"],
            "detected": True,
            "provider": domain,
        }

    # Default guess for custom domains (most use Office 365 or Google Workspace)
    return {
        "host": f"smtp.{domain}",
        "port": 587,
        "detected": False,
        "provider": domain,
    }


def save_settings(email: str, password: str, host: str, port: int, display_name: str = "") -> dict:
    """Save SMTP settings to local config file."""
    settings = {
        "email": email,
        "password": password,
        "host": host,
        "port": port,
        "display_name": display_name or email.split("@")[0].title(),
    }
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    return {"status": "saved"}


def load_settings() -> dict | None:
    """Load SMTP settings from local config file."""
    if not SETTINGS_FILE.exists():
        return None
    try:
        return json.loads(SETTINGS_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return None


def delete_settings():
    """Remove saved SMTP settings."""
    if SETTINGS_FILE.exists():
        SETTINGS_FILE.unlink()


def test_connection(email: str, password: str, host: str, port: int) -> dict:
    """Test SMTP connection with provided credentials."""
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls(context=context)
            server.login(email, password)
        return {"success": True, "message": "Connection successful"}
    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "Authentication failed. Check your email and password. If you use two-factor authentication, you need an app-specific password."}
    except smtplib.SMTPConnectError:
        return {"success": False, "message": f"Could not connect to {host}:{port}. Check the server address."}
    except TimeoutError:
        return {"success": False, "message": f"Connection to {host}:{port} timed out. Check the server address and port."}
    except Exception as e:
        return {"success": False, "message": str(e)}


def send_email(to: str, subject: str, body: str, cc: str = "") -> dict:
    """Send an email using saved SMTP settings."""
    settings = load_settings()
    if not settings:
        return {"success": False, "message": "Email not configured. Go to Settings to set up your email."}

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.get('display_name', '')} <{settings['email']}>"
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc

    msg.attach(MIMEText(body, "plain"))

    all_recipients = [addr.strip() for addr in to.split(",")]
    if cc:
        all_recipients.extend(addr.strip() for addr in cc.split(","))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings["host"], settings["port"], timeout=15) as server:
            server.starttls(context=context)
            server.login(settings["email"], settings["password"])
            server.sendmail(settings["email"], all_recipients, msg.as_string())
        return {"success": True, "message": f"Email sent to {to}"}
    except Exception as e:
        return {"success": False, "message": str(e)}
