# -*- coding: utf-8 -*-
import os
import shutil
from tempfile import mkdtemp

from PyQt5.QtCore import Qt
from osgeo import gdal
from qgis import processing
from qgis.PyQt.QtWidgets import QApplication, QMessageBox
from qgis.core import QgsVectorLayer, QgsCoordinateReferenceSystem, \
    QgsRasterLayer, QgsVectorFileWriter
from qgis.gui import QgsProjectionSelectionDialog
from qgis.utils import iface

from ..GeneratePoints.UI.GeneratePoints_UI import GeneratePoints_UI
from ..GeneratePoints.utils.update_fields import update_fields_list
from ..utils import CreateTemporaryLayer, project, create_progress_bar, \
    add_map_layer, normalize_path, i_iface, change_progressbar_value


class GeneratePoints:
    def __init__(self, parent):
        self.main = parent
        self.iface = i_iface
        self.project_path = os.path.dirname(
            os.path.abspath(project.fileName()))
        self.actual_crs = project.crs().postgisSrid()

    def run(self):
        self.dlg = GeneratePoints_UI(self)
        self.dlg.setup_dialog()
        self.dlg.run_dialog()

    def get_min_max_from_layer(self, layer, how_many_max, how_many_min,
                               radius):
        najnizsze = []
        najwyzsze = []
        layer_max = self.clone_layer(layer)
        # TODO: naprawić klonowanie warstw
        for index in range(1, how_many_max + 1):
            QApplication.processEvents()
            layer_max.removeSelection()
            layer_max.selectByExpression(
                '''"parametr" = maximum("parametr")''')
            highest = layer_max.selectedFeatures()[0]
            layer_max.removeSelection()
            layer_max.select(highest.id())
            najwyzsze.append(highest)
            QApplication.processEvents()
            layer_max = self.create_buffer_and_make_difference(layer_max,
                                                               radius)
        for index in range(0, how_many_min):
            QApplication.processEvents()
            layer.removeSelection()
            layer.selectByExpression(
                '''"parametr" = minimum("parametr")''')
            lowest = layer.selectedFeatures()[0]
            layer.removeSelection()
            layer.select(lowest.id())
            najnizsze.append(lowest)
            QApplication.processEvents()
            layer = self.create_buffer_and_make_difference(layer, radius)
        del layer_max
        return [najwyzsze, najnizsze]

    def create_buffer_and_make_difference(self, layer, distance):
        clone_layer = processing.run("native:saveselectedfeatures",
                                     {'INPUT': layer,
                                      'OUTPUT': 'memory:'})['OUTPUT']
        buffer = processing.run("native:buffer",
                                {'DISSOLVE': False, 'DISTANCE': distance,
                                 'END_CAP_STYLE': 0,
                                 'INPUT': clone_layer,
                                 'JOIN_STYLE': 0, 'MITER_LIMIT': 2,
                                 'OUTPUT': 'TEMPORARY_OUTPUT', 'SEGMENTS': 5})
        layer.removeSelection()
        selected = processing.run("native:selectbylocation",
                                  {'INPUT': layer,
                                   'INTERSECT': buffer['OUTPUT'],
                                   'METHOD': 0, 'PREDICATE': [0]})
        layer.startEditing()
        layer.deleteFeatures([feat.id() for feat in layer.selectedFeatures()])
        layer.commitChanges()
        del selected, buffer, clone_layer
        return layer

    def clone_layer(self, layer):
        layer.selectAll()
        clone_layer = processing.run("native:saveselectedfeatures",
                                     {'INPUT': layer,
                                      'OUTPUT': 'memory:'})['OUTPUT']
        layer.removeSelection()
        return clone_layer

    def create_tmp_layer(self, layer_name):
        tmp = CreateTemporaryLayer(f"point?crs=EPSG:{self.actual_crs}",
                                   layer_name,
                                   "memory")
        tmp.set_fields(update_fields_list)
        return tmp

    def add_and_set_final_features(self, dest_layer, min_values, max_values):
        final_list = min_values + max_values
        self.update_values_dict = {}
        for column_id in range(32):
            if column_id == 11:
                self.update_values_dict[column_id] = 10000
            elif column_id == 12:
                self.update_values_dict[column_id] = "0010_819"
            elif column_id == 14:
                self.update_values_dict[column_id] = 1234.1234
            elif column_id == 15:
                self.update_values_dict[column_id] = "NMT"
            elif column_id == 16 or column_id == 21:
                self.update_values_dict[column_id] = False
            else:
                self.update_values_dict[column_id] = None
        dest_layer.startEditing()
        data_provider = dest_layer.dataProvider()
        for feat in final_list:
            self.update_values_dict[14] = feat.attributes()[0]
            feat.setAttributes(list(self.update_values_dict.values()))
            data_provider.addFeature(feat)
        dest_layer.commitChanges()

    def split_raster_by_mask(self, input_raster, mask):
        gdal.UseExceptions()
        change_progressbar_value(self.progress, self.last_progress_value, 2)
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
        change_progressbar_value(self.progress, self.last_progress_value, 4)
        rand_field = mask_layer.fields().names()[0]
        self.number_of_features = [feature for feature in
                                   mask_layer.getFeatures()]
        for feat in self.number_of_features:
            tmp_raster_name = \
                f'''{os.path.basename(input_raster)}_{raster_counter}.tif'''
            tmp_raster_filepath = os.path.join(self.tmp_dir, tmp_raster_name)
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
                                     22 / len(self.number_of_features))
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

    def raster_to_vector_point(self, src_raster):
        vectorized = processing.run(
            "native:pixelstopoints", {'FIELD_NAME': 'parametr',
                                      'INPUT_RASTER': src_raster,
                                      'OUTPUT': 'TEMPORARY_OUTPUT',
                                      'RASTER_BAND': 1})
        try:
            self.list_of_vectorized_layers.append(vectorized['OUTPUT'])
        except KeyError:
            pass
        del vectorized

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

    def add_vector_to_project(self, layer, group_name):
        group_import = project.layerTreeRoot().findGroup(group_name)
        if not group_import:
            project.layerTreeRoot().addGroup(group_name)
        add_map_layer(layer, group_name)

    def invalid_data_error(self):
        if hasattr(self, "progress"):
            self.progress.close()
        self.clean_after_analysis()
        QMessageBox.critical(
            self.dlg, 'Analiza NMT',
            'Dane są niepoprawne!\n'
            'Sprawdź zgodność danych wejściowych i ich odwzorowań.\n'
            'Generowanie punktów wysokościowych nie powiodło się!',
            QMessageBox.Ok)

    def clean_after_analysis(self):
        self.list_of_splitted_rasters = []
        self.list_of_vectorized_layers = []
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def analysis_process(
            self, input_files, mask_file, export_directory, an_min, an_max,
            q_add_to_project, radius):
        self.progress = \
            create_progress_bar(
                100, txt='Trwa generowanie punktów wysokościowych...')
        self.tmp_dir = mkdtemp(suffix=f'nmt_gen_point')
        self.list_of_splitted_rasters = []
        self.list_of_vectorized_layers = []
        self.last_progress_value = 0
        self.progress.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.progress.show()
        change_progressbar_value(self.progress, self.last_progress_value, 0)
        filename = input_files.split('\\')[-1].strip(
            input_files.split("\\")[-1].split('.')[-1])[:-1]
        qml_path = normalize_path(
            os.path.join(
                self.main.plugin_dir,
                'GeneratePoints\\utils\\punkty_wys.qml'))
        try:
            self.split_raster_by_mask(input_files, mask_file)
        except RuntimeError:
            self.invalid_data_error()
            return
        for raster in self.list_of_splitted_rasters:
            self.raster_to_vector_point(raster)
            change_progressbar_value(self.progress, self.last_progress_value,
                                     16 / len(self.list_of_splitted_rasters))
        tmp_lyr = self.create_tmp_layer(f'{filename}_pkt_wys')
        for vector in self.list_of_vectorized_layers:
            try:
                najwyzsze, najnizsze = self.get_min_max_from_layer(
                    vector, an_max, an_min, radius)
            except IndexError:
                self.invalid_data_error()
                return
            self.add_and_set_final_features(tmp_lyr, najnizsze, najwyzsze)
            change_progressbar_value(self.progress, self.last_progress_value,
                                     46 / len(self.list_of_vectorized_layers))
        tmp_lyr.loadNamedStyle(qml_path)
        tmp_lyr.triggerRepaint()
        if export_directory not in (".", ""):
            _writer = QgsVectorFileWriter.writeAsVectorFormat(tmp_lyr,
                                                              export_directory,
                                                              "utf-8",
                                                              tmp_lyr.crs(),
                                                              "ESRI Shapefile")
            _writer = None
            shutil.copy(qml_path, export_directory.replace(".shp", ".qml"))
            change_progressbar_value(self.progress, self.last_progress_value,
                                     5)
            if q_add_to_project:
                self.add_vector_to_project(
                    QgsVectorLayer(export_directory,
                                   f'{filename}_analiza', "ogr"),
                    "PUNKTY_WYSOKOSCIOWE")
        if q_add_to_project and export_directory in (".", ""):
            self.add_vector_to_project(tmp_lyr, "PUNKTY_WYSOKOSCIOWE")
        self.clean_after_analysis()
        change_progressbar_value(self.progress, self.last_progress_value, 5,
                                 True)
        self.dlg.close()
        QMessageBox.information(
            self.dlg, 'Analiza NMT',
            'Generowanie punktów wysokościowych zakończone.',
            QMessageBox.Ok)
