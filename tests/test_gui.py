import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App
from test_engine import source_file, BASE


class GuiTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
