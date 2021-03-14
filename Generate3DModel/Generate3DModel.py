# -*- coding: utf-8 -*-
import os

from qgis.PyQt.QtWidgets import QMessageBox

from ..utils import i_iface


class Generate3DModel:
    def __init__(self, parent):
        self.main = parent
        self.iface = i_iface
        self.main.btn_gen_model3d.setEnabled(True)

    def run(self):
        if os.path.exists(self.main.qgis2threejs_path):
            try:
                self.main.q23js.classFactory(i_iface).openExporter('')
                self.main.qgis2threejs_exists = True
            except ModuleNotFoundError:
                self.throw_critical_info_about_q23js()
                self.main.qgis2threejs_exists = False
        else:
            self.main.btn_gen_model3d.setEnabled(False)
            self.main.qgis2threejs_exists = False
        if not self.main.qgis2threejs_exists:
            self.throw_critical_info_about_q23js()
            self.qgis2threejs_exists = True

    def throw_critical_info_about_q23js(self):
        QMessageBox.critical(
            None, 'Brak wtyczki Qgis2threejs - Analiza NMT',
            'Opcja "Stwórz model 3D" jest niedostępna!\n'
            'Aby używać mechanizmu generowania modelu 3D zainstaluj wtyczkę\n'
            '"Qgis2threejs" autora "Minoru Akagi" i spróbuj ponownie.\n',
            QMessageBox.Ok)
