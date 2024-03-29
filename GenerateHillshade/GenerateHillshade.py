# -*- coding: utf-8 -*-
import os
import shutil
from tempfile import mkdtemp

from qgis import processing
from qgis.PyQt.QtWidgets import QMessageBox, QApplication

from ..GenerateHillshade.UI.GenerateHillshade_UI import GenerateHillshade_UI
from ..utils import project, create_progress_bar, iface, \
    standarize_path, add_rasters_to_project, Qt


class GenerateHillshade:
    def __init__(self, parent):
        self.main = parent
        self.iface = iface
        self.project_path = os.path.dirname(
            os.path.abspath(project.fileName()))
        self.actual_crs = project.crs().postgisSrid()

    def run(self):
        self.dlg = GenerateHillshade_UI(self)
        self.dlg.setup_dialog()
        self.dlg.run_dialog()

    def invalid_data_error(self):
        self.clean_after_analysis()
        if self.silent:
            return 'Generowanie modelu cieniowania nie powiodło się',
        else:
            QMessageBox.critical(
                self.dlg,
                'Analiza NMT',
                'Dane są niepoprawne!\n'
                'Generowanie modelu cieniowania nie powiodło się!',
                QMessageBox.Ok)

    def clean_after_analysis(self):
        QApplication.processEvents()
        if hasattr(self, "progress"):
            self.progress.close()
        self.list_of_created_rasters = []
        if not self.tmp_layers_flag:
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def generate_hillshade(self, input_raster, zfactor, azimuth, v_angle):
        if not self.tmp_layers_flag:
            tmp_raster_filepath = os.path.join(
                self.tmp_dir,
                f'''{os.path.splitext(
                    os.path.basename(input_raster))[0]}.tif''')
        else:
            tmp_raster_filepath = self.export_path
        processing.run(
            'qgis:hillshade',
            {'AZIMUTH': azimuth, 'INPUT': input_raster,
             'OUTPUT': tmp_raster_filepath, 'V_ANGLE': v_angle,
             'Z_FACTOR': zfactor})
        QApplication.processEvents()
        self.list_of_created_rasters.append(tmp_raster_filepath)

    def gen_hillshade_process(self, input_files, zfactor, azimuth, v_angle,
                              export_directory, q_add_to_project,
                              silent=False):
        self.silent = silent
        self.progress = create_progress_bar(
            0, txt='Trwa generowanie modelu cieniowania...', silent=silent)
        if not self.silent:
            self.progress.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.progress.show()
        QApplication.processEvents()
        self.tmp_dir = mkdtemp(suffix=f'nmt_generate_hillshade')
        qml_path = standarize_path(
            os.path.join(self.main.plugin_dir,
                         '..\\GenerateHillshade\\style.qml'))
        self.tmp_layers_flag = False
        if export_directory and export_directory not in (' ', ',') and \
                export_directory != ".":
            self.export_path = standarize_path(export_directory)
            self.tmp_layers_flag = True
        self.list_of_created_rasters = []
        self.last_progress_value = 0
        QApplication.processEvents()
        try:
            self.generate_hillshade(input_files, zfactor, azimuth, v_angle)
        except RuntimeError:
            return self.invalid_data_error()
        if q_add_to_project:
            add_rasters_to_project("CIENIOWANIE",
                                   self.list_of_created_rasters, qml_path)
        export_list = self.list_of_created_rasters
        self.clean_after_analysis()
        self.dlg.close()
        if not self.silent:
            QMessageBox.information(
                self.dlg, 'Analiza NMT',
                'Generowanie modelu cienowania zakończone.', QMessageBox.Ok)
        else:
            return export_list[0] if export_list else None
