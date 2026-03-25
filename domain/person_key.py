from dataclasses import dataclass

@dataclass
class PersonKey:
    rnokpp: str
    name: str
    des_date: str
    mil_unit: str


    @property
    def uid(self) -> str:
        """Створює унікальний рядок для пошуку в словнику результатів"""
        return f"{self.name}_{self.rnokpp}_{self.des_date}_{self.mil_unit}".lower().replace(" ", "")