from dataclasses import dataclass
from math import sqrt

from app.models.schemas import DiagnosticVectorResult, IdentifiedSymptom, LocalizationResult, ParameterClassification
from app.services.thresholds import RULES


@dataclass(frozen=True)
class FaultPattern:
    fault_id: str
    name: str
    vector: tuple[float, ...]
    symptoms: tuple[str, ...]
    recommendations: tuple[str, ...]


@dataclass(frozen=True)
class FaultCluster:
    cluster_id: str
    component: str
    centroid: tuple[float, ...]
    faults: tuple[FaultPattern, ...]


PARAMETER_ORDER = tuple(rule.name for rule in RULES)


CLUSTERS: tuple[FaultCluster, ...] = (
    FaultCluster(
        cluster_id="normal_operation",
        component="Штатный режим котла",
        centroid=(0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        faults=(
            FaultPattern(
                fault_id="normal_operation",
                name="Нормальная работа котла",
                vector=(0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                symptoms=("параметры находятся вблизи номинальных значений",),
                recommendations=(
                    "Продолжить штатный мониторинг.",
                    "Проверять достоверность датчиков при плановом обходе.",
                ),
            ),
        ),
    ),
    FaultCluster(
        cluster_id="steam_drum",
        component="Основной барабан",
        centroid=(-6, -12, -7, 0, 1, 0, 0, 12, 0, 0),
        faults=(
            FaultPattern(
                fault_id="drum_leak",
                name="Нарушение герметичности основного барабана",
                vector=(-7, -14, -9, 0, 1, 0, 0, 15, 0, 0),
                symptoms=(
                    "давление в барабане падает относительно номинала",
                    "давление в паросборной камере снижается вслед за барабаном",
                    "растет расход РОУ как признак нештатного перераспределения пара",
                ),
                recommendations=(
                    "Снизить нагрузку котла до безопасного уровня.",
                    "Проверить люки, фланцевые соединения, импульсные линии и арматуру барабана.",
                    "Проверить достоверность датчиков давления барабана и паросборной камеры.",
                    "При подтверждении утечки вывести котел из работы для устранения дефекта.",
                ),
            ),
            FaultPattern(
                fault_id="drum_pressure_sensor_fault",
                name="Неверные показания давления барабана",
                vector=(0, -12, 0, 0, 0, 0, 0, 0, 0, 0),
                symptoms=(
                    "давление барабана отклоняется без согласованной реакции связанных параметров",
                    "остальные параметры парового тракта остаются близкими к номиналу",
                ),
                recommendations=(
                    "Сверить показания датчика давления барабана с резервным каналом.",
                    "Проверить импульсную линию датчика на засорение, завоздушивание или утечку.",
                    "Не менять режим котла по одному подозрительному каналу без подтверждения.",
                ),
            ),
        ),
    ),
    FaultCluster(
        cluster_id="superheater",
        component="Пароперегреватель и поверхности нагрева",
        centroid=(2, 0, 0, 8, 0, 0, 7, 4, 6, 0),
        faults=(
            FaultPattern(
                fault_id="steam_overheating",
                name="Перегрев пара и поверхностей нагрева",
                vector=(3, 0, 0, 8, 0, 0, 7, 4, 7, 0),
                symptoms=(
                    "температура перегретого пара выросла выше допустимого уровня",
                    "температуры после РОУ и БРОУ также повышены",
                    "режим указывает на тепловую перегрузку парового тракта",
                ),
                recommendations=(
                    "Ограничить тепловую нагрузку и стабилизировать подачу топлива.",
                    "Проверить расход питательной воды и работу впрысков/охладителей.",
                    "Проверить загрязнение поверхностей нагрева и состояние горелочных устройств.",
                    "Не допускать дальнейшего роста температуры перегретого пара.",
                ),
            ),
            FaultPattern(
                fault_id="feedwater_cooling_loss",
                name="Недостаточное охлаждение перегретого пара",
                vector=(0, 0, 0, 7, -5, 0, 6, 0, 4, 0),
                symptoms=(
                    "перегретый пар растет при признаках нарушения охлаждения",
                    "температура питательной воды ниже расчетного режима",
                ),
                recommendations=(
                    "Проверить тракт питательной воды и расход через охладитель.",
                    "Проверить регулирующую арматуру впрыска.",
                    "Снизить нагрузку до восстановления температурного режима.",
                ),
            ),
        ),
    ),
    FaultCluster(
        cluster_id="steam_cooling",
        component="Охлаждение пара и питательный тракт",
        centroid=(0, 0, 0, -6, -4, 0, -4, 0, -4, 0),
        faults=(
            FaultPattern(
                fault_id="steam_temperature_drop",
                name="Переохлаждение пара",
                vector=(0, 0, 0, -6, -4, 0, -4, 0, -4, 0),
                symptoms=(
                    "температура перегретого пара упала ниже номинального режима",
                    "температуры после РОУ и БРОУ также снижены",
                ),
                recommendations=(
                    "Проверить режим впрыска и работу охладителей пара.",
                    "Проверить температуру и расход питательной воды.",
                    "Ограничить изменение нагрузки до восстановления температурного режима.",
                ),
            ),
        ),
    ),
    FaultCluster(
        cluster_id="safety_relief",
        component="Предохранительные клапаны, РОУ и БРОУ",
        centroid=(0, 13, 11, 3, 0, 0, 0, -10, 0, -8),
        faults=(
            FaultPattern(
                fault_id="safety_valve_fault",
                name="Неисправность предохранительного или сбросного клапана",
                vector=(0, 14, 12, 3, 0, 0, 0, -10, 0, -9),
                symptoms=(
                    "давление в барабане выросло выше допустимого уровня",
                    "давление в паросборной камере также выросло",
                    "расход через РОУ или БРОУ недостаточен для стабилизации давления",
                ),
                recommendations=(
                    "Немедленно проверить готовность предохранительных клапанов и сбросной арматуры.",
                    "Ограничить нагрузку котла до восстановления устойчивого давления.",
                    "Проверить исполнительные механизмы РОУ/БРОУ, приводы, уставки и импульсные линии.",
                    "При сохранении роста давления остановить котел по аварийному регламенту.",
                ),
            ),
            FaultPattern(
                fault_id="prds_low_side_fault",
                name="Нарушение регулирования давления на низкой стороне РОУ",
                vector=(0, 0, 0, 0, 0, 12, 4, 8, 0, 0),
                symptoms=(
                    "давление на низкой стороне РОУ вышло из нормального диапазона",
                    "расход РОУ изменился вместе с температурой после РОУ",
                ),
                recommendations=(
                    "Проверить регулятор давления РОУ и исполнительный механизм клапана.",
                    "Проверить импульсную линию давления на низкой стороне РОУ.",
                    "Ограничить изменение нагрузки до стабилизации давления после РОУ.",
                ),
            ),
        ),
    ),
    FaultCluster(
        cluster_id="relief_flow",
        component="РОУ, БРОУ и контуры расхода",
        centroid=(0, 0, 0, 0, 0, 0, 6, -65, 6, -62),
        faults=(
            FaultPattern(
                fault_id="relief_flow_drop",
                name="Недостаточный расход через РОУ/БРОУ",
                vector=(0, 0, 0, 0, 0, 0, 6, -80, 6, -80),
                symptoms=(
                    "расход РОУ или БРОУ резко упал относительно номинала",
                    "температуры после РОУ/БРОУ растут из-за нарушения расхода",
                ),
                recommendations=(
                    "Проверить исполнительные механизмы РОУ и БРОУ.",
                    "Проверить насосы, задвижки и фактическое открытие регулирующей арматуры.",
                    "Снизить нагрузку до восстановления расчетного расхода.",
                    "Проверить датчики расхода РОУ и БРОУ резервным способом.",
                ),
            ),
            FaultPattern(
                fault_id="bypass_flow_instability",
                name="Неустойчивое регулирование расхода РОУ/БРОУ",
                vector=(0, 0, 0, 0, 0, 0, 4, -40, 4, -40),
                symptoms=(
                    "расходы РОУ и БРОУ отклоняются согласованно",
                    "после регулирующих узлов меняется температура",
                ),
                recommendations=(
                    "Проверить контуры регулирования расхода РОУ и БРОУ.",
                    "Проверить исполнительные механизмы и обратную связь по положению клапанов.",
                    "Стабилизировать режим перед повторным повышением нагрузки.",
                ),
            ),
        ),
    ),
    FaultCluster(
        cluster_id="low_side_prds_pressure",
        component="Низкая сторона РОУ",
        centroid=(0, 0, 0, 0, 0, 14, 5, 11, 0, 0),
        faults=(
            FaultPattern(
                fault_id="prds_low_side_fault",
                name="Нарушение регулирования давления на низкой стороне РОУ",
                vector=(0, 0, 0, 0, 0, 14, 5, 11, 0, 0),
                symptoms=(
                    "давление на низкой стороне РОУ выросло выше допустимого уровня",
                    "расход РОУ и температура после РОУ изменились согласованно",
                ),
                recommendations=(
                    "Проверить регулятор давления на низкой стороне РОУ.",
                    "Проверить исполнительный механизм клапана РОУ и обратную связь по положению.",
                    "Проверить импульсную линию давления после РОУ.",
                    "Ограничить изменение нагрузки до стабилизации давления после РОУ.",
                ),
            ),
        ),
    ),
    FaultCluster(
        cluster_id="pressure_path",
        component="Барабан и паросборная камера",
        centroid=(0, 8, 7, 0, 0, 2, 0, 0, 0, 0),
        faults=(
            FaultPattern(
                fault_id="pressure_growth",
                name="Рост давления в паровом тракте",
                vector=(0, 9, 8, 0, 0, 2, 0, 0, 0, 0),
                symptoms=(
                    "давление в барабане выросло относительно номинала",
                    "давление в паросборной камере выросло согласованно",
                ),
                recommendations=(
                    "Ограничить нагрузку котла до стабилизации давления.",
                    "Проверить контуры регулирования давления и сбросную арматуру.",
                    "Проверить уставки и импульсные линии давления.",
                ),
            ),
        ),
    ),
    FaultCluster(
        cluster_id="drum_sensor",
        component="Канал измерения давления барабана",
        centroid=(0, -13, 0, 0, 0, 0, 0, 0, 0, 0),
        faults=(
            FaultPattern(
                fault_id="drum_pressure_sensor_fault",
                name="Неверные показания давления барабана",
                vector=(0, -13, 0, 0, 0, 0, 0, 0, 0, 0),
                symptoms=(
                    "давление барабана отклоняется изолированно",
                    "паросборная камера и остальные связанные параметры не подтверждают аналогичное падение",
                ),
                recommendations=(
                    "Сверить показания датчика давления барабана с резервным каналом.",
                    "Проверить импульсную линию датчика на засорение, завоздушивание или утечку.",
                    "Не менять режим котла по одному подозрительному каналу без подтверждения.",
                ),
            ),
        ),
    ),
    FaultCluster(
        cluster_id="pressure_path_drop",
        component="Барабан и паросборная камера",
        centroid=(0, -8, -7, 0, 0, -5, 0, 0, 0, 0),
        faults=(
            FaultPattern(
                fault_id="pressure_drop",
                name="Падение давления в паровом тракте",
                vector=(0, -9, -8, 0, 0, -6, 0, 0, 0, 0),
                symptoms=(
                    "давление в барабане упало относительно номинала",
                    "давление в паросборной камере снизилось согласованно",
                ),
                recommendations=(
                    "Проверить герметичность парового тракта и арматуру барабана.",
                    "Проверить фактическую производительность котла и расход пара.",
                    "Проверить датчики давления и импульсные линии.",
                ),
            ),
        ),
    ),
    FaultCluster(
        cluster_id="furnace_combustion",
        component="Топка и система горения",
        centroid=(14, 9, 8, 9, 0, 0, 5, -12, 0, -10),
        faults=(
            FaultPattern(
                fault_id="combustion_instability",
                name="Нарушение режима горения и неустойчивая работа топки",
                vector=(16, 10, 9, 11, 0, 0, 6, -14, 0, -12),
                symptoms=(
                    "производительность котла сильно отклонилась от номинала",
                    "температура перегретого пара и давления меняются согласованно с нагрузкой",
                    "расходы РОУ/БРОУ реагируют на колебания парового режима",
                ),
                recommendations=(
                    "Стабилизировать соотношение топливо-воздух.",
                    "Проверить горелки, тягу, подачу топлива и работу дутьевых/дымососных механизмов.",
                    "Снизить нагрузку до исчезновения колебаний температуры и давления.",
                    "Проверить систему автоматики горения и контуры регулирования.",
                ),
            ),
            FaultPattern(
                fault_id="load_control_fault",
                name="Неустойчивое регулирование производительности котла",
                vector=(13, 6, 5, 4, 0, 0, 0, 5, 0, 4),
                symptoms=(
                    "производительность отклонилась сильнее связанных температурных параметров",
                    "давления изменяются вслед за нагрузкой",
                ),
                recommendations=(
                    "Проверить контур регулирования нагрузки котла.",
                    "Проверить задание нагрузки, исполнительные механизмы подачи топлива и воздуха.",
                    "Ограничить скорость изменения нагрузки до стабилизации параметров.",
                ),
            ),
        ),
    ),
    FaultCluster(
        cluster_id="feedwater",
        component="Питательный тракт",
        centroid=(0, 0, 0, 4, -8, 0, 3, 0, 0, 0),
        faults=(
            FaultPattern(
                fault_id="feedwater_temperature_fault",
                name="Нарушение температурного режима питательной воды",
                vector=(0, 0, 0, 4, -8, 0, 3, 0, 0, 0),
                symptoms=(
                    "температура питательной воды ушла от номинального режима",
                    "изменение питательной воды влияет на температуру парового тракта",
                ),
                recommendations=(
                    "Проверить подогреватели питательной воды и регулирующую арматуру.",
                    "Проверить расход питательной воды и корректность показаний датчика температуры.",
                    "Стабилизировать температуру питательной воды перед изменением нагрузки.",
                ),
            ),
        ),
    ),
)


def run_diagnostics(checked: list[ParameterClassification]) -> DiagnosticVectorResult:
    vector = _build_vector(checked)
    cluster, distance = _nearest_cluster(vector)
    matches = sorted(((_score(vector, fault), fault) for fault in cluster.faults), key=lambda item: item[0][0], reverse=True)[:3]
    symptoms = [
        IdentifiedSymptom(
            fault_id=fault.fault_id,
            name=fault.name,
            component=cluster.component,
            score=round(score, 4),
            cosine_similarity=round(cosine, 4),
            norm_ratio=round(norm_ratio, 4),
            symptoms=list(fault.symptoms),
            recommendations=list(fault.recommendations),
        )
        for (score, cosine, norm_ratio), fault in matches
    ]
    return DiagnosticVectorResult(
        parameters=list(PARAMETER_ORDER),
        vector=[round(value, 2) for value in vector],
        localization=LocalizationResult(
            cluster_id=cluster.cluster_id,
            component=cluster.component,
            distance=round(distance, 4),
        ),
        identified_symptoms=symptoms,
    )


def _build_vector(checked: list[ParameterClassification]) -> tuple[float, ...]:
    by_name = {item.parameter: item.signed_deviation_percent for item in checked}
    return tuple(float(by_name.get(name, 0)) for name in PARAMETER_ORDER)


def _nearest_cluster(vector: tuple[float, ...]) -> tuple[FaultCluster, float]:
    return min(((cluster, _euclidean(vector, cluster.centroid)) for cluster in CLUSTERS), key=lambda item: item[1])


def _score(vector: tuple[float, ...], fault: FaultPattern) -> tuple[float, float, float]:
    if _norm(vector) == 0 and _norm(fault.vector) == 0:
        return 2, 1, 1
    cosine = _cosine_similarity(vector, fault.vector)
    norm_ratio = _norm_ratio(vector, fault.vector)
    return cosine + norm_ratio, cosine, norm_ratio


def _euclidean(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    norm_a = _norm(a)
    norm_b = _norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0
    return sum(x * y for x, y in zip(a, b)) / (norm_a * norm_b)


def _norm_ratio(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    norm_a = _norm(a)
    norm_b = _norm(b)
    if norm_a == 0 and norm_b == 0:
        return 1
    if norm_a == 0 or norm_b == 0:
        return 0
    return min(norm_a, norm_b) / max(norm_a, norm_b)


def _norm(vector: tuple[float, ...]) -> float:
    return sqrt(sum(value**2 for value in vector))
