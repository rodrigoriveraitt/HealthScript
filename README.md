# HealthScript · Intérprete de monitoreo preventivo

Proyecto académico para **Lenguajes y Autómatas II** basado en el documento del proyecto HealthScript.

## Qué implementa

- Lenguaje específico de dominio (DSL) para reglas de monitoreo preventivo.
- Análisis léxico: conversión del código a tokens.
- Análisis sintáctico: validación de la gramática.
- AST (árbol sintáctico abstracto).
- Análisis semántico: variables permitidas y tipos.
- Intérprete: evaluación y ejecución de reglas.
- Motor de reglas: alertas, recomendaciones y nivel de riesgo.
- Editor visual propio.
- Dashboard con indicadores.
- Visor de tokens, AST y trazabilidad de ejecución.
- Manejo de errores léxicos, sintácticos, semánticos y de ejecución.

## Tecnologías

- Python 3.10+ (probado con Python 3.13 en desarrollo).
- Tkinter / ttk para la interfaz.
- **Sin base de datos y sin paquetes externos obligatorios.**
- Todo puede abrirse, editarse y ejecutarse desde Visual Studio Code.

## Ejecutar en Mac desde VS Code

1. Abre la carpeta `HealthScript_Project` en Visual Studio Code.
2. Abre la terminal integrada de VS Code.
3. Comprueba Python:

```bash
python3 --version
```

4. Ejecuta la aplicación:

```bash
python3 main.py
```

### Prueba del intérprete sin abrir la interfaz

```bash
python3 tests/test_interpreter.py
```

Debe aparecer:

```text
OK - prueba del intérprete superada
```

## Gramática principal

```text
programa   -> paciente? declaraciones*
paciente   -> PACIENTE STRING
regla      -> REGLA STRING SI condicion ENTONCES acciones FIN
             | SI condicion ENTONCES acciones FIN
asignacion -> IDENT = expresion
accion     -> ALERTA STRING
             | RECOMENDAR STRING
             | asignacion
condicion  -> expresion
```

La implementación usa un parser recursivo con precedencia para expresiones, de modo que las operaciones y condiciones se convierten en un AST.

## Ejemplo

```text
PACIENTE "P001"
GLUCOSA = 195
PRESION_SISTOLICA = 145
IMC = 31.2

SI GLUCOSA > 180 ENTONCES
    ALERTA "Nivel de glucosa elevado"
FIN
```

## Estructura

```text
HealthScript_Project/
├── main.py
├── README.md
├── examples/
│   └── demo.hs
├── healthscript/
│   ├── ast.py
│   ├── interpreter.py
│   ├── lexer.py
│   ├── parser.py
│   ├── pipeline.py
│   ├── semantic.py
│   └── ui.py
└── tests/
    └── test_interpreter.py
```

## Nota académica

El proyecto trata HealthScript como herramienta de monitoreo y apoyo preventivo, no como sustituto de un médico ni como sistema de diagnóstico.
