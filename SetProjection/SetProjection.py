# -*- coding: utf-8 -*-
import os
import shutil
from tempfile import mkdtemp

from PyQt5.QtCore import Qt
from qgis import processing
from qgis.PyQt.QtWidgets import QMessageBox, QApplication

from ..SetProjection.UI.SetProjection_UI import SetProjection_UI
from ..utils import project, create_progress_bar, i_iface, \
    normalize_path, add_rasters_to_project, add_vectors_to_project


class SetProjection:
    def __init__(self, parent):
        self.main = parent
        self.iface = i_iface
        self.project_path = os.path.dirname(
            os.path.abspath(project.fileName()))
        self.actual_crs = project.crs().postgisSrid()

    def run(self):
        self.dlg = SetProjection_UI(self)
        self.dlg.setup_dialog()
        self.dlg.run_dialog()

    def invalid_data_error(self):
        self.clean_after_analysis()
        if self.silent:
            return 'Nadawanie odwzorowania nie powiodło się',
        else:
            QMessageBox.critical(
                self.dlg,
                'Analiza NMT',
                'Dane są niepoprawne!\n'
                'Nadawanie odwzorowania nie powiodło się!',
                QMessageBox.Ok)

    def clean_after_analysis(self):
        QApplication.processEvents()
        if hasattr(self, "progress"):
            self.progress.close()
        self.list_of_layers = []
        if not self.tmp_layers_flag:
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def set_projection(self, input_layer, dest_crs):
        if not self.tmp_layers_flag:
            tmp_layer_filepath = os.path.join(
                self.tmp_dir, f'{os.path.basename(input_layer)}')
        else:
            tmp_layer_filepath = os.path.join(
                self.export_path, f'{os.path.basename(input_layer)}')

        if os.path.splitext(input_layer)[-1] in ('.shp', '.gpkg'):
            processing.run(
                'qgis:reprojectlayer',
                {'INPUT': input_layer, 'OUTPUT': tmp_layer_filepath,
                 'TARGET_CRS': f'EPSG:{dest_crs}'})
        else:
            processing.run(
                'gdal:translate',
                {'INPUT': input_layer, 'OUTPUT': tmp_layer_filepath,
                 'TARGET_CRS': f'EPSG:{dest_crs}'})
        self.list_of_layers.append(tmp_layer_filepath)

    def set_proj_process(self, input_files, dest_crs,
                         export_directory, q_add_to_project, silent=False):
        self.silent = silent
        self.progress = create_progress_bar(
            0, txt='Trwa nadawanie odwzorowania...')
        if not self.silent:
            self.progress.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.progress.show()
        QApplication.processEvents()
        self.tmp_dir = mkdtemp(suffix=f'nmt_set_projection')
        self.tmp_layers_flag = False
        if export_directory and export_directory not in (' ', ',') and \
                export_directory != ".":
            self.export_path = normalize_path(export_directory)
            self.tmp_layers_flag = True
        self.list_of_layers = []
        self.last_progress_value = 0
        self.layer_type = None
        QApplication.processEvents()
        try:
            self.set_projection(input_files, dest_crs)
        except RuntimeError:
            return self.invalid_data_error()
        if q_add_to_project:
            for lyr in self.list_of_layers:
                if os.path.splitext(lyr)[-1] in ('.shp', '.gpkg'):
                    add_vectors_to_project("PRZETŁUMACZONE_WARSTWY", [lyr])
                else:
                    add_rasters_to_project("PRZETŁUMACZONE_WARSTWY", [lyr])
        self.clean_after_analysis()
        self.dlg.close()
        if not self.silent:
            QMessageBox.information(
                self.dlg, 'Analiza NMT',
                'Nadawanie odwzorowania zakończone.', QMessageBox.Ok)
