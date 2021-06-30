# -*- coding: utf-8 -*-
import os

from qgis.PyQt.QtWidgets import QApplication, QMessageBox

from .UI.TaskAutomation_UI import TaskAutomation_UI
from ..utils import project, iface, create_progress_bar, \
    change_progressbar_value, Qt

from ..GenerateHillshade.UI.GenerateHillshade_UI import GenerateHillshade_UI
from ..GenerateStatistics.UI.GenerateStatistics_UI import GenerateStatistics_UI
from ..GeneratePoints.UI.GeneratePoints_UI import GeneratePoints_UI
from ..GeneratePolygons.UI.GeneratePolygons_UI import GeneratePolygons_UI
from ..GenerateSlope.UI.GenerateSlope_UI import GenerateSlope_UI
from ..RasterCutter.UI.RasterCutter_UI import RasterCutter_UI
from ..SetProjection.UI.SetProjection_UI import SetProjection_UI
from ..GenerateAspect.UI.GenerateAspect_UI import GenerateAspect_UI
from ..GenerateHillshade.GenerateHillshade import GenerateHillshade
from ..GenerateStatistics.GenerateStatistics import GenerateStatistics
from ..GeneratePoints.GeneratePoints import GeneratePoints
from ..GeneratePolygons.GeneratePolygons import GeneratePolygons
from ..GenerateSlope.GenerateSlope import GenerateSlope
from ..RasterCutter.RasterCutter import RasterCutter
from ..SetProjection.SetProjection import SetProjection
from ..GenerateAspect.GenerateAspect import GenerateAspect


