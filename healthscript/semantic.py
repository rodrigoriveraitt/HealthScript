from dataclasses import dataclass
from .ast import Action, Assignment, BinaryOp, Literal, Node, Program, Rule, UnaryOp, Variable


class SemanticError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column


# Variables tomadas del documento de HealthScript.
KNOWN_VARIABLES = {
    'GLUCOSA', 'GLUCOSA_AYUNO',
    'PRESION_SISTOLICA', 'PRESION_DIASTOLICA',
    'PESO', 'ALTURA', 'IMC',
    'CALORIAS', 'AGUA', 'PROTEINA', 'ACTIVIDAD_FISICA',
    'NIVEL_RIESGO',
}
NUMERIC_VARIABLES = KNOWN_VARIABLES - {'NIVEL_RIESGO'}


@dataclass
class SemanticReport:
    symbols: dict[str, object]
    errors: list[str]
    warnings: list[str]


def analyze(program: Program) -> SemanticReport:
    symbols: dict[str, object] = {}
    errors: list[str] = []
    warnings: list[str] = []

    def error(message: str, node: Node):
        errors.append(f'Error semántico [L{node.line}:C{node.column}]: {message}')

    def check_expr(node: Node, require_boolean: bool = False) -> str:
        if isinstance(node, Literal):
            if isinstance(node.value, bool):
                result = 'bool'
            elif isinstance(node.value, (int, float)):
                result = 'number'
            else:
                result = 'string'
        elif isinstance(node, Variable):
            if node.name not in KNOWN_VARIABLES:
                error(f'La variable {node.name} no existe en el lenguaje HealthScript.', node)
                return 'unknown'
            if node.name != 'NIVEL_RIESGO' and node.name not in symbols:
                error(f'La variable {node.name} no tiene un valor registrado para esta ejecución.', node)
            result = 'string' if node.name == 'NIVEL_RIESGO' else 'number'
        elif isinstance(node, UnaryOp):
            inner = check_expr(node.operand)
            if inner != 'number':
                error(f'El operador {node.operator} requiere un valor numérico.', node)
            result = 'number'
        elif isinstance(node, BinaryOp):
            left_type = check_expr(node.left)
            right_type = check_expr(node.right)
            if node.operator in ('+', '-', '*', '/'):
                if left_type != 'number' or right_type != 'number':
                    error(f'El operador {node.operator} solo acepta números.', node)
                result = 'number'
            elif node.operator in ('>', '<', '>=', '<='):
                if left_type != 'number' or right_type != 'number':
                    error(f'La comparación {node.operator} requiere operandos numéricos.', node)
                result = 'bool'
            elif node.operator in ('==', '!='):
                result = 'bool'
            elif node.operator in ('Y', 'O'):
                if left_type != 'bool' or right_type != 'bool':
                    error(f'El operador lógico {node.operator} requiere expresiones booleanas.', node)
                result = 'bool'
            else:
                result = 'unknown'
        else:
            result = 'unknown'
        if require_boolean and result != 'bool':
            error('La condición de SI debe producir VERDADERO o FALSO.', node)
        return result

    def check_assignment(stmt: Assignment):
        if stmt.name not in KNOWN_VARIABLES:
            error(f'La variable {stmt.name} no está definida en HealthScript.', stmt)
            return
        value_type = check_expr(stmt.expression)
        expected = 'string' if stmt.name == 'NIVEL_RIESGO' else 'number'
        if value_type != expected:
            error(f'{stmt.name} requiere un valor {"de texto" if expected == "string" else "numérico"}.', stmt)
        symbols[stmt.name] = None

    for statement in program.statements:
        if isinstance(statement, Assignment):
            check_assignment(statement)
        elif isinstance(statement, Rule):
            check_expr(statement.condition, require_boolean=True)
            for action in statement.actions:
                if action.kind == 'ASIGNACION' and action.assignment:
                    check_assignment(action.assignment)
                elif action.kind in ('ALERTA', 'RECOMENDAR'):
                    if not isinstance(action.message, str):
                        error(f'{action.kind} requiere un mensaje textual.', action)

    if not program.patient_id:
        warnings.append('No se especificó PACIENTE. El programa puede ejecutarse, pero se recomienda incluirlo.')

    # Validar que haya al menos una regla ejecutable.
    if not any(isinstance(s, Rule) for s in program.statements):
        warnings.append('No se encontró ninguna regla SI ... ENTONCES ... FIN.')

    return SemanticReport(symbols=symbols, errors=errors, warnings=warnings)
