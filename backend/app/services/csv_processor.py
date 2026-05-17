from io import BytesIO
from pathlib import Path
import csv

import pandas as pd


TIME_COLUMNS = {"timestamp", "time", "datetime", "date", "время", "дата"}


def _detect_separator(raw: bytes) -> str | None:
    sample = raw[:4096].decode("utf-8-sig", errors="ignore")
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
    except csv.Error:
        return None


def read_csv_bytes(raw: bytes) -> pd.DataFrame:
    separator = _detect_separator(raw)
    kwargs = {"encoding": "utf-8-sig"}
    if separator:
        kwargs["sep"] = separator
    else:
        kwargs["sep"] = None
        kwargs["engine"] = "python"

    dataframe = pd.read_csv(BytesIO(raw), **kwargs)
    dataframe = dataframe.dropna(how="all")
    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    if dataframe.empty:
        raise ValueError("CSV не содержит строк с данными")
    return dataframe


def preprocess_dataframe(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, str | None, list[str]]:
    df = dataframe.copy()
    time_column = next((column for column in df.columns if column.strip().lower() in TIME_COLUMNS), None)

    numeric_columns: list[str] = []
    for column in df.columns:
        if column == time_column:
            continue
        series = df[column]
        if series.dtype == object:
            series = series.astype(str).str.replace(",", ".", regex=False)
        converted = pd.to_numeric(series, errors="coerce")
        if converted.notna().any():
            df[column] = converted
            numeric_columns.append(column)

    if not numeric_columns:
        raise ValueError("CSV должен содержать хотя бы одну числовую колонку")

    df[numeric_columns] = df[numeric_columns].interpolate(method="linear", limit_direction="both")
    for column in numeric_columns:
        if df[column].isna().any():
            df[column] = df[column].fillna(df[column].mean())

    if time_column:
        try:
            df[time_column] = pd.to_datetime(df[time_column])
        except Exception:
            pass

    return df, time_column, numeric_columns


def save_processed_csv(dataframe: pd.DataFrame, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(target, index=False)
