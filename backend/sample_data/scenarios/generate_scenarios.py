from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable


OUT_DIR = Path(__file__).resolve().parent
POINTS = 30
FAULT_START = 11
STEP_MINUTES = 10
START_TIME = datetime(2026, 5, 8, 0, 0)


PARAMETERS = [
    "Производительность котла",
    "Давление в барабане",
    "Давление в паросборной камере",
    "Температура перегретого пара",
    "Температура питательной воды",
    "Давление на низкой стороне РОУ",
    "Температура после РОУ",
    "Расход РОУ",
    "Температура после БРОУ",
    "Расход БРОУ",
]


NOMINALS = {
    "Производительность котла": 640.0,
    "Давление в барабане": 155.0,
    "Давление в паросборной камере": 140.0,
    "Температура перегретого пара": 545.0,
    "Температура питательной воды": 155.0,
    "Давление на низкой стороне РОУ": 25.0,
    "Температура после РОУ": 250.0,
    "Расход РОУ": 20.0,
    "Температура после БРОУ": 160.0,
    "Расход БРОУ": 250.0,
}


BASE_NOISE = [
    -0.25,
    0.12,
    -0.08,
    0.18,
    -0.15,
    0.05,
    0.22,
    -0.18,
    0.08,
    -0.11,
    0.14,
    -0.06,
    0.10,
    -0.20,
    0.16,
    -0.04,
    0.06,
    -0.13,
    0.19,
    -0.09,
    0.11,
    -0.17,
    0.07,
    -0.12,
    0.15,
    -0.05,
    0.09,
    -0.10,
    0.13,
    -0.07,
]


@dataclass(frozen=True)
class Scenario:
    filename: str
    title: str
    description: str
    profile: Callable[[int], dict[str, float]]


def normal_profile(_: int) -> dict[str, float]:
    return {}


def drum_leak(i: int) -> dict[str, float]:
    p = ramp(i, start=11)
    if p == 0:
        return {}
    return {
        "Производительность котла": -1.5 - 6.5 * p,
        "Давление в барабане": -2.0 - 12.0 * p,
        "Давление в паросборной камере": -1.5 - 7.5 * p,
        "Расход РОУ": 2.0 + 13.0 * p,
    }


def steam_overheating(i: int) -> dict[str, float]:
    p = ramp(i, start=10)
    if p == 0:
        return {}
    return {
        "Производительность котла": 0.5 + 2.8 * p,
        "Температура перегретого пара": 1.0 + 7.0 * p,
        "Температура после РОУ": 1.0 + 6.2 * p,
        "Расход РОУ": 0.5 + 4.0 * p,
        "Температура после БРОУ": 1.0 + 5.8 * p,
    }


def steam_overcooling(i: int) -> dict[str, float]:
    p = ramp(i, start=10)
    if p == 0:
        return {}
    return {
        "Температура перегретого пара": -1.0 - 6.2 * p,
        "Температура питательной воды": -1.0 - 5.0 * p,
        "Температура после РОУ": -1.0 - 5.4 * p,
        "Температура после БРОУ": -1.0 - 4.8 * p,
    }


def safety_valve_fault(i: int) -> dict[str, float]:
    p = ramp(i, start=12)
    if p == 0:
        return {}
    return {
        "Давление в барабане": 2.0 + 12.5 * p,
        "Давление в паросборной камере": 1.5 + 11.0 * p,
        "Температура перегретого пара": 0.5 + 3.0 * p,
        "Расход РОУ": -2.0 - 8.5 * p,
        "Расход БРОУ": -2.0 - 7.5 * p,
    }


def pressure_drop(i: int) -> dict[str, float]:
    p = ramp(i, start=12)
    if p == 0:
        return {}
    return {
        "Давление в барабане": -2.0 - 8.0 * p,
        "Давление в паросборной камере": -1.5 - 7.0 * p,
        "Давление на низкой стороне РОУ": -1.0 - 7.0 * p,
    }


def pressure_growth(i: int) -> dict[str, float]:
    p = ramp(i, start=12)
    if p == 0:
        return {}
    return {
        "Давление в барабане": 2.0 + 8.5 * p,
        "Давление в паросборной камере": 1.5 + 8.0 * p,
        "Давление на низкой стороне РОУ": 1.0 + 4.5 * p,
    }


