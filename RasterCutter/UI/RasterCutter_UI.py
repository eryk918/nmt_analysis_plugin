# -*- coding: utf-8 -*-
import os

from PyQt5.QtCore import Qt
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog

from ...utils import repair_dialog_combos, InfoBox, \
    normalize_path, get_project_config, set_project_config

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'RasterCutter_UI.ui'))


class RasterCutter_UI(QDialog, FORM_CLASS):
    def __init__(self, rasterCutter, parent=None):
        super(RasterCutter_UI, self).__init__(parent)
        self.setupUi(self)
        self.rasterCutter = rasterCutter
        repair_dialog_combos(self)
        self.output_layer_btn.clicked.connect(self.get_output_file)
        self.wyjscie.textChanged.connect(self.enable_checkbox)

    def setup_dialog(self):
        self.pushButton_zapisz.clicked.connect(self.validate_fields)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

    def validate_fields(self):
        if self.wejscie.filePath() and self.maska.filePath():
            self.accept()
            self.rasterCutter.cutting_process(
                self.wejscie.lineEdit().text(),
                self.maska.lineEdit().text(),
                normalize_path(self.wyjscie.text()),
                self.add_to_project_cbbx.isChecked())
        else:
            InfoBox(
                self,
                'Wybierz poprawne ścieżki do pocięcia rastra!'
            ).button_ok()

    def enable_checkbox(self, text):
        if text:
            self.add_to_project_cbbx.setEnabled(True)
        else:
            self.add_to_project_cbbx.setChecked(True)
            self.add_to_project_cbbx.setEnabled(False)

    def get_output_file(self):
        path = get_project_config('NMT_analysis', 'raster_cut_path', '')
        if not os.path.exists(path):
            path = ""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Wybierz lokalizacje do zapisu rastrów", path)
        if dir_path:
            self.wyjscie.setText(dir_path)
        set_project_config('NMT_analysis', 'raster_cut_path',
                           os.path.dirname(normalize_path(dir_path)))

    def run_dialog(self):
        self.show()
        self.exec_()
