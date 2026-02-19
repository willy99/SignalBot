from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer
from datetime import datetime, date
from typing import Optional, Any, Union
from dics.deserter_xls_dic import *
from utils.utils import format_to_excel_date

class Person(BaseModel):
    # Дозволяє використовувати як назви змінних, так і аліаси (назви колонок Excel)
    model_config = ConfigDict(populate_by_name=True)

    # Числові та ідентифікатори
    id: int = Field(None, alias=COLUMN_INCREMEMTAL)
    rnokpp: Optional[Any] = Field(None, alias=COLUMN_ID_NUMBER)

    # Дати (тепер використовуємо Union, щоб бути гнучкими)
    insert_date: Optional[Union[date, str]] = Field(None, alias=COLUMN_INSERT_DATE)
    desertion_date: Optional[Union[date, str]] = Field(None, alias=COLUMN_DESERTION_DATE)
    raport_date: Optional[Union[date, str]] = Field(None, alias=COLUMN_RAPORT_DATE)
    birthday: Optional[Union[date, str]] = Field(None, alias=COLUMN_BIRTHDAY)
    enlistment_date: Optional[Union[date, str]] = Field(None, alias=COLUMN_ENLISTMENT_DATE)
    return_date: Optional[Union[date, str]] = Field(None, alias=COLUMN_RETURN_DATE)
    return_reserve_date: Optional[Union[date, str]] = Field(None, alias=COLUMN_RETURN_TO_RESERVE_DATE)

    # Текстові поля (Short Input)
    name: str = Field("", alias=COLUMN_NAME)
    mil_unit: Optional[str] = Field("", alias=COLUMN_MIL_UNIT)
    service_type: Optional[str] = Field("", alias=COLUMN_SERVICE_TYPE)
    title: Optional[str] = Field("", alias=COLUMN_TITLE)
    title2: Optional[str] = Field("", alias=COLUMN_TITLE_2)
    desertion_place: Optional[str] = Field("", alias=COLUMN_DESERTION_PLACE)
    desertion_type: Optional[str] = Field("", alias=COLUMN_DESERTION_TYPE)
    subunit: Optional[str] = Field("", alias=COLUMN_SUBUNIT)
    subunit2: Optional[str] = Field("", alias=COLUMN_SUBUNIT2)
    desertion_region: Optional[str] = Field("", alias=COLUMN_DESERTION_REGION)
    tzk: Optional[str] = Field("", alias=COLUMN_TZK)
    tzk_region: Optional[str] = Field("", alias=COLUMN_TZK_REGION)
    address: Optional[str] = Field("", alias=COLUMN_ADDRESS)
    phone: Optional[str] = Field("", alias=COLUMN_PHONE)
    executor: Optional[str] = Field("", alias=COLUMN_EXECUTOR)
    desertion_term: Optional[str] = Field("", alias=COLUMN_DESERTION_TERM)
    review_status: Optional[str] = Field("", alias=COLUMN_REVIEW_STATUS)
    service_days: Optional[int] = Field(None, alias=COLUMN_SERVICE_DAYS)

    # Великі текстові поля (Textarea)
    desertion_conditions: Optional[str] = Field("", alias=COLUMN_DESERT_CONDITIONS)
    bio: Optional[str] = Field("", alias=COLUMN_BIO)

    @field_validator('insert_date', 'desertion_date', 'raport_date', 'birthday',
                     'enlistment_date', 'return_date', 'return_reserve_date', mode='before')
    @classmethod
    def parse_ua_date(cls, value: Any) -> Any:
        if isinstance(value, str) and value.strip():
            # Намагаємося розпарсити формат ДД.ММ.РРРР
            for fmt in ('%d.%m.%Y', '%d.%m.%y'):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return value

    @classmethod
    def from_excel_dict(cls, data: dict):
        return cls(**data)

    def to_excel_dict(self):
        data = self.model_dump(by_alias=True)
        for key, val in data.items():
            if isinstance(val, datetime):
                data[key] = format_to_excel_date(val)
        return data
