"""
Default message wording. Templates are created from these on first use and can then be
edited by the Super Admin (Messaging screen). Placeholders in {braces} are filled from the
event; unknown placeholders render as empty text.

Placeholders always available: {site_name} {first_name} {full_name} {link}
Consultation events add:       {patient_name} {doctor_name} {date} {time} {mode}
Document events add:           {document_title}
Lead events add:               {lead_number} {customer_name}
"""

from apps.notifications.models import MessageEvent, NotificationChannel

EMAIL = NotificationChannel.EMAIL
WHATSAPP = NotificationChannel.WHATSAPP

DEFAULT_TEMPLATES = {
    (MessageEvent.WELCOME, EMAIL): {
        "subject": "Welcome to {site_name}",
        "body": (
            "Hi {first_name},\n\n"
            "Your patient account is ready. You can book a consultation, see your visits and "
            "keep your reports in one private place.\n\n"
            "Open your portal: {link}\n\n"
            "Warm regards,\nThe {site_name} care team"
        ),
    },
    (MessageEvent.WELCOME, WHATSAPP): {
        "body": "Hi {first_name}, welcome to {site_name}! Your patient account is ready. Book a consultation any time: {link}",
        "whatsapp_params": ["first_name", "link"],
    },
    (MessageEvent.ENQUIRY_RECEIVED, EMAIL): {
        "subject": "We've received your enquiry ({lead_number})",
        "body": (
            "Hi {first_name},\n\n"
            "Thank you for contacting {site_name}. Your reference number is {lead_number}. "
            "A care advisor will get in touch with you within one working day.\n\n"
            "The {site_name} care team"
        ),
    },
    (MessageEvent.ENQUIRY_RECEIVED, WHATSAPP): {
        "body": "Hi {first_name}, thank you for contacting {site_name}. Your reference is {lead_number}. Our care advisor will reach you within one working day.",
        "whatsapp_params": ["first_name", "lead_number"],
    },
    (MessageEvent.CONSULTATION_BOOKED, EMAIL): {
        "subject": "Your consultation is confirmed for {date}",
        "body": (
            "Hi {first_name},\n\n"
            "Your consultation with Dr. {doctor_name} is confirmed.\n\n"
            "Date: {date}\nTime: {time}\nMode: {mode}\n\n"
            "View or manage it here: {link}\n\n"
            "The {site_name} care team"
        ),
    },
    (MessageEvent.CONSULTATION_BOOKED, WHATSAPP): {
        "body": "Hi {first_name}, your consultation with Dr. {doctor_name} is confirmed for {date} at {time} ({mode}). Details: {link}",
        "whatsapp_params": ["first_name", "doctor_name", "date", "time", "mode", "link"],
    },
    (MessageEvent.CONSULTATION_REMINDER, EMAIL): {
        "subject": "Reminder: consultation on {date} at {time}",
        "body": (
            "Hi {first_name},\n\n"
            "This is a reminder of your consultation with Dr. {doctor_name} on {date} at {time} "
            "({mode}).\n\nIf you need to reschedule, please contact us.\n\n"
            "Details: {link}\n\nThe {site_name} care team"
        ),
    },
    (MessageEvent.CONSULTATION_REMINDER, WHATSAPP): {
        "body": "Reminder: your consultation with Dr. {doctor_name} is on {date} at {time} ({mode}). Details: {link}",
        "whatsapp_params": ["doctor_name", "date", "time", "mode", "link"],
    },
    (MessageEvent.CONSULTATION_CANCELLED, EMAIL): {
        "subject": "Your consultation on {date} was cancelled",
        "body": (
            "Hi {first_name},\n\n"
            "Your consultation with Dr. {doctor_name} on {date} at {time} has been cancelled. "
            "You can book a new time here: {link}\n\nThe {site_name} care team"
        ),
    },
    (MessageEvent.CONSULTATION_CANCELLED, WHATSAPP): {
        "body": "Hi {first_name}, your consultation with Dr. {doctor_name} on {date} at {time} was cancelled. Book a new time: {link}",
        "whatsapp_params": ["first_name", "doctor_name", "date", "time", "link"],
    },
    (MessageEvent.PRESCRIPTION_READY, EMAIL): {
        "subject": "Your prescription from Dr. {doctor_name}",
        "body": (
            "Hi {first_name},\n\n"
            "Dr. {doctor_name} has added a prescription to your consultation on {date}. "
            "Sign in to view it: {link}\n\nThe {site_name} care team"
        ),
    },
    (MessageEvent.PRESCRIPTION_READY, WHATSAPP): {
        "body": "Hi {first_name}, Dr. {doctor_name} has added your prescription. View it securely: {link}",
        "whatsapp_params": ["first_name", "doctor_name", "link"],
    },
    (MessageEvent.DOCUMENT_UPLOADED, EMAIL): {
        "subject": "A new report is in your portal",
        "body": (
            "Hi {first_name},\n\n"
            '"{document_title}" has been added to your records. Sign in to view it: {link}\n\n'
            "The {site_name} care team"
        ),
    },
    (MessageEvent.DOCUMENT_UPLOADED, WHATSAPP): {
        "body": 'Hi {first_name}, a new report "{document_title}" is in your portal: {link}',
        "whatsapp_params": ["first_name", "document_title", "link"],
    },
    (MessageEvent.DOCTOR_NEW_BOOKING, EMAIL): {
        "subject": "New booking: {patient_name} on {date} at {time}",
        "body": (
            "Hello Dr. {full_name},\n\n"
            "{patient_name} has booked a {mode} consultation on {date} at {time}.\n\n"
            "Open it: {link}"
        ),
    },
    (MessageEvent.DOCTOR_NEW_BOOKING, WHATSAPP): {
        "body": "New booking: {patient_name}, {date} at {time} ({mode}). {link}",
        "whatsapp_params": ["patient_name", "date", "time", "mode", "link"],
        "is_active": False,
    },
    (MessageEvent.LEAD_ASSIGNED, EMAIL): {
        "subject": "New lead assigned: {lead_number}",
        "body": "Hi {first_name},\n\nLead {lead_number} ({customer_name}) has been assigned to you.\n\nOpen it: {link}",
    },
    (MessageEvent.LEAD_ASSIGNED, WHATSAPP): {
        "body": "New lead {lead_number} ({customer_name}) assigned to you: {link}",
        "whatsapp_params": ["lead_number", "customer_name", "link"],
        "is_active": False,
    },
    (MessageEvent.TEST, EMAIL): {
        "subject": "Test message from {site_name}",
        "body": "This is a test email from {site_name}. If you can read this, email delivery works.",
    },
    (MessageEvent.TEST, WHATSAPP): {
        "body": "This is a test WhatsApp message from {site_name}. Delivery works.",
        "whatsapp_params": [],
    },
}
