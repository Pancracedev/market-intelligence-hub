from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    slack_webhook_url: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserSettingsUpdate(BaseModel):
    slack_webhook_url: str | None = None


class PriceConfig(BaseModel):
    type: Literal["price"] = "price"
    url: str
    css_selector: str
    currency: str = "EUR"
    stock_selector: str | None = None
    promo_selector: str | None = None


class TrendConfig(BaseModel):
    type: Literal["trend"] = "trend"
    keyword: str
    geo: str = ""
    timeframe: str = "today 12-m"


class EurostatConfig(BaseModel):
    type: Literal["eurostat"] = "eurostat"
    dataset_code: str
    filters: dict[str, str] = Field(default_factory=dict)


WatcherConfig = Annotated[
    Union[PriceConfig, TrendConfig, EurostatConfig], Field(discriminator="type")
]


class WatcherCreate(BaseModel):
    watcher_type: Literal["price", "trend", "eurostat"]
    name: str
    config: WatcherConfig
    schedule: str = "@daily"
    alert_price_drop_pct: float | None = Field(default=None, gt=0, le=100)
    alert_on_stock_out: bool = True
    alert_on_promo: bool = True

    @model_validator(mode="after")
    def check_type_matches_config(self) -> "WatcherCreate":
        if self.watcher_type != self.config.type:
            raise ValueError("watcher_type must match config.type")
        return self


class WatcherUpdate(BaseModel):
    name: str | None = None
    config: WatcherConfig | None = None
    schedule: str | None = None
    is_active: bool | None = None
    alert_price_drop_pct: float | None = Field(default=None, gt=0, le=100)
    alert_on_stock_out: bool | None = None
    alert_on_promo: bool | None = None


class WatcherResponse(BaseModel):
    id: int
    watcher_type: str
    name: str
    config: dict
    is_active: bool
    schedule: str
    alert_price_drop_pct: float | None = None
    alert_on_stock_out: bool
    alert_on_promo: bool
    created_at: datetime
    updated_at: datetime
    latest_gold_timeseries_key: str | None = None
    latest_gold_summary_key: str | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    id: int
    watcher_id: int
    alert_type: str
    channel: str
    message: str
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RunResponse(BaseModel):
    id: int
    watcher_id: int
    run_ts: str
    status: str
    error_message: str | None
    records_count: int | None
    gold_key: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
