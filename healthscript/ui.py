import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from .pipeline import PipelineResult, run_pipeline
from .storage import list_patients

COLORS = {
    'bg': '#F5F7FB',
    'panel': '#FFFFFF',
    'sidebar': '#101827',
    'sidebar_muted': '#8D9AAF',
    'text': '#1B2430',
    'muted': '#687386',
    'primary': '#2D6CDF',
    'primary_dark': '#1F54B0',
    'success': '#1B8C5A',
    'success_bg': '#EAF8F1',
    'warning': '#B66A00',
    'warning_bg': '#FFF5E6',
    'danger': '#C44444',
    'danger_bg': '#FDEEEE',
    'border': '#E2E7EF',
    'editor_bg': '#111827',
    'editor_text': '#E7EDF5',
}

SAMPLE = '''PACIENTE "P001"
GLUCOSA = 195
PRESION_SISTOLICA = 145
PRESION_DIASTOLICA = 90
IMC = 31.2
ACTIVIDAD_FISICA = 30
AGUA = 1800
PROTEINA = 85

REGLA "RIESGO_METABOLICO"
SI IMC >= 30 Y GLUCOSA > 180 ENTONCES
    NIVEL_RIESGO = "ALTO"
    ALERTA "Se detectaron indicadores elevados; se recomienda valoración profesional"
FIN

SI GLUCOSA > 180 ENTONCES
    ALERTA "Nivel de glucosa elevado"
FIN

SI PRESION_SISTOLICA > 140 ENTONCES
    ALERTA "Presión arterial elevada"
FIN

SI AGUA < 1500 ENTONCES
    RECOMENDAR "Revisar consumo de líquidos"
FIN
'''


