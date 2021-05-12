# -*- coding: utf-8 -*-
import os
import shutil
from tempfile import mkdtemp

from PyQt5.QtCore import Qt
from osgeo import gdal
from qgis import processing
from qgis.PyQt.QtWidgets import QApplication, QMessageBox
from qgis.core import QgsVectorLayer, QgsCoordinateReferenceSystem, \
    QgsRasterLayer
from qgis.gui import QgsProjectionSelectionDialog
from qgis.utils import iface

from ..RasterCutter.UI.RasterCutter_UI import RasterCutter_UI
from ..utils import project, create_progress_bar, i_iface, \
    add_map_layer, normalize_path, change_progressbar_value


class RasterCutter:
    def __init__(self, parent):
        self.main = parent
        self.iface = i_iface
        self.project_path = os.path.dirname(
            os.path.abspath(project.fileName()))
        self.actual_crs = project.crs().postgisSrid()

    def run(self):
        self.dlg = RasterCutter_UI(self)
        self.dlg.setup_dialog()
        self.dlg.run_dialog()

    def split_raster_by_mask(self, input_raster, mask):
        gdal.UseExceptions()
        change_progressbar_value(self.progress, self.last_progress_value, 2, silent=self.silent)
        raster_counter = 1
        base_raster = QgsRasterLayer(input_raster, "base")
        prj = base_raster.crs().postgisSrid()
        self.progress.setWindowFlags(Qt.WindowStaysOnBottomHint)
        if prj == 0 or prj == '':
            crs = QgsCoordinateReferenceSystem()
            selection_dialog = QgsProjectionSelectionDialog(iface.mainWindow())
            selection_dialog.setCrs(crs)
            if selection_dialog.exec():
                prj = selection_dialog.crs().postgisSrid()
                self.actual_crs = prj
        self.progress.setWindowFlags(Qt.WindowStaysOnTopHint)
        mask_layer, tmp_mask_name, mask = \
            self.check_vector_crs_and_translate(mask, prj, self.tmp_dir)
        change_progressbar_value(self.progress, self.last_progress_value, 4, silent=self.silent)
        rand_field = mask_layer.fields().names()[0]
        self.number_of_features = [feature for feature in
                                   mask_layer.getFeatures()]
        for feat in self.number_of_features:
            tmp_raster_name = \
                f'''{os.path.splitext(
                    os.path.basename(input_raster))[0]}_{raster_counter}.tif'''
            if not self.tmp_layers_flag:
                tmp_raster_filepath = os.path.join(self.tmp_dir,
                                                   tmp_raster_name)
            else:
                tmp_raster_filepath = os.path.join(self.export_path,
                                                   tmp_raster_name)
            sql = f'''SELECT * FROM {tmp_mask_name} 
                                WHERE "{rand_field}" LIKE '{feat[0]}' '''
            ds = gdal.Warp(tmp_raster_filepath, input_raster,
                           cutlineDSName=mask,
                           srcSRS=f'''EPSG:{prj}''',
                           dstSRS=f'''EPSG:{self.actual_crs}''',
                           cutlineSQL=sql, dstNodata=0,
                           creationOptions=['COMPRESS=LZW'],
                           cropToCutline=True, multithread=True)
            ds = None
            self.list_of_splitted_rasters.append(tmp_raster_filepath)
            change_progressbar_value(self.progress, self.last_progress_value,
                                     90 / len(self.number_of_features), silent=self.silent)
            raster_counter += 1

    def add_rasters_to_project(self, group_name):
        group_import = project.layerTreeRoot().findGroup(group_name)
        if not group_import:
            project.layerTreeRoot().addGroup(group_name)
        for raster_path in self.list_of_splitted_rasters:
            rlayer = QgsRasterLayer(raster_path, os.path.basename(raster_path))
            add_map_layer(rlayer, group_name)

    def check_vector_crs_and_translate(self, mask, dest_prj, tmp_dir):
        mask_layer = QgsVectorLayer(mask, mask, "ogr")
        if mask_layer.crs() != dest_prj:
            tmp_mask_name = \
                f'''{os.path.basename(mask).split(".")[0]}_converted'''
            tmp_mask_filepath = os.path.join(tmp_dir, f'{tmp_mask_name}.shp')
            reprojected_mask = processing.run(
                'qgis:reprojectlayer',
                {'INPUT': mask, 'OUTPUT': tmp_mask_filepath,
                 'TARGET_CRS': f'EPSG:{dest_prj}'})
            try:
                mask_layer = QgsVectorLayer(
                    reprojected_mask['OUTPUT'],
                    reprojected_mask['OUTPUT'], "ogr")
            except KeyError:
                pass
        else:
            tmp_mask_name = f'''{os.path.basename(mask).strip(
                os.path.basename(mask).split(".")[-1])[:-1]}'''
            tmp_mask_filepath = mask
        return mask_layer, tmp_mask_name, tmp_mask_filepath

    def invalid_data_error(self):
        if hasattr(self, "progress"):
            self.progress.close()
        self.clean_after_analysis()
        if self.silent:
            return 'Przycinanie rastra nie powiodło się',
        else:
            QMessageBox.critical(
                self.dlg,
                'Analiza NMT',
                'Dane są niepoprawne!\n'
                'Sprawdź zgodność danych wejściowych i ich odwzorowań.\n'
                'Przycinanie rastra nie powiodło się!',
                QMessageBox.Ok)

    def clean_after_analysis(self):
        self.list_of_splitted_rasters = []
        if not self.tmp_layers_flag:
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def cutting_process(self, input_files, mask_file, export_directory,
                        q_add_to_project, silent=False):
        self.silent = silent
        self.progress = create_progress_bar(100,
                                            txt='Trwa przycinanie rastra...')
        if not self.silent:
            self.progress.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.progress.show()
        self.tmp_dir = mkdtemp(suffix=f'nmt_raster_cut')
        self.tmp_layers_flag = False
        if bool(export_directory) and \
                os.path.exists(normalize_path(export_directory)) and \
                export_directory not in (".", ""):
            self.export_path = normalize_path(export_directory)
            self.tmp_layers_flag = True
        self.list_of_splitted_rasters = []
        self.last_progress_value = 0
        change_progressbar_value(self.progress, self.last_progress_value, 0, silent=self.silent)
        try:
            self.split_raster_by_mask(input_files, mask_file)
        except RuntimeError:
            return self.invalid_data_error()
        if q_add_to_project:
            self.add_rasters_to_project("POCIĘTE RASTRY")
        self.clean_after_analysis()
        change_progressbar_value(self.progress, self.last_progress_value, 4,
                                 True, silent=self.silent)
        self.dlg.close()
        if not self.silent:
            QMessageBox.information(
                self.dlg, 'Analiza NMT',
                'Przycinanie rastra zakończone.',
                QMessageBox.Ok)
