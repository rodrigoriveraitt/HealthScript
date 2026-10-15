from dataclasses import dataclass, field
from typing import Optional
from .ast import Program, ast_to_text
from .interpreter import ExecutionResult, execute
from .lexer import LexicalError, Token, lex
from .parser import ParseError, parse
from .semantic import SemanticReport, analyze


@dataclass
class PipelineResult:
    success: bool = False
    tokens: list[Token] = field(default_factory=list)
    program: Optional[Program] = None
    semantic: Optional[SemanticReport] = None
    execution: Optional[ExecutionResult] = None
    stage_messages: dict[str, str] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)
    ast_text: str = ''


def run_pipeline(source: str, execute_program: bool = True) -> PipelineResult:
    result = PipelineResult()

    # 1. Análisis léxico
    try:
        result.tokens = lex(source)
        result.stage_messages['Léxico'] = f'Completado · {max(0, len(result.tokens)-1)} tokens'
    except LexicalError as exc:
        result.stage_messages['Léxico'] = 'Error'
        result.diagnostics.append(f'Error léxico [L{exc.line}:C{exc.column}]: {exc.message}')
        return result

    # 2. Análisis sintáctico
    try:
        result.program = parse(result.tokens)
        result.stage_messages['Sintáctico'] = 'Completado · gramática válida'
    except ParseError as exc:
        result.stage_messages['Sintáctico'] = 'Error'
        result.diagnostics.append(f'Error sintáctico [L{exc.line}:C{exc.column}]: {exc.message}')
        return result

    # 3. Análisis semántico
    result.semantic = analyze(result.program)
    if result.semantic.errors:
        result.stage_messages['Semántico'] = 'Error'
        result.diagnostics.extend(result.semantic.errors)
        if result.semantic.warnings:
            result.diagnostics.extend('Advertencia: ' + x for x in result.semantic.warnings)
        return result
    result.stage_messages['Semántico'] = 'Completado · símbolos consistentes'
    result.diagnostics.extend('Advertencia: ' + x for x in result.semantic.warnings)

    result.ast_text = ast_to_text(result.program)

    # 4. Interpretación
    if execute_program:
        try:
            result.execution = execute(result.program)
            result.stage_messages['Interpretación'] = 'Completado · programa ejecutado'
            result.success = True
        except Exception as exc:
            result.stage_messages['Interpretación'] = 'Error'
            result.diagnostics.append(f'Error de ejecución: {exc}')
            return result
    else:
        result.stage_messages['Interpretación'] = 'Lista para ejecutar'
        result.success = True

    return result
