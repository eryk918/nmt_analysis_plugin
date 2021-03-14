# -*- coding: utf-8 -*-
import os

from PyQt5.QtCore import Qt
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox

from ...utils import repair_comboboxes, normalize_path, \
    get_project_config, set_project_config

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'GenerateStatistics_UI.ui'))


class GenerateStatistics_UI(QDialog, FORM_CLASS):
    def __init__(self, GenerateStatistics, parent=None):
        super(GenerateStatistics_UI, self).__init__(parent)
        self.setupUi(self)
        self.generateStatistics = GenerateStatistics
        repair_comboboxes(self)
        self.setWindowIcon(self.generateStatistics.main.icon)
        self.output_layer_btn.clicked.connect(self.get_output_file)
        self.wyjscie.textChanged.connect(self.enable_checkbox)

    def setup_dialog(self):
        self.pushButton_zapisz.clicked.connect(self.validate_fields)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

    def validate_fields(self):
        if self.wejscie.filePath():
            self.accept()
            self.generateStatistics.generate_statistics_process(
                self.wejscie.splitFilePaths(self.wejscie.lineEdit().text()),
                normalize_path(self.wyjscie.text()),
                self.add_to_project_cbbx.isChecked())
        else:
            QMessageBox.warning(
                self, 'Ostrzeżenie', 'Sprawdź poprawność danych wejściowych!\n'
                , QMessageBox.Ok)

    def enable_checkbox(self, text):
        if text:
            self.add_to_project_cbbx.setEnabled(True)
        else:
            self.add_to_project_cbbx.setChecked(True)
            self.add_to_project_cbbx.setEnabled(False)

    def get_output_file(self):
        if self.wejscie.lineEdit().text():
            path = get_project_config(
                'NMT_analysis', 'generate_statistics', '')
            if not os.path.exists(path):
                path = ""
            filename = QFileDialog.getExistingDirectory(
                self, "Wybierz lokalizacje do zapisu wygenerowanych statystyk",
                path)
            if filename:
                self.wyjscie.setText(filename)
            set_project_config('NMT_analysis', 'generate_statistics',
                               os.path.dirname(normalize_path(filename)))
        else:
            QMessageBox.warning(
                self, 'Ostrzeżenie',
                'Nie można wybrać lokalizacji zapisu.\n'
                'Wybierz poprawną ścieżkę wejściową!',
                QMessageBox.Ok)

    def run_dialog(self):
        self.show()
        self.exec_()