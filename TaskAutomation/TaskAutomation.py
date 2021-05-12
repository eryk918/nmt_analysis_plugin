# -*- coding: utf-8 -*-
import os

from PyQt5.QtCore import Qt
from qgis.PyQt.QtWidgets import QApplication, QMessageBox

from .UI.TaskAutomation_UI import TaskAutomation_UI
from ..utils import project, i_iface, create_progress_bar, \
    change_progressbar_value

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
# from ..GenerateHillshade.UI.GenerateHillshade_UI import GenerateHillshade_UI
# from ..GenerateStatistics.UI.GenerateStatistics_UI import GenerateStatistics_UI
# from ..GeneratePoints.UI.GeneratePoints_UI import GeneratePoints_UI
# from ..GeneratePolygons.UI.GeneratePolygons_UI import GeneratePolygons_UI
# from ..GenerateSlope.UI.GenerateSlope_UI import GenerateSlope_UI
# from ..RasterCutter.UI.RasterCutter_UI import RasterCutter_UI
# from ..SetProjection.UI.SetProjection_UI import SetProjection_UI
# from ..GenerateAspect.UI.GenerateAspect_UI import GenerateAspect_UI
# from ..GenerateHillshade.GenerateHillshade import GenerateHillshade
# from ..GenerateStatistics.GenerateStatistics import GenerateStatistics
# from ..GeneratePoints.GeneratePoints import GeneratePoints
# from ..GeneratePolygons.GeneratePolygons import GeneratePolygons
# from ..GenerateSlope.GenerateSlope import GenerateSlope
# from ..RasterCutter.RasterCutter import RasterCutter
# from ..SetProjection.SetProjection import SetProjection
# from ..GenerateAspect.GenerateAspect import GenerateAspect


class TaskAutomation:
    def __init__(self, parent):
        self.main = parent
        self.iface = i_iface
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

    def run(self):
        self.dlg = TaskAutomation_UI(self)
        self.dlg.setup_dialog()
        self.dlg.run_dialog()

    def collect_dialogs(self):
        self.dlg.accept()
        mech_counter = 1
        self.mechanism_dict = {}
        self.defined_mechs = []
        for cbbx in self.dlg.cbbx_list:
            mech_name = f'self.mech_{mech_counter}_dialog'
            exec(
                f'{mech_name} = {self.dlg.mecha_dict[cbbx.currentText()]}(self)')
            exec(f'{mech_name}.setup_dialog()')
            exec(f'{mech_name}.rejected.connect(self.close_all)')
            self.defined_mechs.append(mech_name)
            self.mechanism_dict[mech_name] = None
            mech_counter += 1
        self.run_dialogs()

    def run_dialogs(self):
        self.force_end=False
        for dialog in self.defined_mechs:
            self.mech = dialog
            if self.defined_mechs.index(dialog) != self.defined_mechs[-1]:
                exec(f'{dialog}.pushButton_zapisz.setText("Dalej")')
            exec(f'{dialog}.run_dialog()')
            if self.force_end:
                return
        self.last_progress_value = 0
        self.info_log = {}
        self.progress = create_progress_bar(
            100, txt='Trwa przetwarzanie algorytmów...')
        self.progress.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.progress.show()
        self.run_mechanisms()

    def run_mechanisms(self):
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
                self.info_log[mech] = eval(f'{mech_var}.{mecha_parameters}')
                QApplication.processEvents()
                step = False
                if mech == list(self.mechanism_dict)[-1]:
                    step = True
                change_progressbar_value(
                    self.progress, self.last_progress_value,
                    (100/len(self.mechanism_dict.keys())), last_step=step)
        except (TypeError, ValueError, AttributeError):
            self.progress.close()
            return
        self.get_info()

    def close_all(self):
        self.force_end = True

    def get_info(self):
        if any(self.info_log.values()):
            end_str = '\n\n'
            for failed_mech in self.info_log.values():
                if failed_mech:
                    for warning in failed_mech:
                        end_str += f'• {warning};\n'
            QMessageBox.warning(
                self.dlg, 'Automatyzacja zadań',
                'Wystapiły następujące błędy podczas przetwarzania algorytmów:'
                f'{end_str}',
                QMessageBox.Ok)
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
