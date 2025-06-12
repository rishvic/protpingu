from email.message import EmailMessage
from smtplib import SMTP
from typing import Sequence

from absl import logging
from jinja2 import Environment, PackageLoader, select_autoescape
import html2text

from .__init__ import Notifier
from .. import pinger, config


class EmailNotFoundError(ValueError):
    user: config.UserDetails

    def __init__(
        self, user: config.UserDetails, message: str = "email ID not found for user"
    ):
        self.user = user
        super().__init__(f"{message}: {user.name}")


class EmailNotifier(Notifier):
    server: SMTP
    sender: str
    jinja_env: Environment

    def __init__(self, server: SMTP, sender: str):
        self.server = server
        self.sender = sender
        self.jinja_env = Environment(
            loader=PackageLoader("protpingu.notifier.email"),
            autoescape=select_autoescape(),
        )

    def send_message(
        self,
        recipient: config.UserDetails,
        products: Sequence[pinger.ProductInfo],
        out_of_stock_products: Sequence[pinger.ProductInfo],
        subject: str = "Products available in Amul Store",
    ):
        if recipient.email is None or len(products) == 0:
            return  # Do not send email.

        logging.info(f"Sending email to %s <%s>", recipient.name, recipient.email)

        email_template = self.jinja_env.get_template("notify_email.html")
        mail_html_content = email_template.render(
            name=recipient.name,
            products=products,
            out_of_stock_products=out_of_stock_products,
        )
        mail_plain_content = html2text.html2text(mail_html_content)

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = f"{recipient.name} <{recipient.email}>"

        msg.set_content(mail_plain_content)
        msg.add_alternative(mail_html_content, subtype="html")

        self.server.send_message(msg)
