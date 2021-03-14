# -*- coding: utf-8 -*-

import os
import re
import subprocess
import sys
from tempfile import mkstemp

from PyQt5.QtCore import Qt
from qgis.PyQt.QtCore import pyqtSignal, QObject
from qgis.PyQt.QtWidgets import QFontComboBox, \
    QComboBox, QApplication, QProgressDialog, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, \
    QgsFeature, QgsRasterLayer
from qgis.utils import iface

project = QgsProject.instance()
i_iface = iface


class CreateTemporaryLayer(QgsVectorLayer):
    parent_layer = None

    def __init__(self, *args, **kwargs):
        if 'parent_layer' in kwargs:
            self.parent_layer = kwargs['parent_layer']
            del kwargs['parent_layer']
        super(CreateTemporaryLayer, self).__init__(*args, **kwargs)

    def set_symbolization_from_layer(self, layer):
        file_handle, tmp_qml = mkstemp(suffix='.qml')
        os.close(file_handle)
        layer.saveNamedStyle(tmp_qml)
        self.loadNamedStyle(tmp_qml)
        os.remove(tmp_qml)

    def set_fields(self, fields):
        self.dataProvider().addAttributes(fields)
        self.updateFields()

    def set_fields_from_layer(self, layer):
        fields = layer.fields()
        self.set_fields(fields)

    def add_features(self, features):
        feats = []
        for feature in features:
            feat = QgsFeature(feature)
            feats.append(feat)
        if feats:
            self.dataProvider().addFeatures(feats)
        iface.mapCanvas().refresh()

    def add_to_group(self, group_name, main_group=None, pos=0):
        add_map_layer(self, group_name, main_group, position=pos)
        self.triggerRepaint()


def repair_comboboxes(dlg_instance):
    dir_list = [dlg_instance.__getattribute__(dir_elem) for dir_elem in
                dlg_instance.__dir__()]
    filter_dir_list = list(filter(
        lambda elem: isinstance(elem, QComboBox) or isinstance(elem,
                                                               QFontComboBox),
        dir_list))
    if not filter_dir_list:
        return
    for cbbx in filter_dir_list:
        cbbx.installEventFilter(dlg_instance)
        temp_value = cbbx.isEditable()
        cbbx.setEditable(True)
        cbbx.setStyleSheet(
            cbbx.styleSheet() + " QComboBox { combobox-popup: 0; }")
        cbbx.setMaxVisibleItems(10)
        cbbx.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        cbbx.setEditable(temp_value)


def get_project_config(parameter, key, default=''):
    value = project.readEntry(parameter, key, default)[0]
    return value


def set_project_config(parameter, key, value):
    if isinstance(project, QgsProject):
        return project.writeEntry(parameter, key, value)


def create_progress_bar(max_len, title='Proszę czekać',
                        txt='Trwa przetwarzanie danych.', start_val=0,
                        auto_close=True, cancel_btn=None):
    progress_bar = QProgressDialog()
    progress_bar.setFixedWidth(500)
    progress_bar.setWindowTitle(title)
    progress_bar.setLabelText(txt)
    progress_bar.setMaximum(max_len)
    progress_bar.setValue(start_val)
    progress_bar.setAutoClose(auto_close)
    progress_bar.setCancelButton(cancel_btn)
    progress_bar.setStyleSheet(
        'QProgressBar::chunk{background:qlineargradient(spread:reflect, x1:0, y1:0.494, x2:0, y2:1, stop:0.269231 rgba(55, 165, 126, 255), stop:1 rgba(38, 115, 85, 255));}*{text-align:center; color:#000;}')
    QApplication.processEvents()
    return progress_bar


def change_progressbar_value(progress, last_progress_value,
                             value, last_step=False):
    progress.show()
    QApplication.processEvents()
    last_progress_value += value
    if last_progress_value == 100 or last_step:
        progress.setValue(100)
        progress.close()
    else:
        progress.setValue(last_progress_value)


def add_map_layer(layer, group_name, main_group_name=None, position=0):
    root = project.layerTreeRoot()
    if main_group_name and root.findGroup(main_group_name):
        group = root.findGroup(main_group_name).findGroup(group_name)
    else:
        group = root.findGroup(group_name)
    if not group:
        project.addMapLayer(layer)
        return
    project.addMapLayer(layer, False)
    if group_name:
        group.insertLayer(position, layer)
        group.setExpanded(False)