class TaskAutomation:
    def __init__(self, parent):
        self.main = parent
        self.iface = iface
        self.project_path = os.path.dirname(
            os.path.abspath(project.fileName()))
        self.actual_crs = project.crs().postgisSrid()
        self.plugin_dir = self.main.plugin_dir
        self.mecha_links = {
            "gen_hillshade_process": "GenerateHillshade",
            "gen_slope_process": "GenerateSlope",
            "gen_aspect_process": "GenerateAspect",
            "generate_polys": "GeneratePolygons",
            "generate_points": "GeneratePoints",
            "generate_statistics_process": "GenerateStatistics",
            "set_proj_process": "SetProjection",
            "cutting_process": "RasterCutter"
        }
        self.inv_mecha_links = {class_name: mech_name for mech_name, class_name
                                in self.mecha_links.items()}
        self.vectors_mechs = {
            'generate_polys': ['maska', 'vector'],
            "generate_points": ['maska', 'vector'],
            "cutting_process": ['maska', 'raster_list'],
            'set_proj_process': ['wejscie', 'all']
        }
        self.rasters_mechs = {
            "gen_hillshade_process": ["wejscie", 'raster'],
            "gen_slope_process": ["wejscie", 'raster'],
            "gen_aspect_process": ["wejscie", 'raster'],
            "generate_polys": ["wejscie", 'vector'],
            "generate_points": ["wejscie", 'vector'],
            "generate_statistics_process": ["wejscie", 'html'],
            "set_proj_process": ["wejscie", 'all'],
            "cutting_process": ["wejscie", 'raster_list']
        }
        self.data_type = {
            'raster': self.rasters_mechs,
            'vector': self.vectors_mechs,
            'all': 'any',
            'html': None,
            'raster_list': None
        }

    def run(self):
        self.dlg = TaskAutomation_UI(self)
        self.dlg.setup_dialog()
        self.dlg.run_dialog()

    def run_tasks_mechanism(self):
        self.configure_dialogs()
        if self.run_dialogs():
            return
        self.run_mechanisms()
        self.fetch_logs()

    def configure_dialogs(self):
        self.dlg.accept()
        mech_counter = 1
        self.mechanism_dict = {}
        self.defined_mechs_dialogs = []
        self.algs = {}
        for cbbx in self.dlg.cbbx_list:
            mech_name = f'self.mech_{mech_counter}_dialog'
            exec(f'{mech_name} = {self.dlg.mecha_dict[cbbx.currentText()]}(self, allow_silent=True)')
            exec(f'{mech_name}.setup_dialog()')
            exec(f'{mech_name}.rejected.connect(self.force_close_all)')
            self.algs[mech_name] = self.dlg.mecha_dict[cbbx.currentText()].rstrip('_UI')
            self.defined_mechs_dialogs.append(mech_name)
            self.mechanism_dict[mech_name] = None
            mech_counter += 1

    def run_dialogs(self):
        self.force_end = False
        for dialog in self.defined_mechs_dialogs:
            self.mech = dialog
            if dialog != self.defined_mechs_dialogs[-1]:
                exec(f'{dialog}.pushButton_zapisz.setText("Dalej")')
            if dialog != self.defined_mechs_dialogs[0]:
                for mech in self.rasters_mechs.keys():
                    if mech in self.mechanism_dict[
                        self.defined_mechs_dialogs[
                            self.defined_mechs_dialogs.index(dialog) - 1]]:
                        out_type = self.rasters_mechs[mech][-1]
                        if out_type and self.data_type[out_type]:
                            if out_type == 'all':
                                if any(ext in
                                       self.mechanism_dict[self.defined_mechs_dialogs[
                                           self.defined_mechs_dialogs.index(dialog) - 1]]
                                       for ext in ('.tif', '.asc', '.xyz')):
                                    out_type = 'raster'
                                else:
                                    out_type = 'vector'
                                mech = self.inv_mecha_links[self.algs[dialog]]
                            try:
                                exec(f'{dialog}.{self.data_type[out_type][mech][0]}.lineEdit().setPlaceholderText("Warstwa wyjściowa z poprzedniego algorytmu")')
                            except (KeyError, IndexError, ValueError, AttributeError):
                                pass
            exec(f'{dialog}.run_dialog()')
            if self.force_end:
                return True
        self.last_progress_value = 0
        self.info_log = {}
        self.progress = create_progress_bar(
            100, txt='Trwa przetwarzanie algorytmów...')
        self.progress.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.progress.show()

    def run_mechanisms(self):
        self.tmp_parameter = None
        try:
            for mech in self.mechanism_dict:
                mecha_parameters = self.mechanism_dict[mech]
                if not mecha_parameters:
                    self.progress.close()
                    return
                for mech_key in self.mecha_links.keys():
                    if mech_key in mecha_parameters:
                        desired_class = self.mecha_links[mech_key]
                        break
                mech_var = mech.rstrip('_dialog')
                QApplication.processEvents()
                exec(f'''{mech_var} = {desired_class}(self)''')
                exec(f'''{mech_var}.dlg = {mech}''')
                QApplication.processEvents()
                mecha_parameters = mecha_parameters.replace('\\', '\\\\')
                if self.tmp_parameter and "''" in mecha_parameters:
                    mecha_parameters = mecha_parameters.replace(
                        "''", f"'{self.tmp_parameter}'")
                    self.tmp_parameter = None
                self.info_log[mech] = eval(f'{mech_var}.{mecha_parameters}')
                QApplication.processEvents()
                if 'powiodło' not in self.info_log[mech]:
                    self.tmp_parameter = self.info_log[mech]
                    if os.path.exists(self.tmp_parameter):
                        self.tmp_parameter = self.tmp_parameter.replace(
                            '\\', '\\\\')
                    self.info_log[mech] = None
                step = False
                if mech == list(self.mechanism_dict)[-1]:
                    step = True
                change_progressbar_value(
                    self.progress, self.last_progress_value,
                    (100 / len(self.mechanism_dict.keys())), last_step=step)
        except (TypeError, ValueError, AttributeError):
            self.progress.close()
            return

    def force_close_all(self):
        self.force_end = True

    def fetch_logs(self):
        end_str = '\n'
        if any(self.info_log.values()):
            for failed_mech in self.info_log.values():
                if failed_mech and 'powiodło' in failed_mech:
                    for warning in failed_mech:
                        end_str += f'• {warning};\n'
        if end_str != '\n':
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowIcon(self.main.icon)
            msg.setText("Przetwarzanie algorytmów zakończyło się błędem.")
            msg.setWindowTitle("Automatyzacja zadań - Analiza NMT")
            msg.setDetailedText(
                'Wystapiły następujące błędy podczas przetwarzania algorytmów:'
                f'{end_str}')
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
        else:
            QMessageBox.information(
                self.dlg, 'Automatyzacja zadań', 'Przetwarzanie zakończone.',
                QMessageBox.Ok)

    def gen_hillshade_process(self, input_files, zfactor, azimuth, v_angle,
                              export_directory, q_add_to_project):
        self.mechanism_dict[
            self.mech] = f'''gen_hillshade_process('{input_files}', {zfactor}, {azimuth}, {v_angle}, '{export_directory}', {q_add_to_project}, True)'''

    def gen_slope_process(self, input_files, zfactor, export_directory,
                          q_add_to_project):
        self.mechanism_dict[
            self.mech] = f'''gen_slope_process('{input_files}', {zfactor}, '{export_directory}', {q_add_to_project}, True)'''

    def gen_aspect_process(self, input_files, zfactor, export_directory,
                           q_add_to_project):
        self.mechanism_dict[
            self.mech] = f'''gen_aspect_process('{input_files}', {zfactor}, '{export_directory}', {q_add_to_project}, True)'''

    def generate_polys(self, input_files, mask_file, export_directory, height,
                       q_add_to_project, offset, amount, feat_height,
                       feat_width, feat_angle, feat_type):
        self.mechanism_dict[
            self.mech] = f'''generate_polys('{input_files}', '{mask_file}', '{export_directory}', {height}, {q_add_to_project}, {offset}, {amount}, {feat_height}, {feat_width}, {feat_angle}, {feat_type}, True)'''

    def generate_points(self, input_files, mask_file, export_directory, an_min,
                        an_max, q_add_to_project, radius):
        self.mechanism_dict[
            self.mech] = f'''generate_points('{input_files}', '{mask_file}', '{export_directory}', {an_min}, {an_max}, {q_add_to_project}, {radius}, True)'''

    def generate_statistics_process(self, input_files, export_directory,
                                    q_add_to_project):
        self.mechanism_dict[
            self.mech] = f'''generate_statistics_process('{input_files}', '{export_directory}', {q_add_to_project}, True)'''

    def set_proj_process(self, input_files, dest_crs, export_directory,
                         q_add_to_project):
        self.mechanism_dict[
            self.mech] = f'''set_proj_process('{input_files}', '{dest_crs}', '{export_directory}', {q_add_to_project}, True)'''

    def cutting_process(self, input_files, mask_file, export_directory,
                        q_add_to_project):
        self.mechanism_dict[
            self.mech] = f'''cutting_process('{input_files}', '{mask_file}', '{export_directory}', {q_add_to_project}, True)'''
