# -*- coding: utf-8 -*-
import os
import shutil
from tempfile import mkdtemp

from PyQt5.QtCore import Qt
from osgeo import gdal
from qgis import processing
from qgis.PyQt.QtWidgets import QApplication
from qgis.core import QgsVectorLayer, QgsCoordinateReferenceSystem, \
    QgsRasterLayer
from qgis.gui import QgsProjectionSelectionDialog
from qgis.utils import iface

from ..RasterCutter.UI.RasterCutter_UI import RasterCutter_UI
from ..utils import project, create_progress_bar, InfoBox, i_iface, \
    add_map_layer, normalize_path


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
        self.change_progressbar_value(2)
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
        self.change_progressbar_value(4)
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
            self.change_progressbar_value(90 / len(self.number_of_features))
            raster_counter += 1

    def change_progressbar_value(self, value, last_step=False):
        self.progress.show()
        QApplication.processEvents()
        self.last_progress_value += value
        if self.last_progress_value == 100 or last_step:
            self.progress.setValue(100)
            self.progress.close()
        else:
            self.progress.setValue(self.last_progress_value)

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
        InfoBox(
            self.dlg,
            'Dane są niepoprawne!\n'
            'Sprawdź zgodność danych wejściowych i ich odwzorowań.\n'
            'Przycinanie rastra nie powiodło się!',
            title='Analiza NMT'
        ).button_ok()

    def clean_after_analysis(self):
        self.list_of_splitted_rasters = []
        if not self.tmp_layers_flag:
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def cutting_process(self, input_files, mask_file, export_directory,
                        q_add_to_project):
        self.progress = create_progress_bar(100,
                                            txt='Trwa przycinanie rastra...')
        self.tmp_dir = mkdtemp(suffix=f'nmt_raster_cut')
        self.tmp_layers_flag = False
        if bool(export_directory) and \
                os.path.exists(normalize_path(export_directory)) and \
                export_directory not in (".", ""):
            self.export_path = normalize_path(export_directory)
            self.tmp_layers_flag = True
        print(export_directory)
        self.list_of_splitted_rasters = []
        self.last_progress_value = 0
        self.progress.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.progress.show()
        self.change_progressbar_value(0)
        try:
            self.split_raster_by_mask(input_files, mask_file)
        except RuntimeError:
            self.invalid_data_error()
            return
        if export_directory not in (".", ""):
            if q_add_to_project:
                self.add_rasters_to_project("POCIĘTE RASTRY")
        if q_add_to_project and export_directory in (".", ""):
            self.add_rasters_to_project("POCIĘTE RASTRY")
        self.clean_after_analysis()
        self.change_progressbar_value(4, True)
        self.dlg.close()
        InfoBox(self.dlg, 'Przycinanie rastra zakończone.').button_ok()
