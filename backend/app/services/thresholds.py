from dataclasses import dataclass
import re
from typing import Iterable


@dataclass(frozen=True)
class ThresholdRule:
    name: str
    aliases: tuple[str, ...]
    nominal: float
    unit: str
    warning_percent: float
    critical_percent: float


RULES: tuple[ThresholdRule, ...] = (
    ThresholdRule("Производительность котла", ("производительность", "load", "capacity"), 640, "т/ч", 5, 10),
    ThresholdRule("Давление в барабане", ("давление в барабане", "барабан", "drum pressure"), 155, "кгс/см2", 5, 10),
    ThresholdRule("Давление в паросборной камере", ("паросбор", "steam header pressure"), 140, "кгс/см2", 5, 10),
    ThresholdRule("Температура перегретого пара", ("перегрет", "superheated steam temperature"), 545, "C", 3, 5),
    ThresholdRule("Температура питательной воды", ("питательной воды", "feedwater temperature"), 155, "C", 3, 5),
    ThresholdRule("Давление на низкой стороне РОУ", ("низкой стороне роу", "роу давление", "prds pressure"), 25, "кгс/см2", 5, 10),
    ThresholdRule("Температура после РОУ", ("температура после роу", "prds temperature"), 250, "C", 3, 5),
    ThresholdRule("Расход РОУ", ("расход роу", "prds flow"), 20, "т/ч", 5, 10),
    ThresholdRule("Температура после БРОУ", ("температура после броу", "bypass temperature"), 160, "C", 3, 5),
    ThresholdRule("Расход БРОУ", ("расход броу", "bypass flow"), 250, "т/ч", 5, 10),
)


def normalize_name(value: str) -> str:
    value = value.lower().replace("ё", "е")
    value = re.sub(r"[^a-zа-я0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def find_rule(column: str, rules: Iterable[ThresholdRule] = RULES) -> ThresholdRule | None:
    normalized = normalize_name(column)
    for rule in rules:
        names = (rule.name, *rule.aliases)
        if any(normalize_name(name) in normalized or normalized in normalize_name(name) for name in names):
            return rule
    return None


def classify_deviation(deviation_percent: float, rule: ThresholdRule) -> str:
    if deviation_percent > rule.critical_percent:
        return "аварийное"
    if deviation_percent >= rule.warning_percent:
        return "предаварийное"
    return "нормальное"

