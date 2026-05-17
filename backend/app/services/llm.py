import httpx
import re

from app.config import Settings
from app.models.schemas import Deviation, DiagnosticVectorResult, FailureMoment, ParameterClassification


class ReportGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate(
        self,
        checked: list[ParameterClassification],
        deviations: list[Deviation],
        documentation_chunks: list[str],
        failure_moment: FailureMoment,
        diagnostic_result: DiagnosticVectorResult,
    ) -> str:
        prompt = build_prompt(checked, deviations, documentation_chunks, failure_moment, diagnostic_result)
        if self.settings.llm_provider.lower() == "openrouter" and self.settings.openrouter_api_key:
            try:
                return _sanitize_plain_text(await self._call_openrouter(prompt))
            except Exception:
                return self._static_report(checked, deviations, failure_moment, diagnostic_result)
        return self._static_report(checked, deviations, failure_moment, diagnostic_result)

    async def _call_openrouter(self, prompt: str) -> str:
        url = f"{self.settings.openrouter_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.settings.openrouter_model,
            "messages": [
                {"role": "system", "content": "Ты инженер-диагност котла ТП-100. Отвечай строго на русском языке."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "HTTP-Referer": self.settings.app_public_url,
            "X-Title": self.settings.app_title,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]

    def _static_report(
        self,
        checked: list[ParameterClassification],
        deviations: list[Deviation],
        failure_moment: FailureMoment,
        diagnostic_result: DiagnosticVectorResult,
    ) -> str:
        primary = diagnostic_result.identified_symptoms[0] if diagnostic_result.identified_symptoms else None
        if deviations:
            deviation_lines = "\n".join(
                f"{item.parameter} - {_status_label(item.status)}. Отклонение: {item.max_deviation_percent:.2f}%. "
                f"Параметр {item.direction}. "
                f"Первое обнаружение: {item.first_detected_time or 'не определено'}."
                for item in deviations
            )
        else:
            deviation_lines = "Отклонения не обнаружены."
        symptom_lines = _format_symptoms(diagnostic_result)
        recommendations = _format_recommendations(diagnostic_result)
        conclusion = (
            f"Наиболее вероятный диагноз: {primary.name}. Локализованный узел: {diagnostic_result.localization.component}."
            if primary
            else "Диагностический вектор не указывает на выраженную неисправность."
        )

        return (
            "Отчет о работе котла ТП-100\n\n"
            "Список обнаруженных отклонений\n"
            f"{deviation_lines}\n\n"
            "Момент возникновения сбоя\n"
            f"{failure_moment.description}\n\n"
            "Локализация\n"
            f"{diagnostic_result.localization.component}\n\n"
            "Идентификация\n"
            f"{symptom_lines}\n\n"
            "Рекомендации по исправлению неисправностей\n"
            f"{recommendations}\n\n"
            "Итоговое заключение\n"
            f"{conclusion}"
        )


def build_prompt(
    checked: list[ParameterClassification],
    deviations: list[Deviation],
    documentation_chunks: list[str],
    failure_moment: FailureMoment,
    diagnostic_result: DiagnosticVectorResult,
) -> str:
    warning = [item for item in checked if item.status == "предаварийное"]
    critical = [item for item in checked if item.status == "аварийное"]
    static_symptoms = [item.model_dump() for item in diagnostic_result.identified_symptoms]
    static_recommendations = _collect_recommendations(diagnostic_result)

    return (
        "Сгенерируй инженерный отчет о работе котла ТП-100.\n"
        "ОБЯЗАТЕЛЬНЫЙ ФОРМАТ: только обычный текст. Не используй Markdown, HTML, XML, таблицы, символы разметки, <br>, списки с вертикальными чертами, знаки разделения между разделами.\n"
        "Разделы выводи обычными строками: Заголовок, Список обнаруженных отклонений, Момент возникновения сбоя, Локализация, Идентификация, Рекомендации по исправлению неисправностей, Итоговое заключение. Разделы должны быть разделены пустой строкой, НИ В КОЕМ СЛУЧАЕ не пиши дополнительных знаков разделения.\n"
        "Не выводи полный перечень всех проверенных параметров. В списке отклонений выводи только параметры в предаварийном или аварийном состоянии.\n"
        "Отклонения должны быть только в таком стиле: Давление на низкой стороне РОУ - Предаварийное! Параметр вырос на 7.2%.\n"
        "В разделе 'Локализация' укажи только конкретную часть объекта управления.\n"
        "В разделе 'Идентификация' выведи список идентифицированных симптомов из готовых данных.\n"
        "Обязательно добавь отдельный раздел 'Момент возникновения сбоя'. В нем назови точное время первого выхода параметра из нормы, если оно передано системой.\n"
        "Не делай таблицы ни при каких условиях.\n\n"
        "ТВОЯ РОЛЬ: только собрать связный текст из готовых данных. Не придумывай новые диагнозы, симптомы, причины и рекомендации.\n"
        "Рекомендации можно брать ТОЛЬКО из поля 'Статические рекомендации'. Не добавляй своих рекомендаций.\n"
        "Диагнозы и симптомы можно брать ТОЛЬКО из поля 'Идентифицированные симптомы'.\n\n"
        "Данные для LLM уже агрегированы пороговым методом. Сырые временные ряды не используются, но переданы рассчитанные моменты первого выхода параметров из нормы.\n\n"
        f"Предаварийное: {[item.model_dump() for item in warning]}\n"
        f"Аварийное: {[item.model_dump() for item in critical]}\n"
        f"Отклонения: {[item.model_dump() for item in deviations]}\n\n"
        f"Момент возникновения сбоя, рассчитанный системой: {failure_moment.model_dump()}.\n"
        f"Диагностический вектор: {diagnostic_result.vector}.\n"
        f"Локализация: {diagnostic_result.localization.model_dump()}.\n"
        f"Идентифицированные симптомы: {static_symptoms}.\n"
        f"Статические рекомендации: {static_recommendations}.\n\n"
        "Собери отчет только из этих структурированных данных."
    )


def _format_symptoms(diagnostic_result: DiagnosticVectorResult) -> str:
    if not diagnostic_result.identified_symptoms:
        return "Идентифицированные симптомы не найдены."
    lines = []
    for index, symptom in enumerate(diagnostic_result.identified_symptoms, start=1):
        lines.append(
            f"{index}. {symptom.name}: {'; '.join(symptom.symptoms)}."
        )
    return "\n".join(lines)


def _format_recommendations(diagnostic_result: DiagnosticVectorResult) -> str:
    recommendations = _collect_recommendations(diagnostic_result)
    if not recommendations:
        return "Продолжить штатный мониторинг."
    return "\n".join(f"{index}. {recommendation}" for index, recommendation in enumerate(recommendations, start=1))


def _collect_recommendations(diagnostic_result: DiagnosticVectorResult) -> list[str]:
    seen: set[str] = set()
    recommendations: list[str] = []
    for symptom in diagnostic_result.identified_symptoms:
        for recommendation in symptom.recommendations:
            if recommendation not in seen:
                seen.add(recommendation)
                recommendations.append(recommendation)
    return recommendations


def infer_diagnosis(checked: list[ParameterClassification], deviations: list[Deviation]) -> dict:
    statuses = {item.parameter: item.status for item in checked}

    def bad(name: str) -> bool:
        return statuses.get(name) in {"предаварийное", "аварийное"}

    def critical(name: str) -> bool:
        return statuses.get(name) == "аварийное"

    if not deviations:
        return {
            "name": "Нормальная работа котла",
            "interpretation": "Параметры не вышли за установленные пороги. Признаков нарушения режима работы не выявлено.",
            "actions": ["Продолжить штатную эксплуатацию.", "Сохранить текущий режим мониторинга."],
            "conclusion": "Работа котла оценивается как нормальная.",
        }

    if critical("Давление в барабане") and bad("Давление в паросборной камере") and bad("Расход РОУ"):
        return {
            "name": "Вероятное нарушение герметичности основного барабана",
            "interpretation": "Снижение или неустойчивость давления барабана вместе с изменением давления паросборной камеры и ростом расхода РОУ указывает на потерю герметичности или неконтролируемый переток пара.",
            "actions": [
                "Снизить нагрузку котла до безопасного уровня.",
                "Проверить люки, фланцевые соединения, импульсные линии и арматуру барабана.",
                "Проверить достоверность датчиков давления барабана и паросборной камеры.",
                "При подтверждении утечки вывести котел из работы для устранения дефекта.",
            ],
            "conclusion": "Наиболее вероятна потеря герметичности барабана; продолжение работы без проверки опасно.",
        }

    if critical("Температура перегретого пара") and (bad("Температура после РОУ") or bad("Температура после БРОУ")):
        return {
            "name": "Вероятный перегрев пара и поверхностей нагрева",
            "interpretation": "Рост температуры перегретого пара вместе с повышением температур после РОУ/БРОУ указывает на перегрев тракта пара и тепловую перегрузку поверхностей нагрева.",
            "actions": [
                "Ограничить тепловую нагрузку и стабилизировать подачу топлива.",
                "Проверить расход питательной воды и работу впрысков/охладителей.",
                "Проверить загрязнение поверхностей нагрева и состояние горелочных устройств.",
                "Не допускать дальнейшего роста температуры перегретого пара.",
            ],
            "conclusion": "Режим соответствует перегреву пара; требуется немедленное снижение тепловой нагрузки и проверка охлаждения.",
        }

    if critical("Давление в барабане") and critical("Давление в паросборной камере") and (bad("Расход РОУ") or bad("Расход БРОУ")):
        return {
            "name": "Вероятная неисправность предохранительного или сбросного клапана",
            "interpretation": "Одновременный рост давления при недостаточном или неправильном изменении расхода через РОУ/БРОУ указывает на нарушение сброса давления.",
            "actions": [
                "Немедленно проверить готовность предохранительных клапанов и сбросной арматуры.",
                "Ограничить нагрузку котла до восстановления устойчивого давления.",
                "Проверить исполнительные механизмы РОУ/БРОУ, приводы, уставки и импульсные линии.",
                "При сохранении роста давления остановить котел по аварийному регламенту.",
            ],
            "conclusion": "Наиболее вероятна неисправность контура сброса давления; режим потенциально аварийный.",
        }

    if critical("Производительность котла") and bad("Температура перегретого пара") and bad("Расход РОУ"):
        return {
            "name": "Вероятное нарушение режима горения и неустойчивая работа топки",
            "interpretation": "Сильные отклонения производительности, температуры пара, давления и расходов РОУ/БРОУ характерны для неустойчивого горения и колебаний тепловыделения в топке.",
            "actions": [
                "Стабилизировать соотношение топливо-воздух.",
                "Проверить горелки, тягу, подачу топлива и работу дутьевых/дымососных механизмов.",
                "Снизить нагрузку до исчезновения колебаний температуры и давления.",
                "Проверить систему автоматики горения и контуры регулирования.",
            ],
            "conclusion": "Наиболее вероятна неустойчивая работа топки; требуется стабилизация горения и ограничение нагрузки.",
        }

    names = ", ".join(item.parameter for item in deviations[:4])
    return {
        "name": "Отклонение технологического режима котла",
        "interpretation": f"Ключевые отклонения затрагивают параметры: {names}. Режим нельзя считать штатным; требуется устранить первопричину наиболее сильных отклонений.",
        "actions": [
            "Снизить нагрузку при наличии аварийных отклонений.",
            "Проверить датчики параметров с наибольшим процентом отклонения.",
            "Проверить соответствующие регулирующие клапаны, приводы и контуры автоматики.",
        ],
        "conclusion": "Обнаружено нарушение технологического режима, требующее оперативной проверки.",
    }


def _status_label(status: str) -> str:
    labels = {
        "нормальное": "Нормальное",
        "предаварийное": "Предаварийное!",
        "аварийное": "Аварийное!",
        "нет данных": "Нет данных",
    }
    return labels.get(status, status.capitalize())


def _sanitize_plain_text(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