def prds_flow_drop(i: int) -> dict[str, float]:
    p = ramp(i, start=10)
    if p == 0:
        return {}
    return {
        "Температура после РОУ": 1.5 + 6.5 * p,
        "Расход РОУ": -5.0 - 80.0 * p,
        "Температура после БРОУ": 1.0 + 5.5 * p,
        "Расход БРОУ": -5.0 - 78.0 * p,
    }


def prds_flow_instability(i: int) -> dict[str, float]:
    p = ramp(i, start=10)
    if p == 0:
        return {}
    wave = -1 if i % 2 == 0 else 1
    amp = 4.0 + 42.0 * p
    return {
        "Температура после РОУ": wave * (1.0 + 5.0 * p),
        "Расход РОУ": -abs(amp),
        "Температура после БРОУ": wave * (1.0 + 4.5 * p),
        "Расход БРОУ": -abs(amp * 0.9),
    }


def combustion_instability(i: int) -> dict[str, float]:
    p = ramp(i, start=10)
    if p == 0:
        return {}
    wave = -1 if i % 2 == 0 else 1
    amp = 2.0 + 12.0 * p
    return {
        "Производительность котла": wave * amp,
        "Давление в барабане": wave * amp * 0.72,
        "Давление в паросборной камере": wave * amp * 0.64,
        "Температура перегретого пара": wave * amp * 0.72,
        "Температура после РОУ": wave * amp * 0.38,
        "Расход РОУ": -wave * amp * 0.95,
        "Расход БРОУ": -wave * amp * 0.78,
    }


def load_control_fault(i: int) -> dict[str, float]:
    p = ramp(i, start=11)
    if p == 0:
        return {}
    wave = -1 if i % 3 == 0 else 1
    return {
        "Производительность котла": wave * (4.0 + 9.5 * p),
        "Давление в барабане": wave * (1.5 + 5.0 * p),
        "Давление в паросборной камере": wave * (1.0 + 4.2 * p),
        "Температура перегретого пара": wave * (1.0 + 3.5 * p),
        "Расход РОУ": -wave * (2.0 + 5.0 * p),
        "Расход БРОУ": -wave * (1.0 + 4.0 * p),
    }


def feedwater_temperature_fault(i: int) -> dict[str, float]:
    p = ramp(i, start=12)
    if p == 0:
        return {}
    return {
        "Температура питательной воды": -2.0 - 8.5 * p,
        "Температура перегретого пара": 0.5 + 4.0 * p,
        "Температура после РОУ": 0.5 + 3.4 * p,
    }


def low_side_prds_pressure_fault(i: int) -> dict[str, float]:
    p = ramp(i, start=11)
    if p == 0:
        return {}
    return {
        "Давление на низкой стороне РОУ": 2.0 + 12.0 * p,
        "Температура после РОУ": 1.0 + 4.0 * p,
        "Расход РОУ": 2.0 + 9.0 * p,
    }


def brou_overuse(i: int) -> dict[str, float]:
    p = ramp(i, start=11)
    if p == 0:
        return {}
    return {
        "Давление в барабане": -1.0 - 5.5 * p,
        "Давление в паросборной камере": -1.0 - 5.0 * p,
        "Температура после БРОУ": 1.0 + 6.5 * p,
        "Расход БРОУ": 4.0 + 14.0 * p,
    }


def sensor_fault_drum_pressure(i: int) -> dict[str, float]:
    p = ramp(i, start=13)
    if p == 0:
        return {}
    return {
        "Давление в барабане": -3.0 - 10.0 * p,
    }


def combined_overheat_pressure(i: int) -> dict[str, float]:
    p = ramp(i, start=10)
    if p == 0:
        return {}
    return {
        "Давление в барабане": 1.0 + 7.5 * p,
        "Давление в паросборной камере": 1.0 + 7.0 * p,
        "Температура перегретого пара": 1.0 + 6.8 * p,
        "Температура после РОУ": 1.0 + 5.8 * p,
        "Температура после БРОУ": 1.0 + 5.0 * p,
    }


