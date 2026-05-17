from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd

from app.config import get_settings
from app.models.schemas import AnalysisResponse, ChartInfo, UploadResponse
from app.services.analyzer import analyze_thresholds
from app.services.charts import build_charts
from app.services.csv_processor import preprocess_dataframe, read_csv_bytes, save_processed_csv
from app.services.diagnostic_engine import run_diagnostics
from app.services.llm import ReportGenerator
from app.services.rag import DocumentationIndex


settings = get_settings()
app = FastAPI(title="TP-100 Diagnostics Analyzer", version="0.1.0")

origins = ["*"] if settings.cors_origins == "*" else [item.strip() for item in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

doc_index = DocumentationIndex(settings.docs_dir)
report_generator = ReportGenerator(settings)
sessions: dict[str, dict] = {}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Загрузите файл CSV")

    raw = await file.read()
    try:
        source_df = read_csv_bytes(raw)
        processed_df, time_column, numeric_columns = preprocess_dataframe(source_df)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session_id = str(uuid4())
    session_dir = settings.storage_dir / session_id
    chart_dir = session_dir / "charts"
    save_processed_csv(processed_df, session_dir / "processed.csv")
    charts = build_charts(processed_df, time_column, numeric_columns, chart_dir)

    sessions[session_id] = {
        "csv": session_dir / "processed.csv",
        "time_column": time_column,
        "numeric_columns": numeric_columns,
    }

    return UploadResponse(
        session_id=session_id,
        rows=len(processed_df),
        parameters=numeric_columns,
        charts=[
            ChartInfo(
                name=chart["name"],
                parameter=chart["parameter"],
                url=f"/api/sessions/{session_id}/charts/{chart['name']}",
            )
            for chart in charts
        ],
    )


@app.get("/api/sessions/{session_id}/charts/{chart_name}")
def get_chart(session_id: str, chart_name: str) -> FileResponse:
    chart_path = settings.storage_dir / session_id / "charts" / Path(chart_name).name
    if not chart_path.exists():
        raise HTTPException(status_code=404, detail="График не найден")
    return FileResponse(chart_path, media_type="image/png")


@app.post("/api/analyze/{session_id}", response_model=AnalysisResponse)
async def analyze(session_id: str) -> AnalysisResponse:
    session = sessions.get(session_id)
    csv_path = settings.storage_dir / session_id / "processed.csv"
    if not session and not csv_path.exists():
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    dataframe = pd.read_csv(csv_path)
    numeric_columns = session["numeric_columns"] if session else [column for column in dataframe.columns if pd.api.types.is_numeric_dtype(dataframe[column])]
    time_column = session.get("time_column") if session else None
    checked, deviations, failure_moment = analyze_thresholds(dataframe, numeric_columns, time_column)
    diagnostic_result = run_diagnostics(checked)

    query = " ".join(item.parameter for item in deviations) or "ТП-100 нормальная работа котла"
    documentation_chunks = doc_index.search(query)
    report = await report_generator.generate(checked, deviations, documentation_chunks, failure_moment, diagnostic_result)

    return AnalysisResponse(
        session_id=session_id,
        checked_parameters=checked,
        deviations=deviations,
        failure_moment=failure_moment,
        diagnostic_vector=diagnostic_result,
        report=report,
    )
