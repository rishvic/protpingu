import os
from pathlib import Path
import requests
from smtplib import SMTP
from typing import Optional

from absl import app
from absl import flags
from absl import logging
from dotenv import load_dotenv
from xdg_base_dirs import xdg_config_home

from .. import config
from ..notifier import email
from .. import pinger

FLAGS = flags.FLAGS
flags.DEFINE_string(
    "config", str(xdg_config_home() / "protpingu" / "config.toml"), "Config file path"
)
flags.DEFINE_bool("debug", False, "Run in debug mode")

EMAIL_HOST: Optional[str] = None
EMAIL_PORT: Optional[int] = None
EMAIL_USERNAME: Optional[str] = None
EMAIL_PASSWORD: Optional[str] = None


def check_and_run(config_data: config.Config, email_notifier: email.EmailNotifier):
    session = requests.Session()
    shop_checker = pinger.Requestor(session)

    for user in config_data.users:
        shop_checker.set_preference(user.pincode)

        present_items = []
        out_of_stock_items = []

        for wanted_item in user.wanted_items:
            item_info = shop_checker.get_item_info(wanted_item)
            logging.info(
                f"Checking for {user.name} pincode {user.pincode} item {wanted_item}"
            )
            if item_info.available != 0:
                present_items.append(item_info)
            else:
                out_of_stock_items.append(item_info)

        email_notifier.send_message(user, present_items, out_of_stock_items)


def main(argv):
    del argv  # Unused.

    if FLAGS.debug:
        load_dotenv()

    EMAIL_HOST = os.getenv("EMAIL_HOST")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT"))
    EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

    if not all([EMAIL_HOST, EMAIL_USERNAME, EMAIL_PASSWORD]):
        raise ValueError(
            "Error: Please set EMAIL_HOST, EMAIL_USERNAME, and EMAIL_PASSWORD environment variables."
        )

    config_path = Path(FLAGS.config)
    config_reader = config.ConfigReader()
    config_data = config_reader.load_config(config_path)

    with SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)

        email_notifier = email.EmailNotifier(
            server, f"Amul Notifier <{EMAIL_USERNAME}>"
        )

        check_and_run(config_data, email_notifier)


def app_run():
    app.run(main)


if __name__ == "__main__":
    app_run()
