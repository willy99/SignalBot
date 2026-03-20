# domain/sys_config.py
from pydantic import BaseModel, Field
from typing import Optional

class SysConfig(BaseModel):
    id: Optional[int] = Field(default=None, description="ID в базі даних")
    category: str = Field(..., description="Група налаштувань для табів")
    key_name: str = Field(..., description="Ім'я змінної в config.py")
    value: str = Field(..., description="Значення у вигляді тексту")
    value_type: str = Field(..., description="Тип: bool, int, float, str")
    description: str = Field(..., description="Опис для UI")
    validation_rule: Optional[str] = Field(default=None, description="Правила валідації (напр. min:0|max:23)")

    def get_typed_value(self):
        """Конвертує рядкове значення з БД у реальний тип Python на основі value_type"""
        if self.value_type == 'bool':
            return str(self.value).strip().lower() in ['true', '1', 'yes']
        elif self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        # Для 'str' або інших просто повертаємо рядок
        return str(self.value)