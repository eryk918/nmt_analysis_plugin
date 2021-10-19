# -*- coding: utf-8 -*-
import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox

from ...utils import repair_comboboxes, \
    standarize_path, get_project_settings, set_project_settings, Qt

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'GeneratePolygons_UI.ui'))


class GeneratePolygons_UI(QDialog, FORM_CLASS):
    def __init__(self, generatePolygons, parent=None, allow_silent=False):
        super(GeneratePolygons_UI, self).__init__(parent)
        self.setupUi(self)
        self.generatePolygons = generatePolygons
        repair_comboboxes(self)
        self.setWindowIcon(self.generatePolygons.main.icon)
        self.output_layer_btn.clicked.connect(self.get_output_file)
        self.wyjscie.textChanged.connect(self.enable_checkbox)
        self.silent = allow_silent
        self.polygon_type = {
            'prostokąt': 0,
            'romb': 1,
            'wielokąt': 2
        }

    def setup_dialog(self):
        self.pushButton_zapisz.clicked.connect(self.validate_fields)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.feat_type_cbbx.addItems(self.polygon_type.keys())

    def validate_fields(self):
        if self.wejscie.filePath() or \
                self.wejscie.lineEdit().placeholderText() and \
                self.maska.filePath() or \
                self.maska.lineEdit().placeholderText():
            self.accept()
            self.generatePolygons.generate_polys(
                self.wejscie.lineEdit().text(),
                self.maska.lineEdit().text(),
                standarize_path(self.wyjscie.text()),
                self.height_spinbox.value(),
                self.add_to_project_cbbx.isChecked(),
                self.offset_spinbox.value(),
                self.amount_spinbox.value(),
                self.height_feat.value(),
                self.width_feat.value(),
                self.angle_feat.value(),
                self.polygon_type[self.feat_type_cbbx.currentText()])
        else:
            QMessageBox.warning(
                self, 'Ostrzeżenie',
                'Wybierz poprawne ścieżki do przeprowadzenia analizy!',
                QMessageBox.Ok)

    def enable_checkbox(self, text):
        if text:
            self.add_to_project_cbbx.setEnabled(True)
        else:
            self.add_to_project_cbbx.setChecked(True)
            self.add_to_project_cbbx.setEnabled(False)

    def get_output_file(self):
        path = get_project_settings('NMT_analysis', 'nmt_poly_export_path', '')
        if not os.path.exists(path):
            path = ""
        filename, __ = QFileDialog.getSaveFileName(
            self, "Zapisz plik", path, "*.shp")
        if filename:
            self.wyjscie.setText(filename)
        set_project_settings('NMT_analysis', 'nmt_poly_export_path',
                           os.path.dirname(standarize_path(filename)))

    def run_dialog(self):
        self.show()
        self.exec_()
