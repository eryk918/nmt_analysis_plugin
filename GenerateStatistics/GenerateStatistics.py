# -*- coding: utf-8 -*-
import os
import shutil
from datetime import datetime
from tempfile import mkdtemp

from qgis import processing
from qgis.PyQt.QtWidgets import QMessageBox, QApplication

from ..GenerateStatistics.UI.GenerateStatistics_UI import GenerateStatistics_UI
from ..utils import project, create_progress_bar, i_iface, normalize_path, \
    open_other_files, Qt


class GenerateStatistics:
    def __init__(self, parent):
        self.main = parent
        self.iface = i_iface
        self.project_path = os.path.dirname(
            os.path.abspath(project.fileName()))
        self.actual_crs = project.crs().postgisSrid()

    def run(self):
        self.dlg = GenerateStatistics_UI(self)
        self.dlg.setup_dialog()
        self.dlg.run_dialog()

    def invalid_data_error(self):
        self.clean_after_analysis()
        if self.silent:
            return 'Generowanie statystyki nie powiodło się',
        else:
            QMessageBox.critical(
                self.dlg,
                'Analiza NMT',
                'Dane są niepoprawne!\n'
                'Generowanie statystyki nie powiodło się!',
                QMessageBox.Ok)

    def clean_after_analysis(self):
        QApplication.processEvents()
        if hasattr(self, "progress"):
            self.progress.close()
        self.list_of_files = []
        if not self.tmp_layers_flag:
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def generate_statistics(self, input_layer):
        if not self.tmp_layers_flag:
            tmp_layer_filepath = os.path.join(
                self.tmp_dir, f'{os.path.basename(input_layer)}.html')
        else:
            tmp_layer_filepath = os.path.join(
                self.export_path, f'{os.path.basename(input_layer)}.html')
        if os.path.exists(tmp_layer_filepath):
            tmp_path = os.path.splitext(tmp_layer_filepath)[0]
            tmp_layer_filepath = \
                f'{tmp_path}_{datetime.now().strftime("%Y-%m-%d_%H_%M_%S")}.html'
        processing.run(
            'qgis:rasterlayerstatistics',
            {'INPUT': input_layer, 'OUTPUT_HTML_FILE': tmp_layer_filepath,
             'BAND': 1})
        self.list_of_files.append(tmp_layer_filepath)

    def generate_statistics_process(self, input_files, export_directory,
                                    q_add_to_project, silent=False):
        self.silent = silent
        self.progress = create_progress_bar(
            0, txt='Trwa generowanie statystyki...')
        if not self.silent:
            self.progress.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.progress.show()
        QApplication.processEvents()
        self.tmp_dir = mkdtemp(suffix=f'nmt_generate_statistics')
        self.tmp_layers_flag = False
        if export_directory and export_directory not in (' ', ',') and \
                export_directory != ".":
            self.export_path = normalize_path(export_directory)
            self.tmp_layers_flag = True
        self.list_of_files = []
        self.last_progress_value = 0
        QApplication.processEvents()
        try:
            self.generate_statistics(input_files)
        except RuntimeError:
            return self.invalid_data_error()
        if q_add_to_project:
            for file in self.list_of_files:
                open_other_files(file)
        self.dlg.close()
        QApplication.processEvents()
        if hasattr(self, "progress"):
            self.progress.close()
        self.list_of_files = []
        if not self.silent:
            QMessageBox.information(
                self.dlg, 'Analiza NMT',
                'Generowanie statystyki zakończone.', QMessageBox.Ok)
