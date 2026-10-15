import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from healthscript.lexer import lex
from healthscript.parser import parse
from healthscript.semantic import analyze
from healthscript.interpreter import execute


SOURCE = '''PACIENTE "T001"
GLUCOSA = 195
IMC = 31
PRESION_SISTOLICA = 120
AGUA = 1200

REGLA "RIESGO"
SI IMC >= 30 Y GLUCOSA > 180 ENTONCES
    NIVEL_RIESGO = "ALTO"
    ALERTA "Atención preventiva"
FIN

SI AGUA < 1500 ENTONCES
    RECOMENDAR "Revisar consumo de líquidos"
FIN
'''


def test_pipeline_core():
    tokens = lex(SOURCE)
    program = parse(tokens)
    semantic = analyze(program)
    assert not semantic.errors
    result = execute(program)
    assert result.patient_id == 'T001'
    assert result.values['NIVEL_RIESGO'] == 'ALTO'
    assert len(result.alerts) == 1
    assert len(result.recommendations) == 1


if __name__ == '__main__':
    test_pipeline_core()
    print('OK - prueba del intérprete superada')
