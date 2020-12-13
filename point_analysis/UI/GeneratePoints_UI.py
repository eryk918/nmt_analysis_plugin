# -*- coding: utf-8 -*-
import os

from PyQt5.QtCore import Qt
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog

from ...utils import lazy_repair_combobox_in_dialog, CustomMessageBox, \
    normalize_path, get_project_config, set_project_config

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'GeneratePoints_UI.ui'))


class GeneratePoints_UI(QDialog, FORM_CLASS):
    def __init__(self, generatePoints, parent=None):
        super(GeneratePoints_UI, self).__init__(parent)
        self.setupUi(self)
        self.generatePoints = generatePoints
        lazy_repair_combobox_in_dialog(self)
        self.output_layer_btn.clicked.connect(self.get_output_file)
        self.wyjscie.textChanged.connect(self.enable_checkbox)

    def setup_dialog(self):
        self.pushButton_zapisz.clicked.connect(self.check_if_lineedit_empty)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

    def check_if_lineedit_empty(self):
        if self.wejscie.filePath() and self.maska.filePath():
            self.accept()
            self.generatePoints.analysis_process(
                self.wejscie.lineEdit().text(),
                self.maska.lineEdit().text(),
                normalize_path(self.wyjscie.text()),
                int(self.analiza_min.text()),
                int(self.analiza_max.text()),
                self.add_to_project_cbbx.isChecked(),
                int(self.analiza_radius.text())
            )
        else:
            CustomMessageBox(
                self,
                'Wybierz poprawne ścieżki do przeprowadzenia analizy!'
            ).button_ok()

    def enable_checkbox(self, text):
        if text:
            self.add_to_project_cbbx.setEnabled(True)
        else:
            self.add_to_project_cbbx.setChecked(True)
            self.add_to_project_cbbx.setEnabled(False)

    def get_output_file(self):
        path = get_project_config('NMT_analysis', 'nmt_export_path', '')
        if not os.path.exists(path):
            path = ""
        filename, __ = QFileDialog.getSaveFileName(
            self, "Zapisz plik", path, "*.shp")
        if filename:
            self.wyjscie.setText(filename)
        set_project_config('NMT_analysis', 'nmt_export_path',
                           os.path.dirname(normalize_path(filename)))

    def run_dialog(self):
        self.show()
        self.exec_()
