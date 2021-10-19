# -*- coding: utf-8 -*-
import os
import shutil
from datetime import datetime
from tempfile import mkdtemp

from osgeo import gdal
from qgis import processing
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import QgsVectorLayer, QgsCoordinateReferenceSystem, \
    QgsRasterLayer
from qgis.gui import QgsProjectionSelectionDialog

from ..RasterCutter.UI.RasterCutter_UI import RasterCutter_UI
from ..utils import project, create_progress_bar, iface, \
    add_layer_into_map, standarize_path, change_progressbar_value, Qt


class RasterCutter:
    def __init__(self, parent):
        self.main = parent
        self.iface = iface
        self.project_path = os.path.dirname(
            os.path.abspath(project.fileName()))
        self.actual_crs = project.crs().postgisSrid()

    def run(self):
        self.dlg = RasterCutter_UI(self)
        self.dlg.setup_dialog()
        self.dlg.run_dialog()

    def split_raster_by_mask(self, input_raster, mask):
        gdal.UseExceptions()
        change_progressbar_value(self.progress, self.last_progress_value, 2,
                                 silent=self.silent)
        self.raster_counter = 1
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
        change_progressbar_value(self.progress, self.last_progress_value, 4,
                                 silent=self.silent)
        self.rand_field = mask_layer.fields().names()[0]
        self.number_of_features = [feature for feature in
                                   mask_layer.getFeatures()]
        for feat in self.number_of_features:
            self.cut_raster_into_tiles(
                input_raster, feat, tmp_mask_name, mask, prj)
            change_progressbar_value(self.progress, self.last_progress_value,
                                     90 / len(self.number_of_features),
                                     silent=self.silent)
            self.raster_counter += 1

    def cut_raster_into_tiles(self, input_raster, feat, mask_name, mask_file,
                              prj):
        tmp_raster_name = \
            f'''{os.path.splitext(
                os.path.basename(input_raster))[0]}_{self.raster_counter}.tif'''
        if not self.tmp_layers_flag:
            tmp_raster_filepath = os.path.join(self.tmp_dir,
                                               tmp_raster_name)
        else:
            tmp_raster_filepath = os.path.join(self.export_path,
                                               tmp_raster_name)
        sql = f'''SELECT * FROM "{mask_name}" WHERE "{self.rand_field}" = '{feat[0]}' '''
        ds = gdal.Warp(destNameOrDestDS=tmp_raster_filepath,
                       srcDSOrSrcDSTab=input_raster,
                       cutlineDSName=mask_file,
                       srcSRS=f'EPSG:{prj}',
                       dstSRS=f'EPSG:{self.actual_crs}',
                       cutlineSQL=sql, dstNodata=0,
                       creationOptions=['COMPRESS=LZW'],
                       cropToCutline=True, multithread=True)
        ds = None
        self.list_of_created_rasters.append(tmp_raster_filepath)

    def add_rasters_to_project(self, group_name):
        group_import = project.layerTreeRoot().findGroup(group_name)
        if not group_import:
            project.layerTreeRoot().addGroup(group_name)
        for raster_path in self.list_of_created_rasters:
            rlayer = QgsRasterLayer(raster_path, os.path.basename(raster_path))
            add_layer_into_map(rlayer, group_name)

    def check_vector_crs_and_translate(self, mask, dest_prj, tmp_dir):
        mask_layer = QgsVectorLayer(mask, mask, "ogr")
        time = datetime.now().strftime('%H_%M_%S_%f')[:-3]
        if mask_layer.crs() != dest_prj:
            tmp_mask_name = f'''mask_{time}'''
            tmp_mask_filepath = os.path.join(tmp_dir, f"{tmp_mask_name}.shp")
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
        self.list_of_created_rasters = []
        if not self.tmp_layers_flag:
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def cutting_process(self, input_files, mask_file, export_directory,
                        q_add_to_project, silent=False):
        self.silent = silent
        self.progress = create_progress_bar(100,
                                            txt='Trwa przycinanie rastra...',
                                            silent=silent)
        if not self.silent:
            self.progress.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.progress.show()
        self.tmp_dir = mkdtemp(suffix=f'nmt_raster_cut')
        self.tmp_layers_flag = False
        if bool(export_directory) and \
                os.path.exists(standarize_path(export_directory)) and \
                export_directory not in (".", ""):
            self.export_path = standarize_path(export_directory)
            self.tmp_layers_flag = True
        self.list_of_created_rasters = []
        self.last_progress_value = 0
        change_progressbar_value(self.progress, self.last_progress_value, 0,
                                 silent=self.silent)
        try:
            self.split_raster_by_mask(input_files, mask_file)
        except RuntimeError:
            return self.invalid_data_error()
        if q_add_to_project:
            self.add_rasters_to_project("POCIĘTE_RASTRY")
        export_list = self.list_of_created_rasters
        self.clean_after_analysis()
        change_progressbar_value(self.progress, self.last_progress_value, 4,
                                 True, silent=self.silent)
        self.dlg.close()
        if not self.silent:
            QMessageBox.information(
                self.dlg, 'Analiza NMT',
                'Przycinanie rastra zakończone.',
                QMessageBox.Ok)
        else:
            return export_list
