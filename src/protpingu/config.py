from dataclasses import dataclass, field
from pathlib import Path
import tomllib
from typing import Optional

from marshmallow import Schema, fields, post_load


@dataclass
class UserDetails:
    name: str
    pincode: str
    email: Optional[str] = None
    wanted_items: list[str] = field(default_factory=list)


@dataclass
class Config:
    users: list[UserDetails] = field(default_factory=list)


class UserDetailsSchema(Schema):
    name = fields.String(required=True)
    pincode = fields.String(required=True)
    email = fields.Email(required=False)
    wanted_items = fields.List(fields.String(), required=False)

    @post_load
    def make_user_details(self, data, **kwargs):
        return UserDetails(**data)


class ConfigSchema(Schema):
    users = fields.List(fields.Nested(UserDetailsSchema), required=False)

    @post_load
    def make_config(self, data, **kwargs):
        return Config(**data)


class ConfigReader:
    config_schema: ConfigSchema

    def __init__(self):
        self.config_schema = ConfigSchema()

    def load_config(self, config_path: Path) -> Config:
        with open(config_path, "rb") as f:
            config_data = tomllib.load(f)
        return self.config_schema.load(config_data)
