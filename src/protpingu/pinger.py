from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import requests
from marshmallow import Schema, fields, post_load

_BASE_URL = "https://shop.amul.com"


@dataclass
class StoreInfo:
    _id: str
    _created_by: str
    _size: int
    _updated_by: str
    pincode: str
    substore: str
    created_on: datetime
    updated_on: datetime


@dataclass
class PaginatedStoreInfo:
    limit: int
    start: int
    records: list[StoreInfo]
    count: int
    total: int


class StoreInfoSchema(Schema):
    _id = fields.String(required=True)
    _created_by = fields.String(required=True)
    _size = fields.Integer(required=True)
    _updated_by = fields.String(required=True)
    pincode = fields.String(required=True)
    substore = fields.String(required=True)
    created_on = fields.DateTime(required=True)
    updated_on = fields.DateTime(required=True)

    @post_load
    def make_store_info(self, data, **kwargs):
        return StoreInfo(**data)


class PaginatedStoreInfoSchema(Schema):
    limit = fields.Integer(required=True)
    start = fields.Integer(required=True)
    records = fields.List(fields.Nested(StoreInfoSchema))
    count = fields.Integer(required=True)
    total = fields.Integer(required=True)

    @post_load
    def make_paginated_store_info(self, data, **kwargs):
        return PaginatedStoreInfo(**data)


class StoreNotFoundError(ValueError):
    def __init__(self, pincode, message="No store found for the given pincode"):
        self.pincode = pincode
        super().__init__(f"{message}: {pincode}")


class Requestor:
    session: requests.Session
    paginated_store_info_schema: PaginatedStoreInfoSchema
    store_info: Optional[StoreInfo]

    def __init__(self, session: requests.Session):
        self.session = session
        self.paginated_store_info_schema = PaginatedStoreInfoSchema()
        self.store_info = None

    def set_preference(self, pincode: str):
        response = self.session.get(
            f"{_BASE_URL}/entity/pincode",
            params={
                "limit": 50,
                "filters[0][field]": "pincode",
                "filters[0][value]": pincode,
                "filters[0][operator]": "regex",
            },
            headers={"Accept": "application/json; charset=utf-8"},
        )
        response.raise_for_status()
        pincode_list = response.json()
        store_records = self.paginated_store_info_schema.load(pincode_list)

        matching_store_records = [store_info for store_info in store_records.records if store_info.pincode == pincode]
        if len(matching_store_records) == 0:
            raise StoreNotFoundError(pincode)
        self.store_info = matching_store_records[0]

        response = self.session.put(
            f"{_BASE_URL}/entity/ms.settings/_/setPreferences",
            json={"data": {"store": self.store_info.substore}},
        )
        response.raise_for_status()