class HealthScriptApp(tk.Tk):
    """Interfaz principal de HealthScript.

    El formulario de paciente funciona como la capa de captura de datos.
    Esos datos se transforman a código HealthScript y después recorren el
    pipeline académico: lexer -> parser -> semántica -> intérprete.
    No hay base de datos externa; los datos viven en la sesión actual,
    pero con la extensión añadida se persiste el historial en disco.
    """

    def __init__(self):
        super().__init__()
        self.title('HealthScript · Intérprete de monitoreo preventivo')
        self.geometry('1460x920')
        self.minsize(1200, 760)
        self.configure(bg=COLORS['bg'])

        self.current_result: Optional[PipelineResult] = None
        self.nav_buttons = {}
        self.patient_vars = {}
        # UI state for patients view
        self.patient_filter = tk.StringVar(value='TODOS')
        self.patient_tree = None
        self.patient_detail = None
        self.patients_frame = None

        self._build_styles()
        self._build_layout()
        self._load_sample()
        # Build patients section after other sections are constructed
        self._build_patients_section()
        self._set_section('Dashboard')

    # ------------------------------------------------------------------
    # Styles / layout
    # ------------------------------------------------------------------
    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame', background=COLORS['bg'])
        style.configure('Panel.TFrame', background=COLORS['panel'])
        style.configure('TLabel', background=COLORS['bg'], foreground=COLORS['text'], font=('SF Pro Display', 12))
        style.configure('Treeview', background=COLORS['panel'], fieldbackground=COLORS['panel'], foreground=COLORS['text'], rowheight=35, borderwidth=0)
        style.configure('Treeview.Heading', background='#F0F3F8', foreground=COLORS['muted'], font=('SF Pro Display', 11, 'bold'), borderwidth=0)
        style.map('Treeview', background=[('selected', '#EAF0FE')], foreground=[('selected', COLORS['primary_dark'])])
        style.configure('TNotebook', background=COLORS['panel'], borderwidth=0)
        style.configure('TNotebook.Tab', background='#EEF2F7', foreground=COLORS['muted'], padding=(16, 9), font=('SF Pro Display', 11, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', COLORS['panel'])], foreground=[('selected', COLORS['primary_dark'])])
        style.configure('Primary.TButton', background=COLORS['primary'], foreground='white', borderwidth=0, padding=(15, 9), font=('SF Pro Display', 12, 'bold'))
        style.map('Primary.TButton', background=[('active', COLORS['primary_dark'])])
        style.configure('Secondary.TButton', background='#EEF2F7', foreground=COLORS['text'], borderwidth=0, padding=(13, 8), font=('SF Pro Display', 11, 'bold'))
        style.map('Secondary.TButton', background=[('active', '#E2E7EF')])
        style.configure('TEntry', fieldbackground='white', foreground=COLORS['text'], padding=7)

    def _build_layout(self):
        self.sidebar = tk.Frame(self, bg=COLORS['sidebar'], width=250)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=COLORS['sidebar'])
        brand.pack(fill='x', padx=24, pady=(24, 26))
        logo = tk.Canvas(brand, width=42, height=42, bg=COLORS['sidebar'], highlightthickness=0)
        logo.pack(side='left')
        logo.create_oval(2, 2, 40, 40, fill=COLORS['primary'], outline='')
        logo.create_text(21, 21, text='HS', fill='white', font=('SF Pro Display', 12, 'bold'))
        brand_text = tk.Frame(brand, bg=COLORS['sidebar'])
        brand_text.pack(side='left', padx=(11, 0))
        tk.Label(brand_text, text='HealthScript', bg=COLORS['sidebar'], fg='white', font=('SF Pro Display', 14, 'bold')).pack(anchor='w')
        tk.Label(brand_text, text='INTÉRPRETE · v2.0', bg=COLORS['sidebar'], fg=COLORS['sidebar_muted'], font=('SF Pro Display', 8, 'bold')).pack(anchor='w')

        tk.Label(self.sidebar, text='PLATAFORMA', bg=COLORS['sidebar'], fg='#5F6C80', font=('SF Pro Display', 8, 'bold')).pack(anchor='w', padx=25, pady=(0, 10))
        # include Pacientes in navigation
        for label, icon in [('Dashboard', '▦'), ('Registro de paciente', '✚'), ('Editor HealthScript', '⌘'), ('Análisis', '◈'), ('Pacientes', '◉')]:
            self._nav_button(label, icon)

        tk.Label(self.sidebar, text='PROYECTO', bg=COLORS['sidebar'], fg='#5F6C80', font=('SF Pro Display', 8, 'bold')).pack(anchor='w', padx=25, pady=(28, 10))
        self._nav_button('Documentación', 'i')

        bottom = tk.Frame(self.sidebar, bg='#0D1420')
        bottom.pack(side='bottom', fill='x')
        tk.Label(bottom, text='Lenguajes y Autómatas II', bg='#0D1420', fg='white', font=('SF Pro Display', 9, 'bold')).pack(anchor='w', padx=20, pady=(16, 2))
        tk.Label(bottom, text='Python · Tkinter · Sin BD externa', bg='#0D1420', fg=COLORS['sidebar_muted'], font=('SF Pro Display', 8)).pack(anchor='w', padx=20, pady=(0, 16))

        self.content = tk.Frame(self, bg=COLORS['bg'])
        self.content.pack(side='left', fill='both', expand=True)

        self.dashboard_frame = self._build_dashboard()
        self.patient_frame = self._build_patient_form()
        self.editor_frame = self._build_editor()
        self.analysis_frame = self._build_analysis()
        self.docs_frame = self._build_docs()

        self.pipeline_var = tk.StringVar(value='Listo para analizar')
        self.status_label = tk.Label(self.content, textvariable=self.pipeline_var, bg='#101827', fg='#D9E2F0', anchor='w', font=('SF Pro Display', 9))
        self.status_label.pack(side='bottom', fill='x', ipady=8)

    def _nav_button(self, label, icon):
        btn = tk.Frame(self.sidebar, bg=COLORS['sidebar'], height=42, cursor='hand2')
        btn.pack(fill='x', padx=12, pady=3)
        icon_label = tk.Label(btn, text=icon, bg=COLORS['sidebar'], fg=COLORS['sidebar_muted'], font=('SF Pro Display', 14, 'bold'))
        icon_label.pack(side='left', padx=(13, 11))
        text_label = tk.Label(btn, text=label, bg=COLORS['sidebar'], fg='#AEB8C8', font=('SF Pro Display', 13, 'bold'), anchor='w')
        text_label.pack(side='left', fill='x', expand=True)
        for widget in (btn, icon_label, text_label):
            widget.bind('<Button-1>', lambda e, name=label: self._set_section(name))
        self.nav_buttons[label] = (btn, icon_label, text_label)

    def _base_header_in(self, frame, title, subtitle):
        header = tk.Frame(frame, bg=COLORS['bg'])
        header.pack(fill='x', padx=34, pady=(28, 20))
        left = tk.Frame(header, bg=COLORS['bg'])
        left.pack(side='left')
        tk.Label(left, text=title, bg=COLORS['bg'], fg=COLORS['text'], font=('SF Pro Display', 22, 'bold')).pack(anchor='w')
        tk.Label(left, text=subtitle, bg=COLORS['bg'], fg=COLORS['muted'], font=('SF Pro Display', 10)).pack(anchor='w', pady=(4, 0))
        return header

    def _card(self, parent, title, value, subtitle, accent=None):
        frame = tk.Frame(parent, bg=COLORS['panel'], highlightbackground=COLORS['border'], highlightthickness=1)
        frame.pack(side='left', fill='both', expand=True, padx=(0, 12))
        tk.Label(frame, text=title.upper(), bg=COLORS['panel'], fg=COLORS['muted'], font=('SF Pro Display', 8, 'bold')).pack(anchor='w', padx=18, pady=(16, 5))
        value_label = tk.Label(frame, text=value, bg=COLORS['panel'], fg=accent or COLORS['text'], font=('SF Pro Display', 21, 'bold'))
        value_label.pack(anchor='w', padx=18)
        tk.Label(frame, text=subtitle, bg=COLORS['panel'], fg=COLORS['muted'], font=('SF Pro Display', 9)).pack(anchor='w', padx=18, pady=(2, 16))
        frame.value_label = value_label
        return frame

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------
    def _build_dashboard(self):
        frame = tk.Frame(self.content, bg=COLORS['bg'])
        header = self._base_header_in(frame, 'Dashboard', 'Centro de monitoreo preventivo · sesión local del usuario autorizado')
        actions = tk.Frame(header, bg=COLORS['bg'])
        actions.pack(side='right', anchor='n')
        ttk.Button(actions, text='Nuevo paciente', style='Secondary.TButton', command=lambda: self._set_section('Registro de paciente')).pack(side='left', padx=5)
        ttk.Button(actions, text='▶  Ejecutar', style='Primary.TButton', command=self.execute_source).pack(side='left', padx=5)

        cards = tk.Frame(frame, bg=COLORS['bg'])
        cards.pack(fill='x', padx=34, pady=(0, 16))
        self.card_patient = self._card(cards, 'Paciente', '—', 'Activo en la sesión')
        self.card_alerts = self._card(cards, 'Alertas', '0', 'Reglas activadas', COLORS['danger'])
        self.card_rules = self._card(cards, 'Reglas activadas', '0', 'Evaluadas en la ejecución', COLORS['warning'])
        self.card_status = self._card(cards, 'Estado', 'LISTO', 'Pipeline del intérprete', COLORS['success'])

        middle = tk.Frame(frame, bg=COLORS['bg'])
        middle.pack(fill='both', expand=True, padx=34)
        left = tk.Frame(middle, bg=COLORS['panel'], highlightbackground=COLORS['border'], highlightthickness=1)
        left.pack(side='left', fill='both', expand=True, padx=(0, 12))
        tk.Label(left, text='INDICADORES DEL PACIENTE', bg=COLORS['panel'], fg=COLORS['text'], font=('SF Pro Display', 13, 'bold')).pack(anchor='w', padx=18, pady=(17, 10))
        self.dashboard_tree = ttk.Treeview(left, columns=('indicator', 'value', 'status'), show='headings', height=10)
        self.dashboard_tree.heading('indicator', text='INDICADOR')
        self.dashboard_tree.heading('value', text='VALOR')
        self.dashboard_tree.heading('status', text='ESTADO')
        self.dashboard_tree.column('indicator', width=200, anchor='w')
        self.dashboard_tree.column('value', width=130, anchor='w')
        self.dashboard_tree.column('status', width=190, anchor='w')
        self.dashboard_tree.pack(fill='both', expand=True, padx=14, pady=(0, 14))
        self.dashboard_tree.tag_configure('high', foreground=COLORS['danger'])
        self.dashboard_tree.tag_configure('normal', foreground=COLORS['success'])
        self.dashboard_tree.tag_configure('neutral', foreground=COLORS['muted'])

        right = tk.Frame(middle, bg=COLORS['panel'], highlightbackground=COLORS['border'], highlightthickness=1, width=440)
        right.pack(side='left', fill='both')
        right.pack_propagate(False)
        tk.Label(right, text='RESULTADO DEL MOTOR DE REGLAS', bg=COLORS['panel'], fg=COLORS['text'], font=('SF Pro Display', 13, 'bold')).pack(anchor='w', padx=18, pady=(17, 10))
        self.result_box = tk.Text(right, bg=COLORS['panel'], fg=COLORS['muted'], relief='flat', wrap='word', font=('SF Pro Text', 10), padx=18, pady=4)
        self.result_box.pack(fill='both', expand=True)
        self.result_box.configure(state='disabled')
        self._write_text(self.result_box, 'Aún no hay una ejecución.\n\nVe a “Registro de paciente” para capturar datos o usa “Editor HealthScript” para escribir el lenguaje directamente.')
        return frame

    # ------------------------------------------------------------------
    # Patient registration / automatic source generation
    # ------------------------------------------------------------------
    def _build_patient_form(self):
        frame = tk.Frame(self.content, bg=COLORS['bg'])
        header = self._base_header_in(frame, 'Registro de paciente', 'Captura los datos y deja que HealthScript genere y ejecute las reglas')
        buttons = tk.Frame(header, bg=COLORS['bg'])
        buttons.pack(side='right', anchor='n')
        ttk.Button(buttons, text='Limpiar formulario', style='Secondary.TButton', command=self.clear_patient_form).pack(side='left', padx=4)
        ttk.Button(buttons, text='Generar HealthScript', style='Secondary.TButton', command=self.generate_from_patient).pack(side='left', padx=4)
        ttk.Button(buttons, text='▶  Analizar y ejecutar', style='Primary.TButton', command=self.execute_patient).pack(side='left', padx=4)

        info = tk.Frame(frame, bg=COLORS['panel'], highlightbackground=COLORS['border'], highlightthickness=1)
        info.pack(fill='x', padx=34, pady=(0, 14))
        tk.Label(info, text='FLUJO DE CAPTURA', bg=COLORS['panel'], fg=COLORS['primary'], font=('SF Pro Display', 8, 'bold')).pack(anchor='w', padx=20, pady=(15, 4))
        tk.Label(info, text='Paciente / expediente → Usuario autorizado → HealthScript → Lexer → Parser → Semántica → Intérprete → Alertas',
                 bg=COLORS['panel'], fg=COLORS['text'], font=('SF Pro Display', 13, 'bold')).pack(anchor='w', padx=20, pady=(0, 15))

        body = tk.Frame(frame, bg=COLORS['bg'])
        body.pack(fill='both', expand=True, padx=34, pady=(0, 18))

        form_card = tk.Frame(body, bg=COLORS['panel'], highlightbackground=COLORS['border'], highlightthickness=1)
        form_card.pack(side='left', fill='both', expand=True, padx=(0, 14))
        tk.Label(form_card, text='DATOS DEL PACIENTE', bg=COLORS['panel'], fg=COLORS['text'], font=('SF Pro Display', 13, 'bold')).pack(anchor='w', padx=20, pady=(18, 4))
        tk.Label(form_card, text='Los datos permanecen en la sesión local y no se envían a servicios externos.', bg=COLORS['panel'], fg=COLORS['muted'], font=('SF Pro Display', 9)).pack(anchor='w', padx=20, pady=(0, 12))

        fields = [
            ('patient_id', 'ID del paciente', 'P001'),
            ('GLUCOSA', 'Glucosa', ''),
            ('GLUCOSA_AYUNO', 'Glucosa en ayuno', ''),
            ('PRESION_SISTOLICA', 'Presión sistólica', ''),
            ('PRESION_DIASTOLICA', 'Presión diastólica', ''),
            ('PESO', 'Peso', ''),
            ('ALTURA', 'Altura', ''),
            ('IMC', 'IMC', ''),
            ('CALORIAS', 'Calorías', ''),
            ('AGUA', 'Agua', ''),
            ('PROTEINA', 'Proteína', ''),
            ('ACTIVIDAD_FISICA', 'Actividad física', ''),
        ]
        grid = tk.Frame(form_card, bg=COLORS['panel'])
        grid.pack(fill='both', expand=True, padx=20, pady=(0, 20))

        for index, (key, label, default) in enumerate(fields):
            row, col = divmod(index, 2)
            cell = tk.Frame(grid, bg=COLORS['panel'])
            cell.grid(row=row, column=col, sticky='ew', padx=(0 if col == 0 else 12, 12 if col == 0 else 0), pady=6)
            tk.Label(cell, text=label, bg=COLORS['panel'], fg=COLORS['muted'], font=('SF Pro Display', 8, 'bold')).pack(anchor='w', pady=(0, 3))
            var = tk.StringVar(value=default)
            self.patient_vars[key] = var
            entry = ttk.Entry(cell, textvariable=var, width=24)
            entry.pack(fill='x')

        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        # IMC helper
        helper = tk.Frame(form_card, bg='#F7F9FC', highlightbackground=COLORS['border'], highlightthickness=1)
        helper.pack(fill='x', padx=20, pady=(0, 20))
        tk.Label(helper, text='Cálculo rápido de IMC', bg='#F7F9FC', fg=COLORS['primary'], font=('SF Pro Display', 9, 'bold')).pack(anchor='w', padx=12, pady=(10, 2))
        tk.Label(helper, text='Usa peso (kg) y altura (m). El botón completa el campo IMC.', bg='#F7F9FC', fg=COLORS['muted'], font=('SF Pro Display', 8)).pack(anchor='w', padx=12, pady=(0, 6))
        ttk.Button(helper, text='Calcular IMC', style='Secondary.TButton', command=self.calculate_bmi).pack(anchor='w', padx=12, pady=(0, 10))

        preview_card = tk.Frame(body, bg=COLORS['panel'], highlightbackground=COLORS['border'], highlightthickness=1, width=470)
        preview_card.pack(side='left', fill='both')
        preview_card.pack_propagate(False)
        tk.Label(preview_card, text='HEALTHSCRIPT GENERADO', bg=COLORS['panel'], fg=COLORS['text'], font=('SF Pro Display', 13, 'bold')).pack(anchor='w', padx=16, pady=(18, 4))
        tk.Label(preview_card, text='Esta es la representación que procesará tu intérprete.', bg=COLORS['panel'], fg=COLORS['muted'], font=('SF Pro Display', 9)).pack(anchor='w', padx=16, pady=(0, 8))
        self.generated_preview = tk.Text(preview_card, bg=COLORS['editor_bg'], fg=COLORS['editor_text'], relief='flat', wrap='none', font=('Menlo', 9), padx=12, pady=12)
        self.generated_preview.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        self.generated_preview.configure(state='disabled')
        self._write_text(self.generated_preview, 'Captura los datos y pulsa “Generar HealthScript”.')
        return frame

    def calculate_bmi(self):
        try:
            weight = float(self.patient_vars['PESO'].get().replace(',', '.'))
            height = float(self.patient_vars['ALTURA'].get().replace(',', '.'))
            if weight <= 0 or height <= 0:
                raise ValueError
            bmi = round(weight / (height * height), 1)
            self.patient_vars['IMC'].set(f'{bmi:g}')
            self.pipeline_var.set(f'IMC calculado automáticamente · {bmi:g}')
        except ValueError:
            messagebox.showerror('Datos inválidos', 'Para calcular el IMC captura peso en kg y altura en metros con valores mayores que cero.')

    def clear_patient_form(self):
        for key, var in self.patient_vars.items():
            var.set('P001' if key == 'patient_id' else '')
        self._write_text(self.generated_preview, 'Captura los datos y pulsa “Generar HealthScript”.')
        self.pipeline_var.set('Formulario de paciente limpio')

    def _numeric_source_lines(self):
        lines = []
        for key in ['GLUCOSA', 'GLUCOSA_AYUNO', 'PRESION_SISTOLICA', 'PRESION_DIASTOLICA', 'PESO', 'ALTURA', 'IMC', 'CALORIAS', 'AGUA', 'PROTEINA', 'ACTIVIDAD_FISICA']:
            value = self.patient_vars[key].get().strip().replace(',', '.')
            if not value:
                continue
            try:
                number = float(value)
            except ValueError:
                raise ValueError(f'{key}: usa un valor numérico.')
            if number < 0:
                raise ValueError(f'{key}: el valor no puede ser negativo.')
            rendered = f'{number:g}'
            lines.append(f'{key} = {rendered}')
        return lines

    def build_healthscript_from_form(self):
        patient_id = self.patient_vars['patient_id'].get().strip() or 'SIN_ID'
        if any(ch in patient_id for ch in ['"', '\\']):
            raise ValueError('El ID del paciente no puede contener comillas ni barras invertidas.')

        source = [f'PACIENTE "{patient_id}"']
        assignments = self._numeric_source_lines()
        if not assignments:
            raise ValueError('Captura al menos un indicador numérico del paciente.')
        source.extend(assignments)
        source.append('')

        if self.patient_vars['IMC'].get().strip() and self.patient_vars['GLUCOSA'].get().strip():
            source += [
                'REGLA "RIESGO_METABOLICO"',
                'SI IMC >= 30 Y GLUCOSA > 180 ENTONCES',
                '    NIVEL_RIESGO = "ALTO"',
                '    ALERTA "Se detectaron indicadores elevados; se recomienda valoración profesional"',
                'FIN',
                ''
            ]

        if self.patient_vars['GLUCOSA'].get().strip():
            source += [
                'SI GLUCOSA > 180 ENTONCES',
                '    ALERTA "Nivel de glucosa elevado"',
                'FIN',
                ''
            ]

        if self.patient_vars['GLUCOSA_AYUNO'].get().strip():
            source += [
                'SI GLUCOSA_AYUNO > 126 ENTONCES',
                '    ALERTA "Valor de glucosa en ayuno elevado"',
                'FIN',
                ''
            ]

        if self.patient_vars['PRESION_SISTOLICA'].get().strip():
            source += [
                'SI PRESION_SISTOLICA > 140 ENTONCES',
                '    ALERTA "Presión arterial elevada"',
                'FIN',
                ''
            ]

        if self.patient_vars['IMC'].get().strip():
            source += [
                'SI IMC >= 30 ENTONCES',
                '    ALERTA "IMC elevado"',
                'FIN',
                ''
            ]

        if self.patient_vars['AGUA'].get().strip():
            source += [
                'SI AGUA < 1500 ENTONCES',
                '    RECOMENDAR "Revisar consumo de líquidos"',
                'FIN',
                ''
            ]

        if self.patient_vars['ACTIVIDAD_FISICA'].get().strip():
            source += [
                'SI ACTIVIDAD_FISICA < 30 ENTONCES',
                '    RECOMENDAR "Revisar el nivel de actividad física"',
                'FIN',
                ''
            ]

        return '\n'.join(source).rstrip() + '\n'

    def generate_from_patient(self):
        try:
            source = self.build_healthscript_from_form()
        except ValueError as exc:
            messagebox.showerror('Formulario incompleto', str(exc))
            return None
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', source)
        self._update_line_numbers()
        self._write_text(self.generated_preview, source)
        self.pipeline_var.set('✓ HealthScript generado desde el formulario')
        return source

    def execute_patient(self):
        source = self.generate_from_patient()
        if not source:
            return
        self.execute_source(return_to_dashboard=True)

    # ------------------------------------------------------------------
    # Editor
    # ------------------------------------------------------------------
    def _build_editor(self):
        frame = tk.Frame(self.content, bg=COLORS['bg'])
        header = self._base_header_in(frame, 'Editor HealthScript', 'Escribe reglas, valida la gramática y ejecuta el intérprete')
        buttons = tk.Frame(header, bg=COLORS['bg'])
        buttons.pack(side='right', anchor='n')
        ttk.Button(buttons, text='Limpiar', style='Secondary.TButton', command=self.clear_editor).pack(side='left', padx=4)
        ttk.Button(buttons, text='Ejemplo', style='Secondary.TButton', command=self._load_sample).pack(side='left', padx=4)
        ttk.Button(buttons, text='✓  Validar', style='Secondary.TButton', command=self.validate_source).pack(side='left', padx=4)
        ttk.Button(buttons, text='▶  Ejecutar', style='Primary.TButton', command=self.execute_source).pack(side='left', padx=4)

        work = tk.Frame(frame, bg=COLORS['bg'])
        work.pack(fill='both', expand=True, padx=34, pady=(0, 18))

        editor_panel = tk.Frame(work, bg=COLORS['editor_bg'], highlightbackground=COLORS['border'], highlightthickness=1)
        editor_panel.pack(side='left', fill='both', expand=True, padx=(0, 14))
        top = tk.Frame(editor_panel, bg='#1B2430')
        top.pack(fill='x')
        tk.Label(top, text='HEALTHSCRIPT', bg='#1B2430', fg='#A9B7CA', font=('SF Pro Display', 8, 'bold')).pack(side='left', padx=14, pady=10)
        tk.Label(top, text='Sin dependencias externas', bg='#1B2430', fg='#617088', font=('SF Pro Display', 8)).pack(side='right', padx=14)

        text_wrap = tk.Frame(editor_panel, bg=COLORS['editor_bg'])
        text_wrap.pack(fill='both', expand=True)
        self.line_numbers = tk.Text(text_wrap, width=4, bg='#0D1420', fg='#56647B', relief='flat', font=('Menlo', 11), padx=8, pady=14, state='disabled', takefocus=0)
        self.line_numbers.pack(side='left', fill='y')
        self.editor = tk.Text(text_wrap, bg=COLORS['editor_bg'], fg=COLORS['editor_text'], insertbackground='white', relief='flat', wrap='none', font=('Menlo', 11), padx=12, pady=14, undo=True)
        self.editor.pack(side='left', fill='both', expand=True)
        self.editor.bind('<KeyRelease>', lambda e: self._update_line_numbers())
        self.editor.bind('<MouseWheel>', self._sync_scroll)
        self.editor.bind('<Button-1>', self._sync_scroll)
        self.editor.bind('<Configure>', lambda e: self._update_line_numbers())

        output_panel = tk.Frame(work, bg=COLORS['panel'], highlightbackground=COLORS['border'], highlightthickness=1, width=480)
        output_panel.pack(side='left', fill='both')
        output_panel.pack_propagate(False)
        tk.Label(output_panel, text='ANALIZADOR', bg=COLORS['panel'], fg=COLORS['text'], font=('SF Pro Display', 13, 'bold')).pack(anchor='w', padx=16, pady=(15, 8))
        self.notebook = ttk.Notebook(output_panel)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        self.out_text = self._text_tab('Salida')
        self.tokens_text = self._text_tab('Tokens')
        self.ast_text = self._text_tab('Árbol AST')

        return frame

    def _text_tab(self, name):
        tab = tk.Frame(self.notebook, bg=COLORS['panel'])
        self.notebook.add(tab, text=name)
        text = tk.Text(tab, bg=COLORS['panel'], fg=COLORS['text'], relief='flat', wrap='word', font=('Menlo', 9), padx=12, pady=12)
        text.pack(fill='both', expand=True)
        text.configure(state='disabled')
        return text

    # ------------------------------------------------------------------
    # Analysis / docs
    # ------------------------------------------------------------------
    def _build_analysis(self):
        frame = tk.Frame(self.content, bg=COLORS['bg'])
        self._base_header_in(frame, 'Análisis', 'Visualiza el pipeline del intérprete y el rastreo de ejecución')
        body = tk.Frame(frame, bg=COLORS['bg'])
        body.pack(fill='both', expand=True, padx=34, pady=(0, 18))
        stages = tk.Frame(body, bg=COLORS['panel'], highlightbackground=COLORS['border'], highlightthickness=1)
        stages.pack(fill='x', pady=(0, 14))
        self.stage_labels = {}
        for i, stage in enumerate(['Léxico', 'Sintáctico', 'Semántico', 'Interpretación']):
            cell = tk.Frame(stages, bg=COLORS['panel'])
            cell.pack(side='left', fill='both', expand=True, padx=12, pady=14)
            tk.Label(cell, text=f'{i+1:02d}', bg=COLORS['panel'], fg=COLORS['primary'], font=('Menlo', 9, 'bold')).pack(anchor='w')
            tk.Label(cell, text=stage, bg=COLORS['panel'], fg=COLORS['text'], font=('SF Pro Display', 13, 'bold')).pack(anchor='w', pady=(4, 2))
            lbl = tk.Label(cell, text='Pendiente', bg=COLORS['panel'], fg=COLORS['muted'], font=('SF Pro Display', 9))
            lbl.pack(anchor='w')
            self.stage_labels[stage] = lbl

        self.trace_box = tk.Text(body, bg=COLORS['panel'], fg=COLORS['text'], relief='flat', wrap='word', font=('Menlo', 9), padx=18, pady=18)
        self.trace_box.pack(fill='both', expand=True)
        self.trace_box.configure(state='disabled')
        return frame

    def _build_docs(self):
        frame = tk.Frame(self.content, bg=COLORS['bg'])
        self._base_header_in(frame, 'Documentación', 'Resumen técnico del lenguaje específico de dominio')
        body = tk.Frame(frame, bg=COLORS['panel'], highlightbackground=COLORS['border'], highlightthickness=1)
        body.pack(fill='both', expand=True, padx=34, pady=(0, 18))
        text = tk.Text(body, bg=COLORS['panel'], fg=COLORS['text'], relief='flat', wrap='word', font=('SF Pro Text', 11), padx=28, pady=24)
        text.pack(fill='both', expand=True)
        docs = '''HEALTHSCRIPT · DOCUMENTACIÓN TÉCNICA

Propósito
HealthScript es un lenguaje especializado para definir y ejecutar reglas de monitoreo preventivo en salud pública. El usuario autorizado puede capturar datos y convertirlos a instrucciones del lenguaje.

Flujo de operación
1. Registro de paciente → captura local de indicadores.
2. Generador → construye código HealthScript.
3. Lexer → convierte el código en tokens.
4. Parser → comprueba la gramática y construye el AST.
5. Semántica → valida variables y tipos.
6. Intérprete → ejecuta asignaciones y condiciones.
7. Motor de reglas → produce alertas y recomendaciones.

Ejemplo
    PACIENTE "P001"
    GLUCOSA = 195
    SI GLUCOSA > 180 ENTONCES
        ALERTA "Nivel de glucosa elevado"
    FIN

Variables del dominio
GLUCOSA, GLUCOSA_AYUNO, PRESION_SISTOLICA, PRESION_DIASTOLICA,
PESO, ALTURA, IMC, CALORIAS, AGUA, PROTEINA y ACTIVIDAD_FISICA.

Importante
Este prototipo trabaja localmente en la computadora y no usa una base de datos externa. Los datos introducidos por formulario solo permanecen en la sesión actual; sin embargo esta versión añade almacenamiento local del historial para consultas futuras.
'''
        text.insert('1.0', docs)
        text.configure(state='disabled')
        return frame

    # ------------------------------------------------------------------
    # Patients section (historial persistente)
    # ------------------------------------------------------------------
    def _build_patients_section(self):
        frame = tk.Frame(self.content, bg=COLORS['bg'])
        self.patients_frame = frame

        header = self._base_header_in(frame, 'Pacientes', 'Historial persistente de pacientes y su severidad')
        controls = tk.Frame(header, bg=COLORS['bg'])
        controls.pack(side='right', anchor='n')

        ttk.Label(controls, text='Severidad:', background=COLORS['bg']).pack(side='left', padx=(0, 6))
        combobox = ttk.Combobox(controls, textvariable=self.patient_filter, values=['TODOS', 'MEDIO', 'MODERADO', 'GRAVE'], state='readonly', width=12)
        combobox.pack(side='left')
        ttk.Button(controls, text='Refrescar', style='Secondary.TButton', command=self._refresh_patient_history).pack(side='left', padx=(8, 0))

        body = tk.Frame(frame, bg=COLORS['bg'])
        body.pack(fill='both', expand=True, padx=34, pady=(0, 16))

        left = tk.Frame(body, bg=COLORS['panel'], highlightbackground=COLORS['border'], highlightthickness=1)
        left.pack(side='left', fill='both', expand=True, padx=(0, 10))

        self.patient_tree = ttk.Treeview(left, columns=('timestamp', 'patient_id', 'severity', 'alerts', 'recommendations'), show='headings', height=16)
        self.patient_tree.heading('timestamp', text='Fecha')
        self.patient_tree.heading('patient_id', text='Paciente')
        self.patient_tree.heading('severity', text='Severidad')
        self.patient_tree.heading('alerts', text='Alertas')
        self.patient_tree.heading('recommendations', text='Recomendaciones')
        self.patient_tree.column('timestamp', width=170, anchor='w')
        self.patient_tree.column('patient_id', width=120, anchor='center')
        self.patient_tree.column('severity', width=100, anchor='center')
        self.patient_tree.column('alerts', width=240, anchor='w')
        self.patient_tree.column('recommendations', width=260, anchor='w')
        self.patient_tree.pack(fill='both', expand=True, padx=10, pady=10)
        self.patient_tree.bind('<<TreeviewSelect>>', self._show_selected_patient_detail)

        right = tk.Frame(body, bg=COLORS['panel'], highlightbackground=COLORS['border'], highlightthickness=1, width=420)
        right.pack(side='left', fill='both')
        right.pack_propagate(False)
        tk.Label(right, text='DETALLE DEL PACIENTE', bg=COLORS['panel'], fg=COLORS['text'], font=('SF Pro Display', 13, 'bold')).pack(anchor='w', padx=16, pady=(15, 10))
        self.patient_detail = tk.Text(right, bg=COLORS['panel'], fg=COLORS['text'], relief='flat', wrap='word', font=('Menlo', 9), padx=16, pady=12)
        self.patient_detail.pack(fill='both', expand=True)
        self.patient_detail.configure(state='disabled')

        self._refresh_patient_history()
        return frame

    def _refresh_patient_history(self):
        rows = list_patients()
        filter_value = self.patient_filter.get()
        if filter_value != 'TODOS':
            rows = [r for r in rows if (r.get('severity') or '').upper() == filter_value]

        for item in self.patient_tree.get_children():
            self.patient_tree.delete(item)

        for row in sorted(rows, key=lambda r: r.get('timestamp', ''), reverse=True):
            self.patient_tree.insert('', 'end', values=(
                row.get('timestamp', ''),
                row.get('patient_id', 'SIN_ID'),
                row.get('severity', 'MEDIO'),
                '; '.join(row.get('alerts', []))[:180],
                '; '.join(row.get('recommendations', []))[:180],
            ))

        self.patient_detail.configure(state='normal')
        self.patient_detail.delete('1.0', 'end')
        self.patient_detail.insert('1.0', 'Selecciona un paciente del historial para ver detalles.')
        self.patient_detail.configure(state='disabled')

    def _show_selected_patient_detail(self, event=None):
        selected = self.patient_tree.selection()
        if not selected:
            return

        item = selected[0]
        values = self.patient_tree.item(item, 'values')
        timestamp, patient_id, severity, alerts_text, recommendations_text = values

        patients = list_patients()
        match = None
        for rec in patients:
            if rec.get('patient_id') == patient_id and rec.get('timestamp') == timestamp:
                match = rec
                break

        if not match:
            return

        detail = []
        detail.append(f'Paciente: {match.get("patient_id")}\n')
        detail.append(f'Fecha: {match.get("timestamp")}\n')
        detail.append(f'Severidad: {match.get("severity")}\n\n')
        detail.append('Valores:\n')
        for key, value in match.get('values', {}).items():
            detail.append(f'  - {key}: {value}\n')
        detail.append('\nAlertas:\n')
        if match.get('alerts'):
            for a in match.get('alerts'):
                detail.append(f'  - {a}\n')
        else:
            detail.append('  - Ninguna\n')
        detail.append('\nRecomendaciones:\n')
        if match.get('recommendations'):
            for r in match.get('recommendations'):
                detail.append(f'  - {r}\n')
        else:
            detail.append('  - Ninguna\n')
        detail.append('\nReglas disparadas:\n')
        if match.get('triggered_rules'):
            for rr in match.get('triggered_rules'):
                detail.append(f'  - {rr}\n')
        else:
            detail.append('  - Ninguna\n')

        self.patient_detail.configure(state='normal')
        self.patient_detail.delete('1.0', 'end')
        self.patient_detail.insert('1.0', ''.join(detail))
        self.patient_detail.configure(state='disabled')

    # ------------------------------------------------------------------
    # Navigation / pipeline execution
    # ------------------------------------------------------------------
    def _set_section(self, name):
        mapping = {
            'Dashboard': self.dashboard_frame,
            'Registro de paciente': self.patient_frame,
            'Editor HealthScript': self.editor_frame,
            'Análisis': self.analysis_frame,
            'Documentación': self.docs_frame,
            'Pacientes': self.patients_frame,
        }
        for frame in mapping.values():
            if frame:
                frame.pack_forget()
        frame = mapping.get(name, self.dashboard_frame)
        if frame:
            frame.pack(fill='both', expand=True, before=self.status_label)
        for label, widgets in self.nav_buttons.items():
            active = label == name
            bg = '#1B2A42' if active else COLORS['sidebar']
            fg = 'white' if active else '#AEB8C8'
            widgets[0].configure(bg=bg)
            widgets[1].configure(bg=bg, fg=COLORS['primary'] if active else COLORS['sidebar_muted'])
            widgets[2].configure(bg=bg, fg=fg)
        self.pipeline_var.set(f'Sección activa · {name}')

    def _load_sample(self):
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', SAMPLE)
        self._update_line_numbers()
        self._write_text(self.generated_preview, SAMPLE)
        self.pipeline_var.set('Ejemplo HealthScript cargado')

        # Sincroniza una copia del ejemplo con el formulario.
        example = {
            'patient_id': 'P001', 'GLUCOSA': '195', 'PRESION_SISTOLICA': '145',
            'PRESION_DIASTOLICA': '90', 'IMC': '31.2', 'ACTIVIDAD_FISICA': '30',
            'AGUA': '1800', 'PROTEINA': '85'
        }
        for key, value in example.items():
            if key in self.patient_vars:
                self.patient_vars[key].set(value)

    def clear_editor(self):
        self.editor.delete('1.0', 'end')
        self._update_line_numbers()
        self._write_text(self.generated_preview, 'Sin código generado.')
        self.pipeline_var.set('Editor limpio')

    def _sync_scroll(self, event=None):
        self.line_numbers.yview_moveto(self.editor.yview()[0])

    def _update_line_numbers(self):
        count = int(self.editor.index('end-1c').split('.')[0])
        nums = '\n'.join(str(i) for i in range(1, count + 1))
        self.line_numbers.configure(state='normal')
        self.line_numbers.delete('1.0', 'end')
        self.line_numbers.insert('1.0', nums)
        self.line_numbers.configure(state='disabled')
        self.line_numbers.yview_moveto(self.editor.yview()[0])

    def validate_source(self):
        result = run_pipeline(self.editor.get('1.0', 'end-1c'), execute_program=False)
        self._show_result(result)
        self._set_section('Análisis')
        if result.success:
            self.pipeline_var.set('✓ Validación completada · lexer + parser + semántica')
        else:
            self.pipeline_var.set('✕ Validación detenida por un error')

    def execute_source(self, return_to_dashboard=True):
        result = run_pipeline(self.editor.get('1.0', 'end-1c'), execute_program=True)
        self._show_result(result)
        self.current_result = result
        self._update_dashboard(result)
        self._set_section('Dashboard' if return_to_dashboard else 'Editor HealthScript')
        self.pipeline_var.set('✓ Ejecución completada' if result.success else '✕ Ejecución detenida por un error')

    def _show_result(self, result: PipelineResult):
        stages = ['Léxico', 'Sintáctico', 'Semántico', 'Interpretación']
        if not hasattr(self, 'stage_labels'):
            return
        for stage in stages:
            text = result.stage_messages.get(stage, 'Pendiente')
            color = COLORS['success'] if text.startswith('Completado') else COLORS['danger'] if text == 'Error' else COLORS['warning'] if 'Lista' in text else COLORS['muted']
            self.stage_labels[stage].configure(text=text, fg=color)

        self._write_text(self.out_text, '\n'.join(result.diagnostics) if result.diagnostics else '✓ Sin errores. El programa es válido.')
        if result.execution:
            parts = []
            parts.append(f'Paciente: {result.execution.patient_id or "—"}')
            parts.append(f'Reglas activadas: {len(result.execution.triggered_rules)}')
            parts.append('')
            for rule in result.execution.triggered_rules:
                parts.append('✓ ' + rule)
            if result.execution.alerts:
                parts.append('\nALERTAS')
                parts.extend('⚠ ' + item for item in result.execution.alerts)
            if result.execution.recommendations:
                parts.append('\nRECOMENDACIONES')
                parts.extend('→ ' + item for item in result.execution.recommendations)
            self._write_text(self.out_text, '\n'.join(parts) if not result.diagnostics else '\n'.join(result.diagnostics + [''] + parts))
            self._write_text(self.trace_box, '\n'.join(result.execution.trace))
        else:
            self._write_text(self.trace_box, 'Sin ejecución. La interpretación se detuvo antes de esta etapa.')

        token_lines = [t.display() for t in result.tokens if t.type != 'NEWLINE']
        self._write_text(self.tokens_text, '\n'.join(token_lines) or 'No se generaron tokens.')
        self._write_text(self.ast_text, result.ast_text or 'El árbol AST no está disponible porque el parser no se completó.')

    def _write_text(self, widget, content):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', content)
        widget.configure(state='disabled')

    # ------------------------------------------------------------------
    # Dashboard rendering
    # ------------------------------------------------------------------
    def _update_dashboard(self, result: PipelineResult):
        if not result.execution:
            self.card_status.value_label.configure(text='ERROR')
            self._clear_tree()
            self._write_text(self.result_box, '\n'.join(result.diagnostics) or 'El análisis no produjo una ejecución.')
            return

        ex = result.execution
        self.card_patient.value_label.configure(text=ex.patient_id or '—')
        self.card_alerts.value_label.configure(text=str(len(ex.alerts)))
        self.card_rules.value_label.configure(text=str(len(ex.triggered_rules)))
        self.card_status.value_label.configure(text='OK' if result.success else 'ERROR')

        self._clear_tree()
        display = [
            ('GLUCOSA', 'mg/dL'), ('GLUCOSA_AYUNO', 'mg/dL'), ('PRESION_SISTOLICA', 'mmHg'),
            ('PRESION_DIASTOLICA', 'mmHg'), ('IMC', ''), ('ACTIVIDAD_FISICA', 'min'),
            ('AGUA', 'mL'), ('PROTEINA', 'g'), ('CALORIAS', 'kcal'), ('PESO', 'kg'), ('ALTURA', 'm')
        ]
        thresholds = {
            'GLUCOSA': (180, 'Elevada'),
            'GLUCOSA_AYUNO': (126, 'Elevada'),
            'PRESION_SISTOLICA': (140, 'Elevada'),
            'IMC': (30, 'Elevado'),
        }
        for name, unit in display:
            if name not in ex.values:
                continue
            value = ex.values[name]
            status = 'Registrado'
            tag = 'neutral'
            if name in thresholds:
                limit, label = thresholds[name]
                try:
                    numeric = float(value)
                except Exception:
                    numeric = None
                if numeric is not None and numeric >= limit:
                    status = label
                    tag = 'high'
                else:
                    status = 'Dentro del umbral de la demo'
                    tag = 'normal'
            self.dashboard_tree.insert('', 'end', values=(name, f'{value} {unit}'.strip(), status), tags=(tag,))

        lines = []
        if ex.alerts:
            lines.append('ALERTAS DETECTADAS')
            lines.extend('⚠  ' + x for x in ex.alerts)
        else:
            lines.append('✓ No se activaron alertas.')
        if ex.recommendations:
            lines.append('\nRECOMENDACIONES')
            lines.extend('→  ' + x for x in ex.recommendations)
        lines.append('\nREGLAS ACTIVADAS')
        if ex.triggered_rules:
            lines.extend('✓  ' + x for x in ex.triggered_rules)
        else:
            lines.append('— Ninguna')
        lines.append('\nOrigen: formulario local → HealthScript → motor de reglas')
        self._write_text(self.result_box, '\n'.join(lines))

    def _clear_tree(self):
        for item in self.dashboard_tree.get_children():
            self.dashboard_tree.delete(item)


def launch():
    app = HealthScriptApp()
    app.mainloop()
