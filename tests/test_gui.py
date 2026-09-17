import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App
from test_engine import source_file, BASE


class GuiTests(unittest.TestCase):
    def test_normalization_cancel_then_category_confirmation(self):
        self.app.load_project(ask=False)
        self.app.normalization_category.set('Documentos')
        self.app.refresh_normalizations()
        count = len(self.app.normalization_items)
        self.assertGreater(count, 0)
        with patch('app.messagebox.askyesno', return_value=False):
            self.app.apply_normalizations(all_rows=True)
        self.assertFalse(self.app.project.decisions)
        with patch('app.messagebox.askyesno', return_value=True):
            self.app.apply_normalizations(all_rows=True)
        self.assertFalse(self.app.normalization_items)
        self.assertTrue(self.app.project.normalizations())

    def test_duplicate_comparison_masks_password_and_preserves_rows(self):
        import tkinter as tk
        self.app.load_project(ask=False)
        records = self.app.project.records['USERS']
        records[1].values[2] = records[0].values[2]
        records[0].values[8] = 'SECRET_TEST_PASSWORD'
        self.app.refresh()
        ids = self.app.duplicates_tree.get_children()
        self.assertEqual(len(ids), 1)
        self.app.duplicates_tree.selection_set(ids[0])
        self.app.compare_duplicates()
        win = next(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))
        trees = [c for w in win.winfo_children() for c in w.winfo_children() if c.winfo_class() == 'Treeview']
        self.assertEqual(len(trees), 1)
        values = [trees[0].item(i, 'values') for i in trees[0].get_children()]
        self.assertEqual(len(values), 14)
        self.assertNotIn('SECRET_TEST_PASSWORD', str(values))
        win.destroy()
        self.assertFalse(self.app.project.decisions)
        self.app.project.set_value('USERS', [records[1].row], 2, '99999999999')
        self.app.refresh()
        self.assertFalse(self.app.duplicates_tree.get_children())
        self.assertEqual(len(self.app.analysis.records['USERS']), 3)

    def test_overview_counts_navigation_and_refresh(self):
        self.app.load_project(ask=False)
        values = self.app.overview_tree.item('USERS', 'values')
        self.assertEqual(int(values[1]), 3)
        self.assertEqual(int(values[2]), 2)
        self.assertEqual(int(values[3]), 2)
        self.assertEqual(int(values[4]), sum(1 for i in self.app.analysis.issues if i.kind == 'USERS' and i.severity == 'Pendente'))
        self.app.open_overview('USERS', '#3')
        self.assertTrue(all(i.kind == 'USERS' and i.severity == 'Erro' for i in self.app.issue_items.values()))
        self.assertEqual(len(self.app.issue_items), 2)
        self.app.open_overview('CUST', '#5')
        self.assertEqual(len(self.app.issue_items), 1 + sum(p['kind'] == 'CUST' for p in self.app.project.normalizations()))
        self.app.open_overview('EMPLOYER', '#2')
        self.assertEqual(len(self.app.data_items), 1)
        self.app.open_overview('USERS', '#4')
        self.assertEqual(self.app.tabs.select(), str(self.app.emails_tab))
        self.app.project.accept_all_emails(self.app.analysis.suggestions, approve_displayed_domains=True)
        self.app.refresh()
        values = self.app.overview_tree.item('USERS', 'values')
        self.assertEqual(int(values[2]), 0)
        self.assertEqual(int(values[3]), 0)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.source = Path(self.tmp.name) / 'source.xlsx'
        source_file(self.source)
        self.app = App()
        self.app.withdraw()
        self.app.source.set(str(self.source))
        self.app.templates.set(str(BASE / 'templates'))

    def tearDown(self):
        self.app.destroy()
        self.tmp.cleanup()

    def test_load_prompts_and_declining_keeps_pending(self):
        with patch('app.messagebox.askyesno', return_value=False) as question:
            self.app.load_project()
        question.assert_called_once()
        self.assertTrue(self.app.analysis.blocking)
        self.assertEqual(self.app.project.decisions, {})
        self.assertEqual(len(self.app.email_items), 2)

    def test_decline_email_unit_question_does_not_change_values(self):
        self.app.load_project(ask=False)
        self.app.emails_tree.selection_set('2')
        with patch('app.messagebox.askyesno', return_value=False):
            self.app.review_email()
        self.assertEqual(self.app.project.decisions, {})

    def test_decline_issue_question_does_not_change_values(self):
        self.app.load_project(ask=False)
        key = next(k for k, issue in self.app.issue_items.items() if issue.kind == 'USERS' and issue.col == 9)
        self.app.issues_tree.selection_set(key)
        with patch('app.messagebox.askyesno', return_value=False):
            self.app.edit_issues()
        self.assertEqual(self.app.project.decisions, {})

    def test_explicit_email_acceptance_refreshes_ui(self):
        self.app.load_project(ask=False)
        self.app.project.set_value('USERS', [2], 9, '01234567000189')
        self.app.project.confirm_domain('01234567000189', 'example.com')
        self.app.refresh()
        proposed = self.app.email_items['2'].proposed
        self.app.emails_tree.selection_set('2')
        with patch('app.messagebox.askyesno', return_value=True):
            self.app.review_email()
        self.assertEqual(self.app.project.analyze().records['USERS'][0].values[3], proposed)
        self.assertNotIn('2', self.app.email_items)

    def test_export_cancel_then_explicit_draft(self):
        self.app.load_project(ask=False)
        with patch('app.messagebox.askyesno', return_value=False), patch('app.filedialog.askdirectory') as folder:
            self.app.export_files()
        folder.assert_not_called()
        with patch('app.messagebox.askyesno', return_value=True), patch('app.filedialog.askdirectory', return_value=self.tmp.name), patch('app.messagebox.showinfo'):
            self.app.export_files()
        self.assertIsNotNone(self.app.last_export)
        self.assertTrue(self.app.last_export.name.startswith('RASCUNHO_'))
        self.assertTrue((self.app.last_export / 'DEFAULT_USERS.xlsx').exists())

    def test_changed_path_requires_new_analysis(self):
        self.app.load_project(ask=False)
        self.app.source.set(str(Path(self.tmp.name) / 'another.xlsx'))
        with patch('app.messagebox.showinfo'), patch('app.filedialog.askdirectory') as folder:
            self.app.export_files()
        folder.assert_not_called()

    def test_batch_preview_cancel_and_confirm(self):
        import tkinter as tk
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        self.app.load_project(ask=False)
        self.app.project.set_value('USERS', [2, 3], 9, '01234567000189')
        self.app.project.confirm_domain('01234567000189', 'example.com')
        self.app.refresh()
        before = dict(self.app.project.decisions)
        self.app.review_all_emails()
        win = next(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))
        next(w for w in descendants(win) if w.winfo_class() == 'TButton' and w.cget('text') == 'Cancelar').invoke()
        self.assertEqual(self.app.project.decisions, before)
        self.app.review_all_emails()
        win = next(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))
        next(w for w in descendants(win) if w.winfo_class() == 'TButton' and w.cget('text') == 'Confirmar 2 alterações').invoke()
        self.assertFalse(self.app.project.analyze().suggestions)

    def test_domain_checkbox_enables_batch_and_can_be_unchecked(self):
        import tkinter as tk
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        self.app.load_project(ask=False)
        self.app.review_all_emails()
        win = next(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))
        controls = list(descendants(win))
        button = next(w for w in controls if w.winfo_class() == 'TButton' and str(w.cget('text')).startswith('Confirmar'))
        check = next(w for w in controls if w.winfo_class() == 'TCheckbutton')
        self.assertTrue(button.instate(['disabled']))
        check.invoke()
        self.assertFalse(button.instate(['disabled']))
        self.assertEqual(button.cget('text'), 'Confirmar 2 alterações')
        check.invoke()
        self.assertTrue(button.instate(['disabled']))
        self.assertFalse(self.app.project.decisions)
        check.invoke()
        button.invoke()
        self.assertFalse(self.app.project.analyze().suggestions)
        self.assertTrue(all(r.values[9] == '' for r in self.app.project.analyze().records['USERS']))


if __name__ == '__main__':
    unittest.main()