def add_rasters_to_project(group_name, list_of_rasters, symbology=None):
    QApplication.processEvents()
    group_import = project.layerTreeRoot().findGroup(group_name)
    if not group_import:
        project.layerTreeRoot().addGroup(group_name)
    for raster_path in list_of_rasters:
        QApplication.processEvents()
        rlayer = QgsRasterLayer(raster_path, os.path.basename(raster_path))
        add_map_layer(rlayer, group_name)
        if symbology:
            rlayer.loadNamedStyle(symbology)
            rlayer.triggerRepaint()


def add_vectors_to_project(group_name, list_of_vectors):
    QApplication.processEvents()
    group_import = project.layerTreeRoot().findGroup(group_name)
    if not group_import:
        project.layerTreeRoot().addGroup(group_name)
    for vector_path in list_of_vectors:
        QApplication.processEvents()
        vlayer = QgsVectorLayer(
            vector_path, os.path.basename(vector_path), "ogr")
        add_map_layer(vlayer, group_name)


def open_other_files(filepath, send_by=None):
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        try:
            os.startfile(filepath)
        except WindowsError:
            ext = os.path.splitext(filepath)[-1]
            QMessageBox.critical(
                None, 'Analiza NMT',
                f'''Błąd przy otwieraniu pliku z rozszerzeniem *.{ext}!
Zainstaluj program obsługujący format *.{ext} i spróbuj ponownie.''',
                QMessageBox.Ok)
            return
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))


def normalize_path(path):
    return os.path.normpath(os.sep.join(re.split(r'\\|/', path)))


# class Importer(QObject):
#     finished = pyqtSignal(str)
#     progress = pyqtSignal(float)
#     debug_print = pyqtSignal(str)
#
#     def run_import(self, cmd, file):
#         QApplication.processEvents()
#         errors = False
#         self.error_messages_list = []
#         ret = runexternal_out_and_err(cmd)
#         QApplication.processEvents()
#         if ret[1]:
#             errors = True
#             if "ERROR 1:" in ret[1].strip():
#                 errors = False
#             elif ret[1].strip() == 'ERROR ret code = -9':
#                 self.error_messages_list.append(
#                     f"Import zakończony przez użytkownika")
#             elif 'Warning' in ret[1]:
#                 errors = False
#             else:
#                 self.error_messages_list.append(
#                     f"Wystąpiły błędy importu dla pliku {file} . Komunikaty procesu:\n{ret[1]}")
#
#         if not errors:
#             self.finished.emit(ret[0])
#         else:
#             self.finished.emit(ret[0])
#             raise Exception('\n\n\n'.join(self.error_messages_list))
#         self.kill()
#
#     def emitProgress(self, dfComplete, pszMessage, pProgressArg):
#         self.progress.emit(dfComplete * 100.0)
#         return True
#
#     def debugPrint(self, text):
#         self.debug_print.emit(str(text))
#
#     def kill(self):
#         self.killed = True
#
#
# def runexternal_out_and_err(cmd, tracking_func=None) -> Any:
#     if os.name == "posix":
#         p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE,
#                              stderr=subprocess.PIPE, preexec_fn=os.setsid)
#     else:
#         DETACHED_PROCESS = 0x00000008
#         p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE,
#                              stderr=subprocess.PIPE,
#                              creationflags=DETACHED_PROCESS)
#     if tracking_func:
#         tracking_func.process_id = p
#
#     if p.stdout is not None:
#         q_stdout = Queue()
#         t_stdout = Thread(target=read_in_thread, args=(p.stdout, q_stdout))
#         t_stdout.start()
#     else:
#         q_stdout = None
#         ret_stdout = ''
#
#     if p.stderr is not None:
#         q_stderr = Queue()
#         t_stderr = Thread(target=read_in_thread, args=(p.stderr, q_stderr))
#         t_stderr.start()
#     else:
#         q_stderr = None
#         ret_stderr = ''
#
#     if q_stdout is not None:
#         ret_stdout = q_stdout.get().decode('utf-8')
#     if q_stderr is not None:
#         ret_stderr = q_stderr.get().decode('utf-8')
#
#     waitcode = p.wait()
#     if waitcode != 0:
#         ret_stderr = ret_stderr + '\nERROR ret code = %d' % waitcode
#
#     return (ret_stdout, ret_stderr)
