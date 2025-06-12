from abc import ABC, abstractmethod
from typing import Optional, Sequence

from .. import config
from .. import pinger


class Notifier(ABC):
    @abstractmethod
    def send_message(
        self,
        recipient: config.UserDetails,
        products: Sequence[pinger.ProductInfo],
        out_of_stock_products: Sequence[pinger.ProductInfo],
        subject: Optional[str] = "Products available in Amul Store",
    ):
        pass
