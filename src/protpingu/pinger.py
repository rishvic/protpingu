import copy
from dataclasses import dataclass
from datetime import datetime
import json
from typing import Optional

import requests
from marshmallow import Schema, fields, post_load, EXCLUDE

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


@dataclass
class ProductMetaFields:
    uom: str
    weight: str
    ingredients: str
    benefits: str
    how_to_useit: str
    product_type: str


@dataclass
class ProductInfo:
    _id: str
    _created_by: str
    _size: int
    _updated_by: str
    alias: str
    metafields: ProductMetaFields
    description: str
    name: str
    available: int
    barcode: str
    created_on: datetime
    updated_on: datetime


@dataclass
class ShopResponseMessage:
    name: str
    level: str


@dataclass
class ProductResponsePaging:
    limit: int
    start: int
    count: int
    total: int
    configurable_fields: list[str]


@dataclass
class ProductResponse:
    messages: list[ShopResponseMessage]
    fileBaseUrl: str
    data: list[ProductInfo]
    paging: ProductResponsePaging


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


class ProductMetaFieldsSchema(Schema):
    uom = fields.String(required=True)
    weight = fields.String(required=True)
    ingredients = fields.String(required=True)
    benefits = fields.String(required=True)
    how_to_useit = fields.String(required=True)
    product_type = fields.String(required=True)

    @post_load
    def make_product_meta_fields(self, data, **kwargs):
        return ProductMetaFields(**data)


class ProductInfoSchema(Schema):
    _id = fields.String(required=True)
    _created_by = fields.String(required=True)
    _size = fields.Integer(required=True)
    _updated_by = fields.String(required=True)
    alias = fields.String(required=True)
    metafields = fields.Nested(ProductMetaFieldsSchema, required=True)
    description = fields.String(required=True)
    name = fields.String(required=True)
    available = fields.Integer(required=True)
    barcode = fields.String(required=True)
    created_on = fields.DateTime(required=True)
    updated_on = fields.DateTime(required=True)

    class Meta:
        unknown = EXCLUDE

    @post_load
    def make_product_info(self, data, **kwargs):
        return ProductInfo(**data)


class ShopResponseMessageSchema(Schema):
    name = fields.String(required=True)
    level = fields.String(required=True)

    @post_load
    def make_shop_response_message(self, data, **kwargs):
        return ShopResponseMessage(**data)


class ProductResponsePagingSchema(Schema):
    limit = fields.Integer(required=True)
    start = fields.Integer(required=True)
    count = fields.Integer(required=True)
    total = fields.Integer(required=True)
    configurable_fields = fields.List(fields.String, required=True)

    @post_load
    def make_product_response_paging(self, data, **kwargs):
        return ProductResponsePaging(**data)


class ProductResponeSchema(Schema):
    messages = fields.List(fields.Nested(ShopResponseMessageSchema), required=True)
    fileBaseUrl = fields.Url(required=True)
    data = fields.List(fields.Nested(ProductInfoSchema), required=True)
    paging = fields.Nested(ProductResponsePagingSchema, required=True)


class StoreNotFoundError(ValueError):
    def __init__(self, pincode, message="No store found for the given pincode"):
        self.pincode = pincode
        super().__init__(f"{message}: {pincode}")


class StoreNotSetError(ValueError):
    def __init__(self, message="Preferred store not set"):
        super().__init__(message)


class Requestor:
    session: requests.Session
    store_info: Optional[StoreInfo]
    paginated_store_info_schema: PaginatedStoreInfoSchema
    product_response_schema: ProductResponeSchema

    def __init__(self, session: requests.Session):
        self.session = session
        self.store_info = None
        self.paginated_store_info_schema = PaginatedStoreInfoSchema()
        self.product_response_schema = ProductResponeSchema()

    def set_preference(self, pincode: str) -> StoreInfo:
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

        return copy.deepcopy(self.store_info)

    def get_item_info(self, item_id: str):
        if self.store_info is None:
            raise StoreNotSetError()

        response = self.session.get(
            f"{_BASE_URL}/api/1/entity/ms.products",
            params={
                "q": json.dumps({"alias": item_id}),
                "limit": 1,
            },
            headers={"Accept": "application/json; charset=utf-8"}
        )
        response.raise_for_status()
        product_info = response.json()

        return self.product_response_schema.load(product_info)
