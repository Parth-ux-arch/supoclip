from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass, replace
from email import policy
from email.message import EmailMessage
from typing import Optional

import boto3
import requests

from ..config import Config
from ..database import get_session_maker
from ..models import EmailDelivery
from .email_layout import is_full_document, render_email_html

logger = logging.getLogger(__name__)

TRANSACTIONAL = "transactional"
# Product announcements must honour the opt-out: send them only through
# ProductUpdateEmailService, which checks it and adds the unsubscribe headers.
PRODUCT_UPDATE = "product_update"


@dataclass(frozen=True)
class InlineImage:
    """An image shown in the body via ``<img src="cid:{content_id}">``.

    Use an address-like id (``clip0@supoclip``), as RFC 2392 expects.
    """

    content_id: str
    data: bytes
    content_type: str = "image/jpeg"


@dataclass(frozen=True)
class EmailContent:
    subject: str
    html: str
    text: str
    headers: tuple[tuple[str, str], ...] = ()
    category: str = TRANSACTIONAL
    inline_images: tuple[InlineImage, ...] = ()
    reply_to: tuple[str, ...] = ()


class SesEmailService:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.region = self.config.aws_region
        self.access_key_id = self.config.aws_access_key_id
        self.secret_access_key = self.config.aws_secret_access_key
        self.from_email = self.config.ses_from_email
        # Keep the existing class name for callers; SES remains the default.
        self.provider = getattr(self.config, "email_provider", "ses")
        self.resend_api_key = getattr(self.config, "resend_api_key", None)
        if self.provider == "resend":
            self.region = "resend"
            self.from_email = getattr(self.config, "resend_from_email", None)
        self._client = None

    @property
    def is_configured(self) -> bool:
        if self.provider == "resend":
            return bool(self.resend_api_key and self.from_email)
        if self.provider != "ses":
            return False
        return bool(
            self.region
            and self.access_key_id
            and self.secret_access_key
            and self.from_email
        )

    def _raw_message(self, recipient: str, content: EmailContent) -> bytes:
        """MIME for emails with inline images.

        multipart/alternative(text, multipart/related(html, images)) is the
        shape Outlook needs to show images in the body instead of listing them
        as attachments; SES's Simple attachments don't guarantee it.
        """
        message = EmailMessage()
        message["From"] = self.from_email
        message["To"] = recipient
        message["Subject"] = content.subject
        for name, value in content.headers:
            message[name] = value
        message.set_content(content.text)
        message.add_alternative(content.html, subtype="html")
        html_part = message.get_payload()[1]
        for image in content.inline_images:
            maintype, subtype = image.content_type.split("/", 1)
            html_part.add_related(
                image.data,
                maintype=maintype,
                subtype=subtype,
                cid=f"<{image.content_id}>",
                disposition="inline",
                filename=f"{image.content_id.split('@')[0]}.{subtype}",
            )
        return message.as_bytes(policy=policy.SMTP)

    def _send_resend(self, recipient: str, content: EmailContent) -> dict:
        payload = {
            "from": self.from_email, "to": [recipient],
            "subject": content.subject, "html": content.html, "text": content.text,
        }
        if content.headers:
            payload["headers"] = dict(content.headers)
        if content.reply_to:
            payload["reply_to"] = list(content.reply_to)
        if content.inline_images:
            payload["attachments"] = [
                {"filename": f"image-{index}.{image.content_type.split('/')[-1]}",
                 "content": base64.b64encode(image.data).decode("ascii"),
                 "content_type": image.content_type, "content_id": image.content_id}
                for index, image in enumerate(content.inline_images)
            ]
        try:
            response = requests.post(
                "https://api.resend.com/emails", json=payload,
                headers={"Authorization": f"Bearer {self.resend_api_key}"},
                timeout=(5, 30), allow_redirects=False,
            )
        except requests.RequestException:
            # Do not include response/request bodies containing verification links.
            raise ValueError("Resend email request failed; delivery is unconfirmed") from None
        if not 200 <= response.status_code < 300:
            raise ValueError(f"Resend rejected email (HTTP {response.status_code})")
        try:
            message_id = response.json().get("id")
        except (ValueError, AttributeError):
            message_id = None
        if not isinstance(message_id, str) or not message_id:
            raise ValueError("Resend response did not include a message ID")
        return {"MessageId": message_id}

    def _send(self, recipient: str, content: EmailContent) -> dict:
        if self.provider == "resend":
            return self._send_resend(recipient, content)
        headers = [{"Name": name, "Value": value} for name, value in content.headers]
        # boto3 clients are thread-safe; reuse one across a campaign's sends.
        if self._client is None:
            self._client = boto3.client(
                "sesv2",
                region_name=self.region,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
            )
        if content.inline_images:
            return self._client.send_email(
                FromEmailAddress=self.from_email,
                Destination={"ToAddresses": [recipient]},
                Content={"Raw": {"Data": self._raw_message(recipient, content)}},
            )
        return self._client.send_email(
            FromEmailAddress=self.from_email,
            Destination={"ToAddresses": [recipient]},
            **({"ReplyToAddresses": list(content.reply_to)} if content.reply_to else {}),
            Content={
                "Simple": {
                    **({"Headers": headers} if headers else {}),
                    "Subject": {"Data": content.subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": content.html, "Charset": "UTF-8"},
                        "Text": {"Data": content.text, "Charset": "UTF-8"},
                    },
                }
            },
        )

    async def send_email(self, recipient: str, content: EmailContent) -> dict:
        if not self.is_configured:
            if self.provider == "resend":
                raise RuntimeError("Resend is not configured. Set RESEND_API_KEY and RESEND_FROM_EMAIL.")
            if self.provider != "ses":
                raise RuntimeError("Unsupported EMAIL_PROVIDER; use ses or resend.")
            raise RuntimeError(
                "Amazon SES is not configured. Set AWS_REGION, AWS_ACCESS_KEY_ID, "
                "AWS_SECRET_ACCESS_KEY and SES_FROM_EMAIL."
            )
        if content.category == PRODUCT_UPDATE and not any(
            name.lower() == "list-unsubscribe-post" for name, _ in content.headers
        ):
            raise ValueError("Send product updates through ProductUpdateEmailService")
        if not is_full_document(content.html):
            content = replace(
                content, html=render_email_html(
                    content.html, app_url=getattr(self.config, "app_base_url", "")
                )
            )

        response = await asyncio.to_thread(self._send, recipient, content)
        # This is acceptance by the email provider, not proof of inbox delivery. Record only
        # metadata: bodies can contain password reset or verification tokens.
        message_id = response["MessageId"]
        try:
            async with get_session_maker()() as db:
                db.add(EmailDelivery(
                    message_id=message_id,
                    recipient=recipient,
                    subject=content.subject,
                    region=self.region,
                ))
                await db.commit()
        except Exception:
            # The email provider has already accepted the message. Preserve a correlation
            # fallback without making callers retry and send duplicate emails.
            logger.exception(
                "Email audit persistence failed: message_id=%s recipient=%s region=%s subject=%r",
                message_id, recipient, self.region, content.subject,
            )
        return dict(response)


def first_name_for(
    *,
    first_name: Optional[str] = None,
    full_name: Optional[str] = None,
    default: str = "there",
) -> str:
    if first_name and first_name.strip():
        return first_name.strip()
    if full_name and full_name.strip():
        return full_name.strip().split()[0]
    return default
