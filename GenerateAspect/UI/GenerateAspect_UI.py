# -*- coding: utf-8 -*-
import os

from PyQt5.QtCore import Qt
from qgis.PyQt import uic, QtGui
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox

from ...utils import repair_comboboxes, normalize_path, \
    get_project_config, set_project_config

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'GenerateAspect_UI.ui'))


class GenerateAspect_UI(QDialog, FORM_CLASS):
    def __init__(self, GenerateAspect, parent=None, allow_silent=False):
        super(GenerateAspect_UI, self).__init__(parent)
        self.setupUi(self)
        self.generateAspect = GenerateAspect
        self.silent = allow_silent
        repair_comboboxes(self)
        self.setWindowIcon(self.generateAspect.main.icon)
        self.output_layer_btn.clicked.connect(self.get_output_file)
        self.wyjscie.textChanged.connect(self.enable_checkbox)

    def setup_dialog(self):
        self.pushButton_zapisz.clicked.connect(self.validate_fields)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

    def validate_fields(self):
        if self.wejscie.filePath() or self.silent:
            self.accept()
            self.generateAspect.gen_aspect_process(
                self.wejscie.lineEdit().text(),
                self.zindex_spinbox.value(),
                normalize_path(self.wyjscie.text()),
                self.add_to_project_cbbx.isChecked())
        else:
            QMessageBox.warning(
                self, 'Ostrzeżenie',
                'Wybierz poprawne ścieżki do wygenerowania cieniowania!',
                QMessageBox.Ok)

    def enable_checkbox(self, text):
        if text:
            self.add_to_project_cbbx.setEnabled(True)
        else:
            self.add_to_project_cbbx.setChecked(True)
            self.add_to_project_cbbx.setEnabled(False)

    def get_output_file(self):
        path = get_project_config('NMT_analysis', 'generate_hillshade', '')
        if not os.path.exists(path):
            path = ""
        filename, __ = QFileDialog.getSaveFileName(
            self, "Wybierz lokalizacje do zapisu rastra modelu cieniowania",
            path, "*.tif")
        if filename:
            self.wyjscie.setText(filename)
        set_project_config('NMT_analysis', 'generate_hillshade',
                           os.path.dirname(normalize_path(filename)))

    def run_dialog(self):
        self.show()
        self.exec_()
