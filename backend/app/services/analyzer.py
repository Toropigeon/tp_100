from app.models.schemas import Deviation, FailureMoment, ParameterClassification
from app.services.thresholds import RULES, classify_deviation, find_rule
import pandas as pd


def analyze_thresholds(
    dataframe: pd.DataFrame,
    numeric_columns: list[str],
    time_column: str | None = None,
) -> tuple[list[ParameterClassification], list[Deviation], FailureMoment]:
    checked: list[ParameterClassification] = []
    deviations: list[Deviation] = []
    first_events: list[tuple[int, str, str, str]] = []

    for column in numeric_columns:
        rule = find_rule(column)
        if not rule:
            continue

        series = dataframe[column].dropna()
        if series.empty:
            continue

        deviations_percent = ((series - rule.nominal).abs() / rule.nominal) * 100
        max_index = int(deviations_percent.idxmax())
        max_value = float(series.loc[max_index])
        signed_deviation = ((max_value - rule.nominal) / rule.nominal) * 100
        max_deviation = abs(float(signed_deviation))
        status = classify_deviation(max_deviation, rule)
        warning_index = _first_threshold_index(deviations_percent, rule.warning_percent)
        critical_index = _first_threshold_index(deviations_percent, rule.critical_percent, strict=True)
        first_warning_time = _format_time(dataframe, time_column, warning_index)
        first_critical_time = _format_time(dataframe, time_column, critical_index)
        if warning_index is not None:
            first_events.append((warning_index, rule.name, "предаварийное", first_warning_time or str(warning_index)))
        if critical_index is not None:
            first_events.append((critical_index, rule.name, "аварийное", first_critical_time or str(critical_index)))

        classification = ParameterClassification(
            parameter=rule.name,
            status=status,
            nominal=rule.nominal,
            unit=rule.unit,
            min_value=float(series.min()),
            max_value=float(series.max()),
            mean_value=float(series.mean()),
            max_deviation_percent=round(max_deviation, 2),
            signed_deviation_percent=round(signed_deviation, 2),
            deviation_direction=_direction(signed_deviation),
            first_warning_time=first_warning_time,
            first_critical_time=first_critical_time,
        )
        checked.append(classification)

        if status != "нормальное":
            first_detected_time = first_critical_time if status == "аварийное" else first_warning_time
            deviations.append(
                Deviation(
                    parameter=rule.name,
                    status=status,
                    max_deviation_percent=round(max_deviation, 2),
                    signed_deviation_percent=round(signed_deviation, 2),
                    direction=_direction(signed_deviation),
                    interpretation=_interpret(rule.name, status, max_deviation, signed_deviation),
                    first_detected_time=first_detected_time,
                )
            )

    known_parameters = {item.parameter for item in checked}
    for rule in RULES:
        if rule.name not in known_parameters:
            checked.append(
                ParameterClassification(
                    parameter=rule.name,
                    status="нет данных",
                    nominal=rule.nominal,
                    unit=rule.unit,
                    min_value=0,
                    max_value=0,
                    mean_value=0,
                    max_deviation_percent=0,
                    signed_deviation_percent=0,
                    deviation_direction="нет данных",
                )
            )

    return checked, deviations, _build_failure_moment(first_events)


def _interpret(parameter: str, status: str, max_deviation: float, signed_deviation: float) -> str:
    direction = _direction(signed_deviation)
    if status == "аварийное":
        return f"{parameter}: параметр {direction} на {max_deviation:.2f}% и превысил аварийный порог."
    return f"{parameter}: параметр {direction} на {max_deviation:.2f}% и находится в предаварийной зоне."


def _direction(signed_deviation: float) -> str:
    if signed_deviation > 0:
        return "вырос"
    if signed_deviation < 0:
        return "упал"
    return "не изменился"


def _first_threshold_index(series: pd.Series, threshold: float, strict: bool = False) -> int | None:
    mask = series > threshold if strict else series >= threshold
    matches = series[mask]
    if matches.empty:
        return None
    return int(matches.index[0])


def _format_time(dataframe: pd.DataFrame, time_column: str | None, index: int | None) -> str | None:
    if index is None:
        return None
    if time_column and time_column in dataframe.columns:
        value = dataframe.loc[index, time_column]
        if pd.notna(value):
            return str(value)
    return f"измерение {index + 1}"


def _build_failure_moment(events: list[tuple[int, str, str, str]]) -> FailureMoment:
    if not events:
        return FailureMoment(
            detected=False,
            description="Сбой не обнаружен: параметры не вышли за предаварийные или аварийные пороги.",
        )
    index, parameter, status, time_value = sorted(events, key=lambda item: (item[0], 0 if item[2] == "аварийное" else 1))[0]
    return FailureMoment(
        detected=True,
        time=time_value,
        status=status,
        parameter=parameter,
        description=f"Первый признак сбоя зафиксирован в момент {time_value}: параметр \"{parameter}\" перешел в состояние \"{status}\".",
    )
