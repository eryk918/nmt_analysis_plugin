# -*- coding: utf-8 -*-
import os

from PyQt5.QtCore import Qt
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox
from qgis.core import QgsCoordinateReferenceSystem

from ...utils import repair_comboboxes, normalize_path, \
    get_project_config, set_project_config, project

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'SetProjection_UI.ui'))


class SetProjection_UI(QDialog, FORM_CLASS):
    def __init__(self, setProjection, parent=None, allow_silent=False):
        super(SetProjection_UI, self).__init__(parent)
        self.setupUi(self)
        self.setProjection = setProjection
        repair_comboboxes(self)
        self.silent = allow_silent
        self.setWindowIcon(self.setProjection.main.icon)
        self.output_layer_btn.clicked.connect(self.get_output_file)
        self.wyjscie.textChanged.connect(self.enable_checkbox)

    def setup_dialog(self):
        self.pushButton_zapisz.clicked.connect(self.validate_fields)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.dest_proj.setCrs(project.crs())

    def validate_fields(self):
        if (self.wejscie.filePath() and self.dest_proj.crs().postgisSrid() != 0) or self.silent:
            self.accept()
            self.setProjection.set_proj_process(
                self.wejscie.lineEdit().text(),
                self.dest_proj.crs().postgisSrid(),
                normalize_path(self.wyjscie.text()),
                self.add_to_project_cbbx.isChecked())
        else:
            QMessageBox.warning(
                self, 'Ostrzeżenie',
                'Sprawdź poprawność danych wejściowych i ich odwzorowań!\n',
                QMessageBox.Ok)

    def enable_checkbox(self, text):
        if text:
            self.add_to_project_cbbx.setEnabled(True)
        else:
            self.add_to_project_cbbx.setChecked(True)
            self.add_to_project_cbbx.setEnabled(False)

    def get_output_file(self):
        if self.wejscie.lineEdit().text():
            path = get_project_config('NMT_analysis', 'set_projection', '')
            if not os.path.exists(path):
                path = ""
            filename = QFileDialog.getExistingDirectory(
                self, "Wybierz lokalizacje do zapisu przetłumaczonych warstw",
                path)
            if filename:
                self.wyjscie.setText(filename)
            set_project_config('NMT_analysis', 'set_projection',
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
