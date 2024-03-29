# -*- coding: utf-8 -*-
import os
import shutil
from tempfile import mkdtemp

from qgis import processing
from qgis.PyQt.QtWidgets import QMessageBox, QApplication

from ..GenerateSlope.UI.GenerateSlope_UI import GenerateSlope_UI
from ..utils import project, create_progress_bar, iface, \
    standarize_path, add_rasters_to_project, Qt


class GenerateSlope:
    def __init__(self, parent):
        self.main = parent
        self.iface = iface
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
        if self.silent:
            return 'Generowanie modelu nachylenia nie powiodło się',
        else:
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
        self.list_of_created_rasters = []
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
        processing.run(
            'qgis:slope',
            {'INPUT': input_raster, 'OUTPUT': tmp_raster_filepath,
             'Z_FACTOR': zfactor})
        QApplication.processEvents()
        self.list_of_created_rasters.append(tmp_raster_filepath)

    def gen_slope_process(self, input_files, zfactor, export_directory,
                          q_add_to_project, silent=False):
        self.silent = silent
        self.progress = create_progress_bar(
            0, txt='Trwa generowanie modelu nachylenia...', silent=silent)
        if not self.silent:
            self.progress.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.progress.show()
        self.tmp_dir = mkdtemp(suffix=f'nmt_generate_slope')
        self.tmp_layers_flag = False
        if export_directory and export_directory not in (' ', ',') and \
                export_directory != ".":
            self.export_path = standarize_path(export_directory)
            self.tmp_layers_flag = True
        self.list_of_created_rasters = []
        self.last_progress_value = 0
        QApplication.processEvents()
        try:
            self.generate_slope(input_files, zfactor)
        except RuntimeError:
            return self.invalid_data_error()
        if q_add_to_project:
            add_rasters_to_project("NACHYLENIE", self.list_of_created_rasters)
        export_list = self.list_of_created_rasters
        self.clean_after_analysis()
        self.dlg.close()
        if not self.silent:
            QMessageBox.information(
                self.dlg, 'Analiza NMT',
                'Generowanie modelu nachylenia zakończone.', QMessageBox.Ok)
        else:
            return export_list[0] if export_list else None
