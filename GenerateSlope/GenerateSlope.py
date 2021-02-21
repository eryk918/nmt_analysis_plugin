# -*- coding: utf-8 -*-
import os
import shutil
from tempfile import mkdtemp

from PyQt5.QtCore import Qt
from qgis import processing
from qgis.PyQt.QtWidgets import QMessageBox, QApplication

from ..GenerateSlope.UI.GenerateSlope_UI import GenerateSlope_UI
from ..utils import project, create_progress_bar, i_iface, \
    normalize_path, add_rasters_to_project


class GenerateSlope:
    def __init__(self, parent):
        self.main = parent
        self.iface = i_iface
        self.project_path = os.path.dirname(
            os.path.abspath(project.fileName()))
        self.actual_crs = project.crs().postgisSrid()

    def run(self):
        self.dlg = GenerateSlope_UI(self)
        self.dlg.setup_dialog()
        self.dlg.run_dialog()

    def invalid_data_error(self):
        if hasattr(self, "progress"):
            self.progress.close()
        self.clean_after_analysis()
        QMessageBox.critical(
            self.dlg,
            'Analiza NMT',
            'Dane są niepoprawne!\n'
            'Generowanie modelu nachylenia nie powiodło się!',
            QMessageBox.Ok)

    def clean_after_analysis(self):
        QApplication.processEvents()
        if hasattr(self, "progress"):
            self.progress.close()
        self.list_of_splitted_rasters = []
        if not self.tmp_layers_flag:
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def generate_slope(self, input_raster, zfactor):
        if not self.tmp_layers_flag:
            tmp_raster_filepath = os.path.join(
                self.tmp_dir,
                f'''{os.path.splitext(
                    os.path.basename(input_raster))[0]}.tif''')
        else:
            tmp_raster_filepath = self.export_path
        QApplication.processEvents()
        processing.run(
            'qgis:slope',
            {'INPUT': input_raster, 'OUTPUT': tmp_raster_filepath,
             'Z_FACTOR': zfactor})
        QApplication.processEvents()
        self.list_of_splitted_rasters.append(tmp_raster_filepath)

    def gen_slope_process(self, input_files, zfactor, export_directory,
                          q_add_to_project):
        self.progress = create_progress_bar(
            0, txt='Trwa generowanie modelu nachylenia...')
        self.tmp_dir = mkdtemp(suffix=f'nmt_generate_slope')
        self.tmp_layers_flag = False
        if export_directory and export_directory not in (' ', ',') and \
                export_directory != ".":
            self.export_path = normalize_path(export_directory)
            self.tmp_layers_flag = True
        self.list_of_splitted_rasters = []
        self.last_progress_value = 0
        self.progress.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.progress.show()
        QApplication.processEvents()
        try:
            self.generate_slope(input_files, zfactor)
        except RuntimeError:
            self.invalid_data_error()
            return
        if q_add_to_project:
            add_rasters_to_project("NACHYLENIE", self.list_of_splitted_rasters)
        self.clean_after_analysis()
        self.dlg.close()
        QMessageBox.information(
            self.dlg, 'Analiza NMT',
            'Generowanie modelu nachylenia zakończone.', QMessageBox.Ok)