SCENARIOS = [
    Scenario("01_normal_operation.csv", "Нормальная работа", "Все параметры остаются около номинала.", normal_profile),
    Scenario("02_drum_seal_leak.csv", "Нарушение герметичности барабана", "Падает давление барабана и паросборной камеры, растет расход РОУ.", drum_leak),
    Scenario("03_steam_overheating.csv", "Перегрев пара", "Растут температуры перегретого пара, после РОУ и после БРОУ.", steam_overheating),
    Scenario("04_steam_overcooling.csv", "Переохлаждение пара", "Температурные параметры парового тракта падают ниже номинала.", steam_overcooling),
    Scenario("05_safety_valve_fault.csv", "Неисправность сбросной арматуры", "Давление растет, расход РОУ/БРОУ недостаточен.", safety_valve_fault),
    Scenario("06_pressure_drop.csv", "Падение давления", "Согласованное падение давления в паровом тракте.", pressure_drop),
    Scenario("07_pressure_growth.csv", "Рост давления", "Согласованный рост давления в барабане и паросборной камере.", pressure_growth),
    Scenario("08_prds_flow_drop.csv", "Падение расхода РОУ/БРОУ", "Резко падает расход через РОУ и БРОУ.", prds_flow_drop),
    Scenario("09_prds_flow_instability.csv", "Неустойчивый расход РОУ/БРОУ", "Расходы РОУ/БРОУ заметно снижаются и температурный режим становится нестабильным.", prds_flow_instability),
    Scenario("10_combustion_instability.csv", "Неустойчивая работа топки", "Колеблются нагрузка, давление, температура пара и расходы.", combustion_instability),
    Scenario("11_load_control_fault.csv", "Неустойчивое регулирование нагрузки", "Производительность колеблется сильнее связанных параметров.", load_control_fault),
    Scenario("12_feedwater_temperature_fault.csv", "Нарушение температуры питательной воды", "Температура питательной воды падает и влияет на паровой тракт.", feedwater_temperature_fault),
    Scenario("13_low_side_prds_pressure_fault.csv", "Нарушение давления на низкой стороне РОУ", "Давление после РОУ растет вместе с расходом и температурой.", low_side_prds_pressure_fault),
    Scenario("14_brou_overuse.csv", "Чрезмерный расход БРОУ", "Растет расход БРОУ и температура после БРОУ при снижении давления.", brou_overuse),
    Scenario("15_drum_pressure_sensor_fault.csv", "Неисправность датчика давления барабана", "Одиночное отклонение давления барабана без согласованной реакции остальных параметров.", sensor_fault_drum_pressure),
    Scenario("16_combined_overheat_pressure.csv", "Комбинированный перегрев и рост давления", "Одновременно растут давление и температура парового тракта.", combined_overheat_pressure),
]


def ramp(index: int, start: int = FAULT_START) -> float:
    if index < start:
        return 0.0
    return min(1.0, (index - start + 1) / (POINTS - start))


def values_for(index: int, profile: Callable[[int], dict[str, float]]) -> dict[str, float]:
    values = {}
    offsets = profile(index)
    for parameter in PARAMETERS:
        percent = BASE_NOISE[index % len(BASE_NOISE)] + offsets.get(parameter, 0.0)
        values[parameter] = round(NOMINALS[parameter] * (1 + percent / 100), 3)
    return values


def write_scenario(scenario: Scenario) -> None:
    path = OUT_DIR / scenario.filename
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", *PARAMETERS])
        for index in range(POINTS):
            timestamp = START_TIME + timedelta(minutes=index * STEP_MINUTES)
            values = values_for(index, scenario.profile)
            writer.writerow([timestamp.strftime("%Y-%m-%d %H:%M"), *[values[p] for p in PARAMETERS]])


def write_readme() -> None:
    lines = [
        "# TP-100 Test Scenarios",
        "",
        f"Каждый CSV содержит {POINTS} измерений по 10 параметрам котла ТП-100.",
        "В аварийных сценариях первые измерения имитируют нормальную работу, затем параметры постепенно выходят в предаварийную и аварийную зоны.",
        "Генератор задает значения как процентные отклонения от номиналов, поэтому сценарии согласованы с диагностическим вектором backend.",
        "",
        "## Файлы",
        "",
    ]
    for scenario in SCENARIOS:
        lines.append(f"- `{scenario.filename}` - {scenario.title}: {scenario.description}")
    lines.append("")
    lines.append("## Перегенерация")
    lines.append("")
    lines.append("```bash")
    lines.append("python3 backend/sample_data/scenarios/generate_scenarios.py")
    lines.append("```")
    lines.append("")
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def remove_old_scenarios() -> None:
    for path in OUT_DIR.glob("*.csv"):
        path.unlink()


def main() -> None:
    remove_old_scenarios()
    for scenario in SCENARIOS:
        write_scenario(scenario)
    write_readme()
    print(f"Generated {len(SCENARIOS)} scenarios in {OUT_DIR}")


if __name__ == "__main__":
    main()
