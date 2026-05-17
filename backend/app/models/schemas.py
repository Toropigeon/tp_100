from pydantic import BaseModel


class ChartInfo(BaseModel):
    name: str
    parameter: str
    url: str


class UploadResponse(BaseModel):
    session_id: str
    rows: int
    parameters: list[str]
    charts: list[ChartInfo]


class ParameterClassification(BaseModel):
    parameter: str
    status: str
    nominal: float
    unit: str
    min_value: float
    max_value: float
    mean_value: float
    max_deviation_percent: float
    signed_deviation_percent: float = 0
    deviation_direction: str = "без отклонения"
    first_warning_time: str | None = None
    first_critical_time: str | None = None


class Deviation(BaseModel):
    parameter: str
    status: str
    max_deviation_percent: float
    signed_deviation_percent: float = 0
    direction: str = "без отклонения"
    interpretation: str
    first_detected_time: str | None = None


class FailureMoment(BaseModel):
    detected: bool
    time: str | None = None
    status: str | None = None
    parameter: str | None = None
    description: str


class LocalizationResult(BaseModel):
    cluster_id: str
    component: str
    distance: float


class IdentifiedSymptom(BaseModel):
    fault_id: str
    name: str
    component: str
    score: float
    cosine_similarity: float
    norm_ratio: float
    symptoms: list[str]
    recommendations: list[str]


class DiagnosticVectorResult(BaseModel):
    parameters: list[str]
    vector: list[float]
    localization: LocalizationResult
    identified_symptoms: list[IdentifiedSymptom]


class AnalysisResponse(BaseModel):
    session_id: str
    checked_parameters: list[ParameterClassification]
    deviations: list[Deviation]
    failure_moment: FailureMoment
    diagnostic_vector: DiagnosticVectorResult
    report: str
