from dataclasses import dataclass, field
from typing import Optional
from .ast import Action, Assignment, BinaryOp, Literal, Program, Rule, UnaryOp, Variable
import os
import json
from datetime import datetime


class RuntimeErrorHS(Exception):
    pass


@dataclass
class ExecutionResult:
    patient_id: Optional[str]
    values: dict[str, object] = field(default_factory=dict)
    alerts: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    triggered_rules: list[str] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)
    severity: Optional[str] = None
    saved: bool = False


def _compute_severity(values: dict[str, object]) -> Optional[str]:
    """Determina un nivel de gravedad a partir de las mediciones.

    Niveles (de menor a mayor): MEDIO, MODERADO, GRAVE
    Reglas heurísticas (configurables aquí):
      - GRAVE: GLUCOSA >= 250 o IMC >= 40 o PRESION_SISTOLICA >= 180
      - MODERADO: GLUCOSA > 180 o IMC >= 30 o PRESION_SISTOLICA > 140
      - MEDIO: GLUCOSA > 140 o IMC >= 25 o PRESION_SISTOLICA > 120
      - Si no hay datos relevantes, devuelve None
    """
    if not values:
        return None

    # Extraer valores con tolerancia (pueden no estar definidos)
    glucosa = values.get('GLUCOSA')
    imc = values.get('IMC')
    presion = values.get('PRESION_SISTOLICA')

    try:
        if glucosa is not None and float(glucosa) >= 250:
            return 'GRAVE'
        if imc is not None and float(imc) >= 40:
            return 'GRAVE'
        if presion is not None and float(presion) >= 180:
            return 'GRAVE'

        if glucosa is not None and float(glucosa) > 180:
            return 'MODERADO'
        if imc is not None and float(imc) >= 30:
            return 'MODERADO'
        if presion is not None and float(presion) > 140:
            return 'MODERADO'

        if glucosa is not None and float(glucosa) > 140:
            return 'MEDIO'
        if imc is not None and float(imc) >= 25:
            return 'MEDIO'
        if presion is not None and float(presion) > 120:
            return 'MEDIO'
    except (TypeError, ValueError):
        # Si hay valores no numéricos, no determinamos gravedad aquí
        return None

    return None


def _data_file_path() -> str:
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    data_dir = os.path.join(base, 'data')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, 'patients.json')


def _load_all() -> list:
    path = _data_file_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _save_all(items: list) -> bool:
    path = _data_file_path()
    try:
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def save_patient(record: dict) -> bool:
    """Guarda una ejecución/paciente (añade al final del archivo JSON).

    El registro debe contener como mínimo: patient_id, values, alerts, recommendations,
    severity y timestamp. Devuelve True si se guardó correctamente.
    """
    items = _load_all()
    items.append(record)
    return _save_all(items)


def list_patients() -> list:
    """Devuelve la lista completa de pacientes guardados."""
    return _load_all()
