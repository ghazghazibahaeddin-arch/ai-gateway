from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

_analyzer = None
_anonymizer = None


def _get_engines():
    global _analyzer, _anonymizer
    if _analyzer is None:
        _analyzer = AnalyzerEngine()
        _anonymizer = AnonymizerEngine()
    return _analyzer, _anonymizer


ENTITY_TYPES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
    "LOCATION",
    "NRP",
    "MEDICAL_LICENSE",
    "US_SSN",
    "US_PASSPORT",
    "US_DRIVER_LICENSE",
    "US_BANK_NUMBER",
    "UK_NHS",
    "CRYPTO",
]

MASK_MAP = {
    "PERSON": "[NAME]",
    "EMAIL_ADDRESS": "[EMAIL]",
    "PHONE_NUMBER": "[PHONE]",
    "CREDIT_CARD": "[CREDIT_CARD]",
    "IBAN_CODE": "[IBAN]",
    "IP_ADDRESS": "[IP_ADDRESS]",
    "LOCATION": "[LOCATION]",
    "NRP": "[NRP]",
    "MEDICAL_LICENSE": "[MED_LICENSE]",
    "US_SSN": "[SSN]",
    "US_PASSPORT": "[PASSPORT]",
    "US_DRIVER_LICENSE": "[DL]",
    "US_BANK_NUMBER": "[BANK_ACCOUNT]",
    "UK_NHS": "[NHS]",
    "CRYPTO": "[CRYPTO_ADDR]",
}


def analyze_and_redact(text: str) -> tuple[str, list[dict]]:
    if not text or not text.strip():
        return text, []

    analyzer, anonymizer = _get_engines()

    results = analyzer.analyze(
        text=text,
        entities=ENTITY_TYPES,
        language="en",
        score_threshold=0.35,
    )

    if not results:
        return text, []

    operators = {
        entity: OperatorConfig("replace", {"new_value": mask})
        for entity, mask in MASK_MAP.items()
    }
    operators["DEFAULT"] = OperatorConfig("replace", {"new_value": "[REDACTED]"})

    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=operators,
    )

    findings = [
        {
            "entity_type": r.entity_type,
            "score": round(r.score, 3),
            "start": r.start,
            "end": r.end,
            "original_length": r.end - r.start,
            "masked_as": MASK_MAP.get(r.entity_type, "[REDACTED]"),
        }
        for r in results
    ]

    return anonymized.text, findings
