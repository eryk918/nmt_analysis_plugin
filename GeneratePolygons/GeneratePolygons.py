# -*- coding: utf-8 -*-
import os
import shutil

from qgis import processing
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QApplication, QMessageBox
from qgis.core import QgsProcessingFeatureSourceDefinition, QgsField
from qgis.core import QgsVectorLayer, QgsVectorFileWriter, QgsFeatureRequest

from ..GeneratePolygons.UI.GeneratePolygons_UI import GeneratePolygons_UI
from ..utils import project, create_progress_bar, \
    add_layer_into_map, iface, change_progressbar_value, standarize_path, \
    CreateTemporaryLayer, Qt


class GeneratePolygons:
    def __init__(self, parent):
        self.main = parent
        self.iface = iface
        self.project_path = os.path.dirname(
            os.path.abspath(project.fileName()))
        self.actual_crs = project.crs().postgisSrid()

    def run(self):
        self.dlg = GeneratePolygons_UI(self)
        self.dlg.setup_dialog()
        self.dlg.run_dialog()

    def raster_to_vector_point(self, src_raster):
        try:
            lyr = processing.run(
                "native:pixelstopoints",
                {'FIELD_NAME': 'parametr', 'INPUT_RASTER': src_raster,
                 'OUTPUT': 'TEMPORARY_OUTPUT', 'RASTER_BAND': 1})['OUTPUT']
            self.layers_list.append(lyr.id())
            return lyr
        except KeyError:
            return

    def multipart_to_singlepart(self, layer):
        try:
            lyr = processing.run(
                "native:multiparttosingleparts", {
                    'INPUT': layer, 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
            self.layers_list.append(lyr.id())
            return lyr
        except KeyError:
            pass

    def extract_layer_extent(self, src_raster):
        try:
            lyr = processing.run(
                "native:polygonfromlayerextent",
                {'INPUT': src_raster, 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
            self.layers_list.append(lyr.id())
            return lyr
        except KeyError:
            pass

    def layer_difference(self, base_lyr, diff_lyr):
        try:
            lyr = processing.run("native:difference", {
                'INPUT': base_lyr, 'OVERLAY': diff_lyr,
                'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
            self.layers_list.append(lyr.id())
            return lyr
        except KeyError:
            pass

    def clip_layers(self, base_lyr, clip_lyr):
        try:
            lyr = processing.run(
                "native:clip",
                {'INPUT': base_lyr, 'OVERLAY': clip_lyr,
                 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
            self.layers_list.append(lyr.id())
            return lyr
        except KeyError:
            pass

    def polygonize_raster(self, base_lyr):
        try:
            return processing.run("gdal:polygonize",
                                  {'INPUT': base_lyr, 'BAND': 1, 'FIELD': 'DN',
                                   'EIGHT_CONNECTEDNESS': False, 'EXTRA': '',
                                   'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
        except KeyError:
            pass

    def generate_features(self, base_layer, height, width, rotation, shape):
        try:
            lyr = processing.run(
                "native:rectanglesovalsdiamonds",
                {'INPUT': base_layer, 'SHAPE': shape, 'WIDTH': width,
                 'HEIGHT': height, 'ROTATION': rotation, 'SEGMENTS': 5,
                 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
            self.layers_list.append(lyr.id())
            return lyr
        except KeyError:
            pass

    def extract_by_location(self, base_lyr, overlay, pred=None,
                            selected=False):
        if not pred:
            pred = [6]
        if selected:
            project.addMapLayer(overlay, False)
            intersect = \
                QgsProcessingFeatureSourceDefinition(
                    overlay.id(), selectedFeaturesOnly=True,
                    featureLimit=-1,
                    geometryCheck=QgsFeatureRequest.GeometryAbortOnInvalid)
        else:
            intersect = overlay
        try:
            lyr = processing.run(
                "native:extractbylocation",
                {'INPUT': base_lyr, 'PREDICATE': pred, 'INTERSECT': intersect,
                 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
            self.layers_list.append(lyr.id())
            return lyr
        except KeyError:
            pass

    def aggregate_layer(self, base_lyr):
        try:
            lyr = processing.run(
                "native:aggregate",
                {'INPUT': base_lyr, 'GROUP_BY': 'NULL',
                 'AGGREGATES': [
                     {'aggregate': 'sum', 'delimiter': ',', 'input': '"DN"',
                      'length': 9, 'name': 'DN', 'precision': 0, 'type': 2}],
                 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
            self.layers_list.append(lyr.id())
            return lyr
        except KeyError:
            pass

    def repair_layer(self, base_lyr):
        try:
            lyr = processing.run(
                "native:fixgeometries",
                {'INPUT': base_lyr,
                 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
            self.layers_list.append(lyr.id())
            return lyr
        except KeyError:
            pass

    def create_buffer(self, layer, distance):
        try:
            lyr = processing.run("native:buffer", {
                'INPUT': layer, 'DISTANCE': distance, 'SEGMENTS': 5,
                'END_CAP_STYLE': 0, 'JOIN_STYLE': 0, 'MITER_LIMIT': 2,
                'DISSOLVE': False, 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
            self.layers_list.append(lyr.id())
            return lyr
        except KeyError:
            pass

    def get_height_difference(self, points, max_height):
        QApplication.processEvents()
        points.removeSelection()
        points.selectByExpression(
            '''"parametr" = maximum("parametr")''')
        highest = points.selectedFeatures()[0]
        points.removeSelection()
        QApplication.processEvents()
        points.removeSelection()
        points.selectByExpression(
            '''"parametr" = minimum("parametr")''')
        lowest = points.selectedFeatures()[0]
        points.removeSelection()
        if highest['parametr'] - lowest['parametr'] > max_height:
            self.height_poly = (highest['parametr'] + lowest['parametr']) / 2
            return False
        else:
            self.height_poly = (highest['parametr'] + lowest['parametr']) / 2
            return True

    def add_vector_to_project(self, layer, group_name):
        group_import = project.layerTreeRoot().findGroup(group_name)
        if not group_import:
            project.layerTreeRoot().addGroup(group_name)
        add_layer_into_map(layer, group_name)

    def invalid_data_error(self):
        self.clean_after_analysis()
        if self.silent:
            return 'Generowanie poligonów nie powiodło się',
        else:
            QMessageBox.critical(
                self.dlg, 'Analiza NMT',
                'Dane są niepoprawne!\n'
                'Sprawdź zgodność danych wejściowych i ich odwzorowań.\n'
                'Generowanie poligonów nie powiodło się!',
                QMessageBox.Ok)

    def clean_after_analysis(self):
        try:
            for lyrid in self.layers_list:
                project.removeMapLayer(lyrid)
            del self.feats_to_predict, self.extracted_values
        except:
            pass
        if hasattr(self, "progress"):
            self.progress.close()

    def generate_polys(self, input_files, mask_file, export_directory,
                       height, q_add_to_project, offset, amount, feat_height,
                       feat_width, feat_angle, feat_type, silent=False):
        self.silent = silent
        self.progress = \
            create_progress_bar(0, txt='Trwa generowanie poligonów...',
                                silent=silent)
        if not silent:
            self.last_progress_value = 0
            self.progress.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.progress.show()
            change_progressbar_value(self.progress, self.last_progress_value,
                                     0, self.silent)
        filename = input_files.split('\\')[-1].strip(
            input_files.split("\\")[-1].split('.')[-1])[:-1]
        qml_path = standarize_path(
            os.path.join(self.main.plugin_dir,
                         '..\\GeneratePolygons\\utils\\polygons.qml'))
        self.layers_list = []
        input_files = standarize_path(input_files)
        mask_file = standarize_path(mask_file)
        dem_extent = self.extract_layer_extent(input_files)
        QApplication.processEvents()
        mask_layer = QgsVectorLayer(mask_file, 'input_lyr', 'ogr')
        points_to_analysis = self.clip_layers(
            self.raster_to_vector_point(input_files),
            self.layer_difference(dem_extent, mask_file))
        QApplication.processEvents()
        points_to_analysis_single = self.multipart_to_singlepart(
            points_to_analysis)
        QApplication.processEvents()
        features_to_analysis = \
            self.generate_features(points_to_analysis_single, feat_height,
                                   feat_width, feat_angle, feat_type)
        QApplication.processEvents()
        polygonized_layer = self.polygonize_raster(input_files)
        QApplication.processEvents()
        extent = self.layer_difference(
            self.aggregate_layer(self.repair_layer(polygonized_layer)),
            mask_file)
        QApplication.processEvents()
        self.extracted_values = \
            self.extract_by_location(features_to_analysis, extent)
        tmp_lyr = CreateTemporaryLayer(
            f"polygon?crs=EPSG:{mask_layer.crs().postgisSrid()}",
            'Wygenerowane poligony', "memory")
        tmp_lyr.set_layer_fields(
            [QgsField("srednia_wysokosc", QVariant.Double, 'double', 20, 2)])
        QApplication.processEvents()
        self.feats_to_predict = list(self.extracted_values.getFeatures())
        counter = 0
        if not self.feats_to_predict:
            return self.invalid_data_error()
        try:
            while True:
                for feat in self.feats_to_predict:
                    if counter == amount:
                        break
                    feature = feat
                    self.extracted_values.select(feature.id())
                    QApplication.processEvents()
                    points_to_calc = self.extract_by_location(
                        points_to_analysis_single, self.extracted_values, [0],
                        True)
                    QApplication.processEvents()
                    if self.get_height_difference(points_to_calc, height):
                        if hasattr(self, 'height_poly'):
                            feature.setAttributes([self.height_poly])
                        tmp_lyr.dataProvider().addFeature(feature)
                        self.extracted_values.removeSelection()
                        counter += 1
                    else:
                        self.extracted_values.removeSelection()
                        continue
                    buffer = self.create_buffer(tmp_lyr, offset)
                    QApplication.processEvents()
                    self.extracted_values = self.extract_by_location(
                        self.extracted_values, buffer, [2])
                    QApplication.processEvents()
                    self.feats_to_predict = \
                        list(self.extracted_values.getFeatures())
                    QApplication.processEvents()
                    break
                QApplication.processEvents()
                if not self.feats_to_predict:
                    return self.invalid_data_error()
                if counter == amount:
                    break
        except RuntimeError:
            return self.invalid_data_error()
        if counter < amount:
            resp = QMessageBox.information(
                self.dlg, 'Analiza NMT',
                'Ilość wygenerowanych poligonów jest mniejsza niz oczekiwana.'
                '\nCzy chcesz zapisać warstwę wyjściową?',
                QMessageBox.Yes, QMessageBox.No)
            if resp == QMessageBox.No:
                self.clean_after_analysis()
                return
        tmp_lyr.loadNamedStyle(qml_path)
        tmp_lyr.triggerRepaint()
        if export_directory not in (".", ""):
            _writer = QgsVectorFileWriter.writeAsVectorFormat(
                tmp_lyr, export_directory, "utf-8", tmp_lyr.crs(),
                "ESRI Shapefile")
            shutil.copy(qml_path, export_directory.replace(".shp", ".qml"))
            QApplication.processEvents()
            _writer = None
            if q_add_to_project:
                self.add_vector_to_project(
                    QgsVectorLayer(
                        export_directory, f'{filename}_poligony', "ogr"),
                    "WYGENEROWANE_POLIGONY")
        if q_add_to_project and export_directory in (".", ""):
            self.add_vector_to_project(tmp_lyr, "WYGENEROWANE_POLIGONY")
            QApplication.processEvents()
        self.clean_after_analysis()
        self.dlg.close()
        if not silent:
            QMessageBox.information(
                self.dlg, 'Analiza NMT', 'Generowanie poligonów zakończone.',
                QMessageBox.Ok)
        else:
            return export_directory if export_directory not in (".", "") \
                else tmp_lyr.source()
