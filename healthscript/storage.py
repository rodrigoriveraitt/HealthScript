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
    Reglas heurísticas:
      - GRAVE: GLUCOSA >= 250 o IMC >= 40 o PRESION_SISTOLICA >= 180
      - MODERADO: GLUCOSA > 180 o IMC >= 30 o PRESION_SISTOLICA > 140
      - MEDIO: GLUCOSA > 140 o IMC >= 25 o PRESION_SISTOLICA > 120
    """
    if not values:
        return None

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


def make_patient_record(patient_id: str, values: dict, alerts: list[str], recommendations: list[str], triggered_rules: list[str]) -> dict:
    return {
        'patient_id': patient_id,
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'values': values,
        'alerts': alerts,
        'recommendations': recommendations,
        'triggered_rules': triggered_rules,
        'severity': _compute_severity(values) or 'MEDIO',
    }


def save_patient(record: dict) -> bool:
    """Guarda una ejecución/paciente (añade al final del archivo JSON)."""
    items = _load_all()
    items.append(record)
    return _save_all(items)


def list_patients() -> list:
    """Devuelve la lista completa de pacientes guardados."""
    return _load_all()


def execute(program: Program) -> ExecutionResult:
    result = ExecutionResult(patient_id=program.patient_id)

    for statement in program.statements:
        if isinstance(statement, Assignment):
            result.values[statement.name] = eval_expr(statement.expression, result.values)
            result.trace.append(f'Asignación ejecutada: {statement.name} = {result.values[statement.name]}')

    for statement in program.statements:
        if not isinstance(statement, Rule):
            continue
        rule_label = statement.name or f'Regla en línea {statement.line}'
        condition = eval_expr(statement.condition, result.values)
        result.trace.append(f'Evaluando {rule_label}: {condition}')
        if condition is True:
            result.triggered_rules.append(rule_label)
            result.trace.append(f'Condición verdadera → ejecutando acciones de {rule_label}')
            for action in statement.actions:
                execute_action(action, result)
        else:
            result.trace.append(f'Condición falsa → {rule_label} no genera acciones')

    result.severity = _compute_severity(result.values) or 'MEDIO'
    try:
        record = make_patient_record(
            patient_id=result.patient_id or 'SIN_ID',
            values=result.values,
            alerts=result.alerts,
            recommendations=result.recommendations,
            triggered_rules=result.triggered_rules,
        )
        result.saved = save_patient(record)
        result.trace.append(f'Historial guardado: {result.saved}')
    except Exception as exc:
        result.trace.append(f'No se pudo guardar el historial del paciente: {exc}')
        result.saved = False

    return result


def execute_action(action: Action, result: ExecutionResult) -> None:
    if action.kind == 'ALERTA':
        result.alerts.append(action.message or '')
        result.trace.append(f'ALERTA: {action.message}')
    elif action.kind == 'RECOMENDAR':
        result.recommendations.append(action.message or '')
        result.trace.append(f'RECOMENDAR: {action.message}')
    elif action.kind == 'ASIGNACION' and action.assignment:
        value = eval_expr(action.assignment.expression, result.values)
        result.values[action.assignment.name] = value
        result.trace.append(f'Acción ejecutada: {action.assignment.name} = {value}')


def eval_expr(node, values):
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, Variable):
        if node.name not in values:
            raise RuntimeErrorHS(f'Variable no inicializada: {node.name}')
        return values[node.name]
    if isinstance(node, UnaryOp):
        value = eval_expr(node.operand, values)
        return +value if node.operator == '+' else -value
    if isinstance(node, BinaryOp):
        left = eval_expr(node.left, values)
        right = eval_expr(node.right, values)
        if node.operator == '+': return left + right
        if node.operator == '-': return left - right
        if node.operator == '*': return left * right
        if node.operator == '/':
            if right == 0:
                raise RuntimeErrorHS('División entre cero.')
            return left / right
        if node.operator == '>': return left > right
        if node.operator == '<': return left < right
        if node.operator == '>=': return left >= right
        if node.operator == '<=': return left <= right
        if node.operator == '==': return left == right
        if node.operator == '!=': return left != right
        if node.operator == 'Y': return bool(left) and bool(right)
        if node.operator == 'O': return bool(left) or bool(right)
    raise RuntimeErrorHS('Expresión no soportada.')
