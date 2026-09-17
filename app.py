"""Windows desktop interface for the local Paytrack load validator."""
from __future__ import annotations
import argparse
import json
import os
import sys
import re
import unicodedata
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from engine import Project, KINDS, LABELS, SHEETS, COMPANY_COL, text, email_valid


def resource_dir():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).parent))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        try:
            self.iconbitmap(default=str(resource_dir() / 'assets' / 'paytrack.ico'))
        except Exception:
            pass
        self.title('Validador de Cargas | Paytrack')
        self.geometry('1260x820')
        self.minsize(1000, 650)
        self.configure(bg='#F3F5F8')
        self.project = None
        self.analysis = None
        self.source = tk.StringVar()
        self.templates = tk.StringVar(value=str(resource_dir() / 'templates'))
        self.template_display = tk.StringVar(value='4 modelos padrão incluídos no aplicativo')
        self.status = tk.StringVar(value='Selecione a planilha preenchida pelo cliente para começar.')
        self.summary = tk.StringVar(value='Nenhuma planilha carregada')
        self.filter = tk.StringVar(value='Todas')
        self.issue_severity = tk.StringVar(value='Todas')
        self.kind = tk.StringVar(value=LABELS['USERS'])
        self.search = tk.StringVar()
        self.issue_items = {}
        self.email_items = {}
        self.data_items = {}
        self.last_export = None
        self._style()
        self._layout()
        self.protocol('WM_DELETE_WINDOW', self.close_app)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10))
        style.configure('TFrame', background='#F3F5F8')
        style.configure('TLabel', background='#F3F5F8', foreground='#1D2939')
        style.configure('Title.TLabel', font=('Segoe UI', 21, 'bold'))
        style.configure('Sub.TLabel', foreground='#526079')
        style.configure('TButton', padding=(12, 8))
        style.configure('Primary.TButton', background='#245EAB', foreground='white')
        style.map('Primary.TButton', background=[('active', '#194B91')])
        style.configure('Treeview', rowheight=29, background='white', fieldbackground='white', font=('Segoe UI', 10))
        style.configure('Treeview.Heading', background='#E5EBF3', font=('Segoe UI', 10, 'bold'), padding=7)
        style.configure('TNotebook.Tab', padding=(15, 9))

    def _layout(self):
        outer = ttk.Frame(self, padding=24)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='Validador de cargas', style='Title.TLabel').pack(anchor='w')
        ttk.Label(outer, text='Prepare as cargas, revise as decisões e exporte no padrão do sistema.', style='Sub.TLabel').pack(anchor='w', pady=(3, 17))
        files = ttk.Frame(outer)
        files.pack(fill='x')
        files.columnconfigure(1, weight=1)
        ttk.Label(files, text='Planilha do cliente').grid(row=0, column=0, sticky='w', padx=(0, 14))
        ttk.Entry(files, textvariable=self.source).grid(row=0, column=1, sticky='ew', padx=5)
        ttk.Button(files, text='Selecionar arquivo', command=self.browse_source).grid(row=0, column=2, padx=5)
        ttk.Label(files, text='Modelos de importação').grid(row=1, column=0, sticky='w')
        ttk.Entry(files, textvariable=self.template_display, state='readonly').grid(row=1, column=1, sticky='ew', padx=5, pady=6)
        ttk.Button(files, text='Selecionar pasta', command=self.browse_templates).grid(row=1, column=2, padx=5)
        toolbar = ttk.Frame(outer)
        toolbar.pack(fill='x', pady=(9, 12))
        self.load_button = ttk.Button(toolbar, text='Analisar planilha', style='Primary.TButton', command=self.load_project)
        self.load_button.pack(side='left')
        ttk.Button(toolbar, text='Abrir revisão', command=self.open_session).pack(side='left', padx=7)
        ttk.Button(toolbar, text='Salvar revisão', command=self.save_session).pack(side='left')
        ttk.Button(toolbar, text='Aplicar recomendações em lote', command=self.review_recommendations).pack(side='left', padx=7)
        ttk.Button(toolbar, text='Exportar cargas', style='Primary.TButton', command=self.export_files).pack(side='right')
        ttk.Label(outer, textvariable=self.summary, font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 10))
        ttk.Label(outer, textvariable=self.status, style='Sub.TLabel', wraplength=1150).pack(side='bottom', anchor='w', pady=(12, 0))
        self.tabs = ttk.Notebook(outer)
        self.tabs.pack(fill='both', expand=True)
        self.overview_tab = ttk.Frame(self.tabs, padding=10)
        self.readiness_tab = ttk.Frame(self.tabs, padding=10)
        self.pending_tab = ttk.Frame(self.tabs, padding=10)
        self.emails_tab = ttk.Frame(self.tabs, padding=10)
        self.data_tab = ttk.Frame(self.tabs, padding=10)
        self.domains_tab = ttk.Frame(self.tabs, padding=10)
        for frame, label in [(self.overview_tab, 'Resumo por aba'), (self.readiness_tab, 'Prontidão por carga'), (self.pending_tab, 'Pendências'), (self.emails_tab, 'Sugestões de e-mail'), (self.data_tab, 'Dados de saída'), (self.domains_tab, 'Domínios das unidades')]:
            self.tabs.add(frame, text=label)
        ttk.Label(self.overview_tab, text='Clique em uma quantidade para abrir os registros correspondentes.', font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 10))
        ttk.Label(self.overview_tab, text='Erros e pendências contam ocorrências, não pessoas. Um registro pode ter mais de uma ocorrência.\nSugestões de e-mail podem corresponder aos mesmos registros com erro; não some as colunas.', wraplength=1050, style='Sub.TLabel').pack(anchor='w', pady=(0, 12))
        self.overview_tree = self.tree(self.overview_tab, [('sheet', 'Aba', 240), ('records', 'Registros', 135), ('errors', 'Erros', 135), ('suggestions', 'Sugestões', 135), ('pending', 'Pendências', 135), ('warnings', 'Avisos', 135)])
        self.overview_tree.bind('<ButtonRelease-1>', self.open_overview_cell)
        ttk.Label(self.readiness_tab, text='A prontidão é calculada para cada carga separadamente. Pendências em Usuários não impedem a revisão de Empresas, Centros de custo ou Tipos de despesa.', wraplength=1050, style='Sub.TLabel').pack(anchor='w', pady=(0, 10))
        ttk.Label(self.readiness_tab, text='Clique em uma carga para abrir as pendências locais.', style='Sub.TLabel').pack(anchor='w', pady=(0, 8))
        self.readiness_tree = self.tree(self.readiness_tab, [('kind', 'Carga', 230), ('status', 'Prontidão', 180), ('records', 'Registros', 110), ('errors', 'Erros', 90), ('pending', 'Pendências', 110), ('warnings', 'Avisos', 90), ('detail', 'Detalhes', 480)])
        self.readiness_tree.bind('<Double-1>', self.open_readiness)
        bar = ttk.Frame(self.pending_tab)
        bar.pack(fill='x', pady=(0, 8))
        ttk.Label(bar, text='Carga:').pack(side='left')
        combo = ttk.Combobox(bar, textvariable=self.filter, values=['Todas'] + list(LABELS.values()), state='readonly', width=24)
        combo.pack(side='left', padx=8)
        combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_issues())
        ttk.Label(bar, text='Situação:').pack(side='left', padx=(10, 0))
        severity = ttk.Combobox(bar, textvariable=self.issue_severity, values=['Todas', 'Erro', 'Pendente', 'Aviso'], state='readonly', width=12)
        severity.pack(side='left', padx=8)
        severity.bind('<<ComboboxSelected>>', lambda e: self.refresh_issues())
        ttk.Button(bar, text='Revisar seleção', command=self.edit_issues).pack(side='right')
        ttk.Label(self.pending_tab, text='Selecione uma ou mais linhas do mesmo campo para decidir em conjunto. Adiar mantém a pendência.', style='Sub.TLabel').pack(anchor='w', pady=(0, 8))
        self.issues_tree = self.tree(self.pending_tab, [('status', 'Situação', 85), ('kind', 'Carga', 150), ('row', 'Linha origem', 115), ('name', 'Registro', 230), ('field', 'Campo', 180), ('reason', 'Motivo', 460)])
        self.issues_tree.bind('<Double-1>', lambda e: self.edit_issues())
        self.issues_tree.bind('<<TreeviewSelect>>', self.show_issue_detail)
        self.detail = tk.Text(self.pending_tab, height=3, wrap='word', font=('Segoe UI', 10), bg='#EAF0F7', relief='flat', padx=10, pady=8)
        self.detail.pack(side='bottom', fill='x', pady=(8, 0), before=self.issues_tree.master)
        self.detail.configure(state='disabled')
        bar = ttk.Frame(self.emails_tab)
        bar.pack(fill='x', pady=(0, 8))
        ttk.Label(self.emails_tab, text='Sugestões só substituem o original após sua confirmação.', style='Sub.TLabel').pack(anchor='w', before=bar, pady=(0, 8))
        ttk.Button(bar, text='Aplicar todas as sugestões', style='Primary.TButton', command=self.review_all_emails).pack(side='left')
        ttk.Button(bar, text='Revisar e-mail selecionado', command=self.review_email).pack(side='right')
        self.emails_tree = self.tree(self.emails_tab, [('row', 'Linha', 60), ('name', 'Nome', 235), ('original', 'E-mail atual', 250), ('proposal', 'Sugestão', 290), ('status', 'Domínio', 160)])
        self.emails_tree.bind('<Double-1>', lambda e: self.review_email())
        bar = ttk.Frame(self.data_tab)
        bar.pack(fill='x', pady=(0, 8))
        combo = ttk.Combobox(bar, textvariable=self.kind, values=list(LABELS.values()), state='readonly', width=24)
        combo.pack(side='left')
        combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_data())
        ttk.Label(bar, text='Buscar:').pack(side='left', padx=(15, 5))
        entry = ttk.Entry(bar, textvariable=self.search, width=28)
        entry.pack(side='left')
        entry.bind('<KeyRelease>', lambda e: self.refresh_data())
        ttk.Button(bar, text='Editar registro', command=self.edit_data).pack(side='right')
        self.data_tree = self.tree(self.data_tab, [('row', 'Linha origem', 90)])
        self.data_tree.bind('<Double-1>', lambda e: self.edit_data())
        ttk.Label(self.domains_tab, text='Confirme o domínio para cada unidade. O contato da empresa fornece apenas uma sugestão.', style='Sub.TLabel').pack(anchor='w', pady=(0, 10))
        ttk.Button(self.domains_tab, text='Confirmar / alterar domínio', command=self.edit_domain).pack(anchor='e', pady=(0, 8))
        self.domains_tree = self.tree(self.domains_tab, [('cnpj', 'CNPJ', 160), ('name', 'Unidade', 380), ('proposal', 'Domínio do contato', 220), ('chosen', 'Domínio confirmado', 220)])
        self.domains_tree.bind('<Double-1>', lambda e: self.edit_domain())
        self.duplicates_tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(self.duplicates_tab, text='Duplicidades')
        ttk.Label(self.duplicates_tab, text='Usuários com CPF repetido. Compare os dados de saída antes de decidir. Nenhuma linha será excluída.', wraplength=1000).pack(anchor='w')
        ttk.Button(self.duplicates_tab, text='Comparar registros', command=self.compare_duplicates).pack(anchor='e', pady=8)
        self.duplicates_tree = self.tree(self.duplicates_tab, [('cpf', 'CPF', 160), ('rows', 'Linhas de origem', 180), ('classification', 'Comparação', 240), ('names', 'Nomes', 480)])
        self.duplicates_tree.bind('<Double-1>', lambda e: self.compare_duplicates())
        self.normalizations_tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(self.normalizations_tab, text='Correções em lote')
        ttk.Label(self.normalizations_tab, text='Revise a origem e a proposta. A conversão prévia de formatos só fica aprovada após sua confirmação.\nSem confirmação, a carga permanece pendente e só pode ser exportada como rascunho.', wraplength=1050).pack(anchor='w')
        bar = ttk.Frame(self.normalizations_tab)
        bar.pack(fill='x', pady=8)
        self.normalization_category = tk.StringVar(value='Espaços')
        categories = ttk.Combobox(bar, textvariable=self.normalization_category, values=['Espaços', 'Documentos', 'Datas', 'Sim/Não', 'Sexo', 'CEP', 'Telefones'], state='readonly')
        categories.pack(side='left')
        categories.bind('<<ComboboxSelected>>', lambda e: self.refresh_normalizations())
        ttk.Button(bar, text='Aplicar categoria exibida', command=lambda: self.apply_normalizations(all_rows=True)).pack(side='right')
        ttk.Button(bar, text='Aplicar selecionadas', command=self.apply_normalizations).pack(side='right', padx=8)
        self.normalizations_tree = self.tree(self.normalizations_tab, [('kind', 'Carga', 150), ('row', 'Linha origem', 90), ('field', 'Campo', 210), ('before', 'Origem', 290), ('after', 'Proposta', 290)])
        self.catalog_tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(self.catalog_tab, text='Sugestões de preenchimento')
        ttk.Label(self.catalog_tab, text='Correspondências dos cadastros desta planilha. Alternativas podem aparecer para o mesmo registro.\nCentros de custo só são sugeridos quando a unidade está identificada por CNPJ ou código exato. Nada é aplicado automaticamente.', wraplength=1050).pack(anchor='w')
        ttk.Button(self.catalog_tab, text='Revisar sugestão selecionada', command=self.review_catalog).pack(anchor='e', pady=8)
        self.catalog_tree = self.tree(self.catalog_tab, [('kind', 'Carga', 145), ('row', 'Linha', 65), ('before', 'Atual', 280), ('after', 'Proposta', 280), ('reference', 'Cadastro de referência', 220), ('reason', 'Motivo', 390)])
        self.catalog_tree.configure(selectmode='browse')
        self.catalog_tree.bind('<Double-1>', lambda e: self.review_catalog())
        self.decisions_tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(self.decisions_tab, text='Antes e depois')
        ttk.Label(self.decisions_tab, text='Alterações confirmadas nesta revisão. Selecione uma ou mais para restaurar os valores anteriores. O arquivo de origem não é alterado.', wraplength=1050).pack(anchor='w')
        bar = ttk.Frame(self.decisions_tab)
        bar.pack(fill='x', pady=8)
        ttk.Button(bar, text='Desfazer todas as alterações', command=lambda: self.undo_history(all_rows=True)).pack(side='right')
        ttk.Button(bar, text='Desfazer selecionadas', style='Primary.TButton', command=self.undo_history).pack(side='right', padx=8)
        self.decisions_tree = self.tree(self.decisions_tab, [('when', 'Quando', 165), ('kind', 'Carga', 145), ('row', 'Linha', 75), ('field', 'Campo', 210), ('before', 'Antes', 300), ('after', 'Depois', 300)])

    def refresh_catalog(self):
        self.catalog_tree.delete(*self.catalog_tree.get_children())
        self.catalog_items = {}
        for index, proposal in enumerate(self.project.catalog_suggestions()):
            key = str(index)
            self.catalog_items[key] = proposal
            def describe(values):
                return ' | '.join(f'{self.project.headers[proposal["kind"]][col]}: {text(value) or "(vazio)"}' for col, value in values.items())
            self.catalog_tree.insert('', 'end', iid=key, values=[LABELS[proposal['kind']], proposal['row'], describe(proposal['before']), describe(proposal['changes']), proposal['reference'], proposal['reason']])

    def refresh_decisions(self):
        self.decisions_tree.delete(*self.decisions_tree.get_children())
        self.decision_items = {}
        if not self.project:
            return
        for entry in reversed(self.project.reversible_history()):
            if not entry['reversible']:
                continue
            key = str(entry['index'])
            self.decision_items[key] = entry
            kind = 'Domínios das unidades' if entry['kind'] == 'DOMINIO' else LABELS[entry['kind']]
            self.decisions_tree.insert('', 'end', iid=key, values=[entry['when'], kind, entry['row'], entry['field'], text(entry['before']) or '(origem)', text(entry['after'])])

    def undo_history(self, all_rows=False):
        keys = self.decisions_tree.get_children() if all_rows else self.decisions_tree.selection()
        if not keys:
            return
        entries = [self.decision_items[key] for key in keys]
        message = f'Desfazer {len(entries)} alteração(ões) e restaurar os valores anteriores?\n\nO arquivo original continuará preservado.'
        if not messagebox.askyesno('Desfazer alterações', message):
            return
        try:
            self.project.undo_history([entry['index'] for entry in entries])
            self.refresh()
        except ValueError as exc:
            messagebox.showerror('Não foi possível desfazer', str(exc))
            self.refresh()

    def review_catalog(self):
        selection = self.catalog_tree.selection()
        if not selection:
            return
        proposal = self.catalog_items[selection[0]]
        details = '\n'.join(f'{self.project.headers[proposal["kind"]][col]}: {text(proposal["before"][col]) or "(vazio)"} → {value}' for col, value in proposal['changes'].items())
        if not messagebox.askyesno('Confirmar preenchimento', f"{LABELS[proposal['kind']]} — linha {proposal['row']}\n{proposal['reference']}\n{proposal['reason']}\n\n{details}\n\nDeseja aplicar esta sugestão?"):
            return
        try:
            self.project.accept_catalog_suggestion(proposal)
            self.refresh()
        except ValueError as exc:
            messagebox.showerror('Revisão alterada', str(exc))
            self.refresh()

    def refresh_normalizations(self):
        self.normalizations_tree.delete(*self.normalizations_tree.get_children())
        self.normalization_items = {}
        if not self.project:
            return
        for p in self.project.normalizations():
            if p['category'] != self.normalization_category.get():
                continue
            key = f"{p['kind']}:{p['row']}:{p['col']}"
            self.normalization_items[key] = p
            after = p['after'].strftime('%d/%m/%Y') if isinstance(p['after'], datetime) else p['after']
            self.normalizations_tree.insert('', 'end', iid=key, values=[LABELS[p['kind']], p['row'], self.project.headers[p['kind']][p['col']], repr(p['before']), after])

    def apply_normalizations(self, all_rows=False):
        keys = self.normalizations_tree.get_children() if all_rows else self.normalizations_tree.selection()
        preview = [self.normalization_items[k] for k in keys]
        if not preview:
            return
        if not messagebox.askyesno('Confirmar correções em lote', f"Aplicar as {len(preview)} alterações de {self.normalization_category.get()} exibidas na revisão?\nO arquivo original será preservado."):
            return
        try:
            self.project.accept_normalizations(preview)
            self.refresh()
        except ValueError as exc:
            messagebox.showerror('Revisão alterada', str(exc))
            self.refresh()

    def refresh_duplicates(self):
        self.duplicates_tree.delete(*self.duplicates_tree.get_children())
        self.duplicate_items = {}
        for group in self.project.duplicate_users(self.analysis.records):
            self.duplicate_items[group['cpf']] = group
            self.duplicates_tree.insert('', 'end', iid=group['cpf'], values=[group['cpf'],
                ', '.join(str(r.row) for r in group['records']), group['classification'],
                ' / '.join(text(r.values[0]) for r in group['records'])])

    def compare_duplicates(self):
        selected = self.duplicates_tree.selection()
        if not selected:
            return
        group = self.duplicate_items[selected[0]]
        dialog = tk.Toplevel(self)
        dialog.title('Comparar usuários com CPF repetido')
        dialog.geometry('1100x650')
        dialog.transient(self)
        ttk.Label(dialog, text=group['classification'] + '\nCampos divergentes destacados. Comparação dos dados de saída; campos exclusivos da origem não são comparados.\nSenhas permanecem ocultas, mesmo quando diferentes.', wraplength=1050, padding=10).pack(anchor='w')
        bar = ttk.Frame(dialog, padding=10)
        bar.pack(fill='x')
        rows = [str(r.row) for r in group['records']]
        row = tk.StringVar(value=rows[0])
        ttk.Label(bar, text='Linha de origem para editar:').pack(side='left')
        ttk.Combobox(bar, textvariable=row, values=rows, state='readonly', width=10).pack(side='left', padx=8)
        def edit():
            chosen = int(row.get())
            if messagebox.askyesno('Decidir agora?', f'Deseja editar o registro da linha {chosen}?', parent=dialog):
                dialog.destroy()
                self.edit_dialog('USERS', [chosen], 2)
        ttk.Button(bar, text='Editar registro', command=edit).pack(side='left')
        ttk.Button(bar, text='Decidir depois', command=dialog.destroy).pack(side='right')
        comparison = self.tree(dialog, [('field', 'Campo', 240)] + [(str(r.row), f'Linha {r.row}', 280) for r in group['records']])
        for col, heading in enumerate(self.project.headers['USERS']):
            different = col in group['differences']
            values = [('≠ ' if different else '') + heading] + [('••••••' if text(r.values[col]) else '') if col == 8 else text(r.values[col]) for r in group['records']]
            comparison.insert('', 'end', values=values, tags=('Erro',) if different else ())
        dialog.grab_set()

    def tree(self, parent, columns):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        tree = ttk.Treeview(frame, show='headings', selectmode='extended')
        self.configure_columns(tree, columns)
        y = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        x = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        tree.grid(row=0, column=0, sticky='nsew')
        y.grid(row=0, column=1, sticky='ns')
        x.grid(row=1, column=0, sticky='ew')
        tree.tag_configure('Erro', foreground='#A12631')
        tree.tag_configure('Pendente', foreground='#815419')
        return tree

    @staticmethod
    def configure_columns(tree, columns):
        tree._sort_column = None
        tree._sort_descending = False
        tree._column_labels = {key: label for key, label, _ in columns}
        tree.configure(columns=[c[0] for c in columns])
        for key, label, width in columns:
            tree.heading(key, text=label, command=lambda col=key: App.sort_column(tree, col))
            tree.column(key, width=width, minwidth=60, stretch=False)

    @staticmethod
    def sort_column(tree, column):
        descending = not tree._sort_descending if tree._sort_column == column else False
        def sort_key(item):
            value = text(tree.set(item, column))
            folded = unicodedata.normalize('NFKD', value.casefold())
            folded = ''.join(c for c in folded if not unicodedata.combining(c))
            # Natural ordering keeps source lines 2, 10, 100 in numeric order.
            return tuple((1, int(part)) if part.isdigit() else (0, part)
                         for part in re.split(r'([0-9]+)', folded))
        for index, item in enumerate(sorted(tree.get_children(''), key=sort_key, reverse=descending)):
            tree.move(item, '', index)
        tree._sort_column, tree._sort_descending = column, descending
        for key, label in tree._column_labels.items():
            tree.heading(key, text=label + ((' ▼' if descending else ' ▲') if key == column else ''))

    def browse_source(self):
        path = filedialog.askopenfilename(title='Planilha preenchida pelo cliente', filetypes=[('Planilha Excel', '*.xlsx')])
        if path:
            self.source.set(path)

    def browse_templates(self):
        path = filedialog.askdirectory(title='Pasta com os quatro modelos DEFAULT')
        if path:
            self.templates.set(path)
            self.template_display.set(path)

    def load_project(self, *, ask=True):
        if not self.source.get():
            messagebox.showinfo('Selecione um arquivo', 'Selecione a planilha preenchida pelo cliente.')
            return
        if self.project and self.project.history and ask:
            if not messagebox.askyesno('Nova análise', 'Carregar novamente descarta as decisões não salvas desta sessão. Deseja continuar?'):
                return
        self.status.set('Lendo a planilha e conferindo os modelos...')
        self.update_idletasks()
        try:
            project = Project(self.source.get(), self.templates.get())
            self.project = project
            self.refresh()
            if ask and self.analysis.blocking:
                decide = messagebox.askyesno('Decisões pendentes', f'Foram encontradas {len(self.analysis.blocking)} pendências.\n\nDeseja revisar essas decisões agora?\n\nSe escolher Não, elas continuarão pendentes e a exportação será um rascunho.')
                if decide:
                    self.tabs.select(self.pending_tab)
        except Exception as exc:
            self.status.set('Não foi possível carregar a planilha.')
            messagebox.showerror('Falha na análise', str(exc))

    def refresh(self):
        if not self.project:
            return
        self.analysis = self.project.analyze()
        self.refresh_overview()
        self.refresh_readiness()
        data = self.analysis.records
        self.summary.set(f'{len(data["EMPLOYER"])} unidades   ·   {len(data["USERS"])} usuários   ·   {len(data["CUST"])} centros de custo   ·   {len(data["EXPENSES"])} despesas   |   {len(self.analysis.blocking)} pendências')
        self.refresh_issues()
        self.refresh_emails()
        self.refresh_data()
        self.refresh_domains()
        self.refresh_duplicates()
        self.refresh_normalizations()
        self.refresh_catalog()
        self.refresh_decisions()
        self.status.set('Decisões aplicadas somente nesta revisão. Arquivos originais preservados. Exportação pendente.' if self.project.history else 'Análise concluída. Revise as pendências ou exporte um rascunho para conferência.')

    def refresh_overview(self):
        self.overview_tree.delete(*self.overview_tree.get_children())
        for kind in KINDS:
            issues = [i for i in self.analysis.issues if i.kind == kind]
            self.overview_tree.insert('', 'end', iid=kind, values=[SHEETS[kind], len(self.analysis.records[kind]),
                sum(i.severity == 'Erro' for i in issues), len(self.analysis.suggestions) if kind == 'USERS' else 0,
                sum(i.severity == 'Pendente' for i in issues), sum(i.severity == 'Aviso' for i in issues)])

    def refresh_readiness(self):
        self.readiness_tree.delete(*self.readiness_tree.get_children())
        for kind, item in self.analysis.readiness_by_kind().items():
            self.readiness_tree.insert('', 'end', iid=kind, values=[LABELS[kind], item['status'], item['records'], item['errors'], item['pending'], item['warnings'], item['detail']])

    def open_readiness(self, _event=None):
        selected = self.readiness_tree.selection()
        if not selected:
            return
        kind = selected[0]
        self.filter.set(LABELS[kind])
        self.issue_severity.set('Todas')
        self.refresh_issues()
        self.tabs.select(self.pending_tab)

    def open_overview_cell(self, event):
        kind = self.overview_tree.identify_row(event.y)
        column = self.overview_tree.identify_column(event.x)
        if kind and column in ('#2', '#3', '#4', '#5', '#6'):
            self.open_overview(kind, column)

    def open_overview(self, kind, column):
        if column == '#2':
            self.kind.set(LABELS[kind])
            self.search.set('')
            self.refresh_data()
            self.tabs.select(self.data_tab)
        elif column == '#4':
            if kind == 'USERS':
                self.tabs.select(self.emails_tab)
            else:
                self.status.set(f'{SHEETS[kind]}: nenhuma sugestão disponível nesta análise.')
        else:
            self.filter.set(LABELS[kind])
            self.issue_severity.set({'#3': 'Erro', '#5': 'Pendente', '#6': 'Aviso'}[column])
            self.refresh_issues()
            self.tabs.select(self.pending_tab)

    def refresh_issues(self):
        self.issues_tree.delete(*self.issues_tree.get_children())
        self.issue_items.clear()
        if not self.analysis:
            return
        names = {(k, r.row): (r.values[1] if k == 'EXPENSES' else r.values[2] if k == 'CUST' else r.values[0]) for k, records in self.analysis.records.items() for r in records}
        for i, issue in enumerate(self.analysis.issues):
            if self.filter.get() != 'Todas' and LABELS[issue.kind] != self.filter.get():
                continue
            if self.issue_severity.get() != 'Todas' and issue.severity != self.issue_severity.get():
                continue
            key = str(i)
            self.issue_items[key] = issue
            heading = self.project.headers[issue.kind][issue.col] if issue.col is not None else ''
            self.issues_tree.insert('', 'end', iid=key, values=[issue.severity, LABELS[issue.kind], issue.row or '', names.get((issue.kind, issue.row), ''), heading, issue.message], tags=(issue.severity,))

    def refresh_emails(self):
        self.emails_tree.delete(*self.emails_tree.get_children())
        self.email_items.clear()
        for s in self.analysis.suggestions:
            key = str(s.row)
            self.email_items[key] = s
            self.emails_tree.insert('', 'end', iid=key, values=[s.row, s.name, s.original, s.proposed, 'Confirmado' if s.confirmed_domain else 'Confirmar unidade/domínio'])

    def refresh_data(self):
        self.data_tree.delete(*self.data_tree.get_children())
        self.data_items.clear()
        if not self.analysis:
            return
        kind = next(k for k in KINDS if LABELS[k] == self.kind.get())
        columns = [('row', 'Linha origem', 90)] + [(str(i), h.replace('\n', ' '), 220 if i in (0, 3) else 165) for i, h in enumerate(self.project.headers[kind])]
        self.configure_columns(self.data_tree, columns)
        for r in self.analysis.records[kind]:
            values = [v.strftime('%d/%m/%Y') if isinstance(v, datetime) else text(v) for v in r.values]
            if kind == 'USERS':
                values[8] = '••••••' if values[8] else ''
            if self.search.get().casefold() not in ' '.join(values).casefold():
                continue
            self.data_items[r.key] = r
            self.data_tree.insert('', 'end', iid=r.key, values=[r.row] + values)

    def refresh_domains(self):
        self.domains_tree.delete(*self.domains_tree.get_children())
        for i, r in enumerate(self.analysis.records['EMPLOYER']):
            cnpj, email = text(r.values[1]), text(r.values[4])
            domain = email.rsplit('@', 1)[-1].lower() if '@' in email else ''
            self.domains_tree.insert('', 'end', iid=str(i), values=[cnpj, r.values[0], domain, self.project.domains.get(cnpj, '')])

    def show_issue_detail(self, _event=None):
        selected = self.issues_tree.selection()
        self.detail.configure(state='normal')
        self.detail.delete('1.0', 'end')
        if selected:
            issue = self.issue_items.get(selected[0])
            if issue:
                self.detail.insert('1.0', f'{SHEETS[issue.kind]} · linha {issue.row or "—"}\n{issue.message}')
        self.detail.configure(state='disabled')

    def edit_issues(self):
        selected = [self.issue_items[i] for i in self.issues_tree.selection()]
        if not selected:
            messagebox.showinfo('Revisar', 'Selecione uma ou mais pendências.')
            return
        first = selected[0]
        normalizations = [i for i in selected if i.message.startswith('Normalização de ')]
        if normalizations:
            keys = {(i.kind, i.row, i.col) for i in normalizations}
            proposals = [p for p in self.project.normalizations() if (p['kind'], p['row'], p['col']) in keys]
            if proposals:
                self.normalization_category.set(proposals[0]['category'])
                self.refresh_normalizations()
                visible = [key for key, p in self.normalization_items.items() if (p['kind'], p['row'], p['col']) in keys]
                self.normalizations_tree.selection_set(visible)
                self.tabs.select(self.normalizations_tab)
                self.status.set('Confira a proposta individual de cada célula e clique em Aplicar selecionadas. Outras categorias devem ser revisadas separadamente.')
            return
        if first.col is None or not first.row:
            messagebox.showinfo('Revisar na origem', first.message + '\n\nRevise a planilha de origem e carregue novamente, se necessário.')
            return
        if any((i.kind, i.col) != (first.kind, first.col) for i in selected):
            messagebox.showinfo('Seleção', 'Para uma decisão em conjunto, selecione o mesmo campo da mesma carga.')
            return
        if messagebox.askyesno('Decidir agora?', f'Deseja definir {self.project.headers[first.kind][first.col]} para {len(selected)} registro(s) selecionado(s) agora?'):
            self.edit_dialog(first.kind, sorted({i.row for i in selected}), first.col)

    def edit_data(self):
        selected = [self.data_items[i] for i in self.data_tree.selection()]
        if not selected:
            messagebox.showinfo('Editar', 'Selecione um ou mais registros.')
            return
        self.edit_dialog(selected[0].kind, [r.row for r in selected], None)

    def edit_dialog(self, kind, rows, col):
        if kind == 'USERS' and col == 5:
            self.review_integration(rows)
            return
        if kind == 'USERS' and col == 2 and len(set(rows)) > 1:
            messagebox.showinfo('CPF individual', 'Selecione apenas um registro para editar o CPF. Para normalizar documentos, use Correções em lote; cada linha conserva seu próprio CPF.')
            return
        win = tk.Toplevel(self)
        win.title('Decisão de preenchimento')
        win.geometry('740x335')
        win.transient(self)
        win.grab_set()
        frame = ttk.Frame(win, padding=22)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=f'{LABELS[kind]} — {len(rows)} registro(s) selecionado(s)', font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 12))
        selected_col = tk.StringVar(value=self.project.headers[kind][col or 0])
        select = ttk.Combobox(frame, values=self.project.headers[kind], textvariable=selected_col, state='readonly', width=80)
        select.pack(fill='x')
        if col is not None:
            select.configure(state='disabled')
        value = tk.StringVar()
        control = ttk.Combobox(frame, textvariable=value, width=80)
        control.pack(fill='x', pady=14)
        note = ttk.Label(frame, text='O valor informado será aplicado IGUAL a todas as linhas selecionadas. Isto não é uma normalização. Para preservar valores individuais, use Correções em lote.' if len(rows) > 1 else 'A decisão vale apenas para a linha selecionada. Campo vazio mantém a pendência se for obrigatório.', wraplength=680, style='Sub.TLabel')
        note.pack(anchor='w')
        def configure(_event=None):
            c = self.project.headers[kind].index(selected_col.get())
            r = next(r for r in self.analysis.records[kind] if r.row == rows[0])
            v = r.values[c]
            value.set('' if len(rows) > 1 else v.strftime('%d/%m/%Y') if isinstance(v, datetime) else text(v))
            control.configure(values=self.project.choices(kind, rows[0], c), show='*' if kind == 'USERS' and c == 8 else '')
        select.bind('<<ComboboxSelected>>', configure)
        configure()
        def apply():
            c = self.project.headers[kind].index(selected_col.get())
            chosen = value.get()
            if COMPANY_COL.get(kind) == c or (kind == 'USERS' and c == 5):
                chosen = chosen.split(' | ', 1)[0]
            try:
                self.project.set_value(kind, rows, c, chosen)
                win.destroy()
                self.refresh()
            except Exception as exc:
                messagebox.showerror('Decisão não aplicada', str(exc), parent=win)
        actions = ttk.Frame(frame)
        actions.pack(side='bottom', fill='x')
        ttk.Button(actions, text='Decidir depois', command=win.destroy).pack(side='left')
        ttk.Button(actions, text='Aplicar decisão', style='Primary.TButton', command=apply).pack(side='right')

    def review_integration(self, rows):
        preview = self.project.integration_suggestions(rows)
        win = tk.Toplevel(self)
        win.title('Concatenar códigos de integração')
        win.geometry('1180x580')
        win.transient(self)
        win.grab_set()
        frame = ttk.Frame(win, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Padrão sugerido: 0.CÓDIGOEXTRAFRUTI.1.CÓDIGOCASAFRUTI', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        pattern = tk.StringVar(value='0.{EXTRAFRUTI}.1.{CASAFRUTI}')
        ttk.Label(frame, text='Edite o formato usando {EXTRAFRUTI} e/ou {CASAFRUTI} como campos variáveis:').pack(anchor='w', pady=(8, 0))
        ttk.Entry(frame, textvariable=pattern).pack(fill='x')
        format_status = tk.StringVar()
        ttk.Label(frame, textvariable=format_status).pack(anchor='w')
        ttk.Label(frame, text='Cada linha usa seus próprios códigos. Confira a proposta e selecione os registros que deseja aplicar.\nPropostas completas vêm selecionadas. Propostas parciais ficam desmarcadas para você decidir; zeros à esquerda existentes como texto são preservados.', wraplength=1100).pack(anchor='w', pady=8)
        actions = ttk.Frame(frame)
        actions.pack(side='bottom', fill='x', pady=10)
        table = self.tree(frame, [('row', 'Linha', 60), ('name', 'Nome', 230), ('extra', 'Extrafruti', 120), ('casa', 'Casafruti', 120), ('before', 'Atual', 160), ('after', 'Proposta', 230), ('note', 'Situação', 320)])
        items = {}
        for p in preview:
            key = str(p['row'])
            items[key] = p
            table.insert('', 'end', iid=key, values=[p[k] for k in ('row', 'name', 'extra', 'casa', 'before', 'after', 'note')])
        table.selection_set([str(p['row']) for p in preview if p['after'] and p['complete'] and not p['duplicate']])
        def update_preview(*_):
            nonlocal preview
            table.delete(*table.get_children())
            try:
                preview = self.project.integration_suggestions(rows, pattern.get())
                format_status.set('Prévia atualizada com o formato informado.')
            except ValueError as exc:
                preview = []
                format_status.set(str(exc))
            for p in preview:
                table.insert('', 'end', iid=str(p['row']), values=[p[k] for k in ('row', 'name', 'extra', 'casa', 'before', 'after', 'note')])
            table.selection_set([str(p['row']) for p in preview if p['after'] and p['complete'] and not p['duplicate']])
        pattern.trace_add('write', update_preview)
        def apply():
            selected = set(table.selection())
            chosen = [p for p in preview if str(p['row']) in selected]
            if not chosen or any(not p['after'] or p['duplicate'] for p in chosen):
                messagebox.showinfo('Selecionar propostas', 'Selecione apenas registros com proposta válida e sem código duplicado.', parent=win)
                return
            if not messagebox.askyesno('Confirmar concatenação', f'Aplicar as {len(chosen)} propostas selecionadas? Cada registro receberá o código exibido na sua linha.', parent=win):
                return
            try:
                self.project.accept_integration_suggestions(chosen, pattern.get())
                win.destroy()
                self.refresh()
            except ValueError as exc:
                messagebox.showerror('Proposta não aplicada', str(exc), parent=win)
        ttk.Button(actions, text='Decidir depois', command=win.destroy).pack(side='left')
        ttk.Button(actions, text='Confirmar selecionadas', style='Primary.TButton', command=apply).pack(side='right')

    def review_recommendations(self):
        if not self.project:
            messagebox.showinfo('Recomendações', 'Analise uma planilha primeiro.')
            return
        win = tk.Toplevel(self)
        win.title('Aplicar recomendações em lote')
        win.geometry('1180x680')
        win.transient(self)
        win.grab_set()
        frame = ttk.Frame(win, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Escolha as categorias e confirme uma vez. Cada célula recebe sua própria proposta.\nCasos ambíguos, documentos longos e conflitos permanecem pendentes.', wraplength=1100).pack(anchor='w')
        bar = ttk.Frame(frame)
        bar.pack(fill='x', pady=10)
        categories = {name: tk.BooleanVar(value=True) for name in ['Espaços', 'Documentos', 'Datas', 'Sim/Não', 'Sexo', 'CEP', 'Telefones', 'E-mails', 'Preenchimento', 'Integração']}
        pattern = tk.StringVar(value='0.{EXTRAFRUTI}.1.{CASAFRUTI}')
        approved = tk.BooleanVar(value=False)
        summary = tk.StringVar()
        for name, variable in categories.items():
            ttk.Checkbutton(bar, text=name, variable=variable).pack(side='left')
        ttk.Label(frame, text='Formato da integração (somente campos de destino vazios):').pack(anchor='w')
        ttk.Entry(frame, textvariable=pattern).pack(fill='x', pady=5)
        ttk.Checkbutton(frame, text='Confirmo o uso dos domínios exibidos nas propostas de e-mail, mesmo sem domínio confirmado da unidade.', variable=approved).pack(anchor='w')
        ttk.Label(frame, textvariable=summary, wraplength=1100).pack(anchor='w', pady=8)
        actions = ttk.Frame(frame)
        actions.pack(side='bottom', fill='x', pady=8)
        table = self.tree(frame, [('category', 'Categoria', 130), ('kind', 'Carga', 130), ('row', 'Linha', 65), ('field', 'Campo', 200), ('before', 'Atual / origem', 250), ('after', 'Proposta', 270)])
        preview = []
        def refresh(*_):
            nonlocal preview
            table.delete(*table.get_children())
            selected = [name for name, var in categories.items() if var.get()]
            try:
                preview = self.project.recommendation_batch(selected, pattern.get(), approved.get())
                counts = {name: sum(p['category'] == name for p in preview) for name in selected}
                summary.set(f'{len(preview)} células propostas. ' + ' | '.join(f'{name}: {n}' for name, n in counts.items()) + '\nE-mails sem domínio confirmado só entram após marcar a confirmação acima. Correspondências aproximadas ficam para revisão individual.')
            except ValueError as exc:
                preview = []
                summary.set(str(exc))
            for p in preview:
                table.insert('', 'end', values=[p['category'], LABELS[p['kind']], p['row'], self.project.headers[p['kind']][p['col']], p['before'], p['after']])
            confirm.configure(state='normal' if preview else 'disabled')
        def apply():
            try:
                count = self.project.accept_recommendation_batch(preview, [name for name, var in categories.items() if var.get()], pattern.get(), approved.get())
                win.destroy()
                self.refresh()
                self.status.set(f'{count} correções aplicadas. Revise as pendências restantes e exporte para salvar as cargas.')
            except ValueError as exc:
                messagebox.showerror('Recomendações alteradas', str(exc), parent=win)
                refresh()
        ttk.Button(actions, text='Cancelar', command=win.destroy).pack(side='left')
        confirm = ttk.Button(actions, text='Confirmar todas as propostas exibidas', command=apply, style='Primary.TButton')
        confirm.pack(side='right')
        for var in [*categories.values(), pattern, approved]:
            var.trace_add('write', refresh)
        refresh()

    def review_email(self):
        selected = self.emails_tree.selection()
        if len(selected) != 1:
            messagebox.showinfo('Revisar e-mail', 'Selecione um e-mail para revisar.')
            return
        suggestion = self.email_items[selected[0]]
        if not suggestion.confirmed_domain:
            if messagebox.askyesno('Unidade e domínio pendentes', 'A sugestão usa provisoriamente o domínio original.\n\nDeseja definir a unidade do usuário agora? Depois confirme o domínio na aba Domínios das unidades.'):
                self.edit_dialog('USERS', [suggestion.row], 9)
            return
        if messagebox.askyesno('Aceitar sugestão?', f'{suggestion.name}\n\nAtual: {suggestion.original}\nSugestão: {suggestion.proposed}\n\n{suggestion.note}\n\nDeseja aplicar este endereço? A caixa postal deve ser confirmada com o cliente.'):
            try:
                self.project.accept_email(suggestion.row, suggestion.proposed)
                self.refresh()
            except Exception as exc:
                messagebox.showerror('Sugestão não aplicada', str(exc))

    def review_all_emails(self):
        if not self.project:
            messagebox.showinfo('Sugestões', 'Analise uma planilha primeiro.')
            return
        preview = self.project.analyze().suggestions
        if not preview:
            messagebox.showinfo('Sugestões', 'Não há e-mails repetidos para revisar.')
            return
        eligible = [s for s in preview if s.confirmed_domain and email_valid(s.proposed)]
        win = tk.Toplevel(self)
        win.title('Revisar todas as sugestões de e-mail')
        win.geometry('1120x590')
        win.minsize(850, 450)
        win.transient(self)
        win.grab_set()
        frame = ttk.Frame(win, padding=20)
        frame.pack(fill='both', expand=True)
        summary = tk.StringVar()
        approve_domains = tk.BooleanVar(value=False)
        ttk.Label(frame, textvariable=summary, font=('Segoe UI', 13, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Confira os endereços abaixo. Você pode aprovar os domínios exibidos para corrigir os e-mails agora, sem definir a unidade.', wraplength=1040).pack(anchor='w', pady=(6, 8))
        approval = ttk.Checkbutton(frame, text='Confirmo o uso dos domínios exibidos nas sugestões deste lote', variable=approve_domains)
        approval.pack(anchor='w', pady=(0, 8))
        actions = ttk.Frame(frame)
        actions.pack(side='bottom', fill='x', pady=(12, 0))
        ttk.Button(actions, text='Cancelar', command=win.destroy).pack(side='left')
        table = self.tree(frame, [('row', 'Linha', 65), ('name', 'Nome', 235), ('old', 'E-mail atual', 260), ('new', 'Sugestão', 280), ('state', 'Tratamento', 300)])
        def confirm():
            try:
                applied, pending = self.project.accept_all_emails(preview, approve_displayed_domains=approve_domains.get())
                win.destroy()
                self.refresh()
                self.status.set(f'{applied} sugestões aplicadas nesta revisão. {pending} sugestões da prévia ficaram pendentes. Exporte para salvar as cargas.')
            except ValueError as exc:
                messagebox.showerror('Sugestões não aplicadas', str(exc), parent=win)
        confirm_button = ttk.Button(actions, style='Primary.TButton', command=confirm)
        confirm_button.pack(side='right')
        def update_preview():
            eligible = [s for s in preview if (s.confirmed_domain or approve_domains.get()) and email_valid(s.proposed)]
            summary.set(f'{len(eligible)} alterações propostas | {len(preview) - len(eligible)} pendentes')
            confirm_button.configure(text=f'Confirmar {len(eligible)} alterações', state='normal' if eligible else 'disabled')
            table.delete(*table.get_children())
            for s in preview:
                state = 'Será aplicada' if s in eligible else 'Marque a confirmação dos domínios' if not s.confirmed_domain else 'Pendente: endereço insuficiente'
                table.insert('', 'end', values=[s.row, s.name, s.original, s.proposed, state])
        approval.configure(command=update_preview)
        update_preview()

    def edit_domain(self):
        selected = self.domains_tree.selection()
        if len(selected) != 1:
            messagebox.showinfo('Domínio', 'Selecione uma unidade.')
            return
        cnpj, name, proposed, current = self.domains_tree.item(selected[0], 'values')
        from tkinter.simpledialog import askstring
        value = askstring('Confirmar domínio', f'Unidade: {name}\nCNPJ: {cnpj}\n\nQual domínio deseja usar nas sugestões desta unidade?', initialvalue=current or proposed, parent=self)
        if value is not None:
            try:
                self.project.confirm_domain(cnpj, value)
                self.refresh()
            except ValueError as exc:
                messagebox.showerror('Domínio inválido', str(exc))

    def save_session(self):
        if not self.project:
            messagebox.showinfo('Revisão', 'Analise uma planilha primeiro.')
            return
        path = filedialog.asksaveasfilename(title='Salvar decisões para continuar depois', defaultextension='.json', filetypes=[('Revisão do validador', '*.json')])
        if path:
            try:
                self.project.save_session(path)
                self.status.set('Revisão salva. Alterações de senha não são salvas no arquivo de revisão.')
            except Exception as exc:
                messagebox.showerror('Falha ao salvar', str(exc))

    def open_session(self):
        if not self.project:
            messagebox.showinfo('Revisão', 'Analise a planilha original antes de abrir as decisões salvas.')
            return
        path = filedialog.askopenfilename(title='Abrir revisão', filetypes=[('Revisão do validador', '*.json')])
        if path:
            try:
                self.project.load_session(path)
                self.refresh()
            except Exception as exc:
                messagebox.showerror('Revisão não carregada', str(exc))

    def export_files(self):
        if not self.project:
            messagebox.showinfo('Exportar', 'Analise uma planilha primeiro.')
            return
        if Path(self.source.get()).resolve() != self.project.source or Path(self.templates.get()).resolve() != self.project.template_dir:
            messagebox.showinfo('Atualizar análise', 'O arquivo ou a pasta dos modelos mudou. Clique em Analisar planilha antes de exportar.')
            return
        self.analysis = self.project.analyze()
        draft = bool(self.analysis.blocking)
        if draft and not messagebox.askyesno('Exportar como rascunho?', f'Há {len(self.analysis.blocking)} pendências.\n\nDeseja exportar um RASCUNHO para conferência?\nEle não deve ser importado como carga final.'):
            return
        destination = filedialog.askdirectory(title='Pasta para salvar as cargas e o relatório')
        if not destination:
            return
        self.status.set('Exportando e conferindo os arquivos...')
        self.update_idletasks()
        try:
            path = self.project.export(destination, draft=draft)
            self.last_export = path
            self.status.set(f'Exportação concluída: {path}')
            messagebox.showinfo('Exportação concluída', f'Quatro cargas, relatório e revisão salvos em:\n\n{path}\n\n' + ('Rascunho com pendências.' if draft else 'Validações locais concluídas. Importação no Paytrack não testada.'))
        except Exception as exc:
            self.status.set('A exportação não foi concluída.')
            messagebox.showerror('Falha ao exportar', str(exc))

    def close_app(self):
        if self.project and self.project.history:
            if not messagebox.askyesno('Fechar', 'As decisões só ficam disponíveis depois se você salvar a revisão ou exportar as cargas. Deseja fechar?'):
                return
        self.destroy()


def main():
    parser = argparse.ArgumentParser(description='Validador local de cargas Paytrack')
    parser.add_argument('--check', type=Path, help='Analisar sem abrir a interface')
    parser.add_argument('--templates', type=Path, default=resource_dir() / 'templates')
    parser.add_argument('--result', type=Path, help='Salvar resumo da verificação em JSON')
    parser.add_argument('--export-draft', type=Path, help='Exportar rascunho com --check')
    args = parser.parse_args()
    if args.check:
        project = Project(args.check, args.templates)
        a = project.analyze()
        summary = {'counts': {k: len(v) for k, v in a.records.items()}, 'pending': len(a.blocking), 'email_suggestions': len(a.suggestions)}
        if args.export_draft:
            summary['export'] = str(project.export(args.export_draft, draft=True))
        if args.result:
            args.result.write_text(json.dumps(summary, indent=2), encoding='utf8')
        elif sys.stdout:
            print(json.dumps(summary))
    else:
        app = App()
        app.templates.set(str(args.templates))
        app.mainloop()


if __name__ == '__main__':
    main()
