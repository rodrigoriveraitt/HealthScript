from dataclasses import dataclass, field
from typing import Optional
from .ast import Action, Assignment, BinaryOp, Literal, Program, Rule, UnaryOp, Variable


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
