import argparse
import sys
import os

import numpy as np
import pandas as pd
import copy
import netCDF4 as nc
import datetime as dt
import re
import math

import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib
import matplotlib.patheffects as pe
import matplotlib.patches as patches
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from mpl_toolkits.axes_grid1 import make_axes_locatable

from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QPalette, QColor, QIcon
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtWidgets import QTableWidgetItem, QVBoxLayout, QHBoxLayout, QHeaderView, QFileDialog, QMessageBox
from regression_model_ui import Ui_MainWindow

ver = 'alpha 1.6'

# Default class for proxies to be saved as
class Proxy:

    #   Class for different Proxies with the same format
    #   Data will always be dependant in this order (time, lat)

    def __init__(self, name):
        self.name = name        # Name of the proxy
        self.data = []          # Data with the axis as follows (time, lat)
        self.time = []          # Time in datetime
        self.time_days = []     # Time in days since 1900-01-01
        self.lat_min = None       # Latitude minimum; The latitude from which this proxy should be used
        self.lat_max = None       # Latitude maximum; The latitude to which this proxy should be used
        self.alt_min = None       # Altitude minimum; The altitude from which this proxy should be used
        self.alt_max = None       # Altitude maximum; The altitude to which this proxy should be used
        self.desc = ''          # Description of the merged Dataset
        self.method = 1         # Method on how to use this proxy in the model. 0: don't use this proxy; 1: use this proxy; 2: use this proxy harmonically; 3: use this proxy for year-of-the-month
        self.seas_comp = 2      # Number of seasonal components if used with the harmonic method

# Default class for ozone data to be saved as
class Dataset:

    #   Class for different Datasets with the same format
    #   Ozone (O3) will always be dependant in this order (time, lev, lat)
    #   Or (time, lev, lat, lon) if the data is gridded

    def __init__(self, name):
        self.name = name        # Name of the merged dataset
        self.o3 = None            # Ozone Data with the axis as follows (time, lev, lat, lon)
        self.o3_unit = None       # Unit of measurement of the ozone
        self.time = None          # Time in datetime
        self.time_days = None     # Time in days since 1900-01-01
        self.lat = None           # Latitude
        self.lon = None           # Longitude if gridded
        self.lev = None           # Level in Pressure or Height
        self.lev_unit = None      # Unit of measurement of the level (hPa/km)
        self.desc = None          # Description of the merged Dataset


class ComboMethod(QtWidgets.QComboBox):
    def __init__(self, parent):
        super().__init__(parent)
        self.addItems(['disabled', 'single', 'harmonics', '12 months'])


class ComboSeasonal(QtWidgets.QComboBox):
    def __init__(self, parent):
        super().__init__(parent)
        self.addItems(['annual (2 terms)', 'semi-annual (4 terms)', 'tri-annual (6 terms)', 'quarter-annual (8 terms)'])


# Empty "canvas" for plotting
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure()
        # self.axes =fig.add_subplot(111)
        super().__init__(fig)
        self.axes_list = []


class PreviewWindow(QtWidgets.QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        # super(PreviewWindow, self).__init__()
        uic.loadUi('preview_table.ui', self)

        self.activateWindow()
        self.raise_()

        self.fill_table(data)

        self.btn_exit.clicked.connect(self.close)

    def fill_table(self, data):
        self.preview_table.setRowCount(data.shape[0])
        self.preview_table.setColumnCount(data.shape[1] if data.shape[1] else 0)

        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                self.preview_table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))


# Popup window to set the variable names to load data
class VariableWindow(QtWidgets.QDialog):
    ini_signal = pyqtSignal(dict)
    def __init__(self, settings_ini, filename):
        super(VariableWindow, self).__init__()
        uic.loadUi('data_load.ui', self)

        self.ini = settings_ini
        self.data = nc.Dataset(filename[0], 'r')

        self.load_variable_keys()

        self.dim_layout = self.findChild(QtWidgets.QWidget, 'variable_stacked_widget').layout()
        self.o3_var_combo.currentTextChanged.connect(self.populate_dim_widget)
        self.variable_bttn.clicked.connect(self.show_options)

        # connect buttons
        self.bttn_ok.clicked.connect(self.save_settings)
        self.bttn_cancel.clicked.connect(self.close)

    def show_options(self):
        current_index = self.variable_widget.currentIndex()
        if current_index == 0:
            self.variable_widget.setCurrentIndex(1)
        else:
            self.variable_widget.setCurrentIndex(0)

    def clear_dim_widget(self):
        while self.dim_layout.count():
            item = self.dim_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def populate_dim_widget(self):
        self.clear_dim_widget()
        if self.o3_var_combo.currentIndex() == 0:
            self.clear_dim_widget()
            return

        dims = self.data.variables[self.o3_var_combo.currentText()].dimensions

        self.combo_boxes = []
        self.line_edits = []
        for k, i in enumerate(dims):
            try:
                dim_index = self.o3_keys.index(i)
            except:
                dim_index = 0
            frame = QtWidgets.QFrame()
            frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
            frame.setFrameShadow(QtWidgets.QFrame.Raised)
            frame_layout = QVBoxLayout(frame)

            # Add widget with variable input
            row_widget = QtWidgets.QWidget()
            row_layout = QHBoxLayout(row_widget)
            label = QtWidgets.QLabel(i + ' variable: ')
            row_layout.addWidget(label)
            spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            row_layout.addItem(spacer)
            combo = QtWidgets.QComboBox()
            combo.addItems(self.o3_keys)
            combo.currentIndexChanged.connect(self.update_OK)
            combo.setCurrentIndex(dim_index)
            self.combo_boxes.append(combo)
            row_layout.addWidget(combo)
            frame_layout.addWidget(row_widget)

            # Add widget with tag input
            row_widget = QtWidgets.QWidget()
            row_layout = QHBoxLayout(row_widget)
            label = QtWidgets.QLabel(i + ' tag: ')
            row_layout.addWidget(label)
            spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            row_layout.addItem(spacer)
            line = QtWidgets.QLineEdit()
            row_layout.addWidget(line)
            frame_layout.addWidget(row_widget)

            match_key = [key for key in self.ini if 'tag_name_' in key]
            for ii in match_key:
                if i in [s.strip() for s in self.ini[ii].split(',')]:
                    line.setText(ii.split('_')[-1])
                    if ii.split('_')[-1] == 'time':
                        row_widget = QtWidgets.QWidget()
                        row_layout = QHBoxLayout(row_widget)
                        label = QtWidgets.QLabel('Time format: ')
                        row_layout.addWidget(label)
                        spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
                        row_layout.addItem(spacer)
                        line_time = QtWidgets.QLineEdit()
                        line_time.setText('%Y/%m')
                        row_layout.addWidget(line_time)
                        frame_layout.addWidget(row_widget)
            line.textChanged.connect(self.tag_change)
            self.dim_layout.addWidget(frame)

    def load_variable_keys(self):
        self.o3_keys = list(self.data.variables.keys())
        self.o3_keys.insert(0, '-None-')
        self.o3_var_combo.addItems(self.o3_keys)

    def update_OK(self):
        self.bttn_ok.setEnabled(not any(combo.currentIndex() == 0 for combo in self.combo_boxes))

    def tag_change(self):
        line_text = self.sender().text()
        if line_text == 'time':
            row_widget = QtWidgets.QWidget()
            row_layout = QHBoxLayout(row_widget)
            label = QtWidgets.QLabel('Time format: ')
            row_layout.addWidget(label)
            spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            row_layout.addItem(spacer)
            line = QtWidgets.QLineEdit()
            line.setText('%Y/%m')
            row_layout.addWidget(line)
            self.sender().parent().parent().layout().addWidget(row_widget)
        else:
            if self.sender().parent().parent().layout().itemAt(2):
                self.sender().parent().parent().layout().removeWidget(self.sender().parent().parent().layout().itemAt(2).widget())

    def save_settings(self):
        # Saves all settings and closes the settings window

        # Change ini
        if self.o3_var_combo.currentIndex() != 0:
            self.ini['o3_var'] = self.o3_var_combo.currentText()
        else:
            self.ini['o3_var'] = None

        for i in range(self.dim_layout.count()):
            combo_text = self.dim_layout.itemAt(i).widget().layout().itemAt(0).widget().layout().itemAt(2).widget().currentText()
            line_text = self.dim_layout.itemAt(i).widget().layout().itemAt(1).widget().layout().itemAt(2).widget().text()

            if line_text == 'time':
                self.ini['time_var'] = combo_text
                self.ini['time_dim'] = i + 1
                self.ini['time_format'] = self.dim_layout.itemAt(i).widget().layout().itemAt(2).widget().layout().itemAt(2).widget().text()
            else:
                self.ini['additional_var_' + str(i + 1) + '_index'] = combo_text
                self.ini['additional_var_' + str(i + 1) + '_tag'] = line_text

        self.ini_signal.emit(self.ini)
        self.accept()

    def closeEvent(self, event):
        if self.data is not None:
            self.data.close()
        super().closeEvent(event)


class ProxyWindow(QtWidgets.QDialog):
    ini_signal = pyqtSignal(dict)
    def __init__(self, settings_ini, filename):
        super(ProxyWindow, self).__init__()
        uic.loadUi('proxy_load.ui', self)
        self.ini = settings_ini
        self.file = filename[0]

        # Distinguish between ascii file and netCDF file
        if self.file.endswith('.nc'):
            self.proxy_widget.setCurrentIndex(0)
            self.data = nc.Dataset(self.file, 'r')
            self.load_nc_file()
            self.dim_layout = self.findChild(QtWidgets.QWidget, 'variable_stacked_widget').layout()
            self.proxy_var_combo.currentTextChanged.connect(self.populate_dim_widget)
            self.variable_bttn.clicked.connect(self.show_options)
        else:
            self.proxy_widget.setCurrentIndex(1)
            self.btn_preview.clicked.connect(self.open_preview)
            self.is2d_check.toggled.connect(self.toggle_2d)
            self.bttn_ok.setEnabled(True)

        # Set Proxy Name
        self.proxy_name.setText(self.file.split('/')[-1].split('.')[0])

        # connect buttons
        self.bttn_ok.clicked.connect(self.save_settings)
        self.bttn_cancel.clicked.connect(self.close)

        if isinstance(self.ini.get('additional_proxy_path', None), (list, np.ndarray)):
            if not self.ini.get('additional_proxy_path', None).all():
                self.create_add_proxy_list()
        else:
            if not self.ini.get('additional_proxy_path', None):
                self.create_add_proxy_list()

    def show_options(self):
        current_index = self.variable_widget.currentIndex()
        if current_index == 0:
            self.variable_widget.setCurrentIndex(1)
        else:
            self.variable_widget.setCurrentIndex(0)

    def create_add_proxy_list(self):
        self.ini['additional_proxy_name'] = np.array([], dtype='object')
        self.ini['additional_proxy_path'] = np.array([], dtype='object')
        self.ini['additional_proxy_time_col'] = np.array([], dtype='object')
        self.ini['additional_proxy_data_col'] = np.array([], dtype=int)
        self.ini['additional_proxy_method'] = np.array([], dtype=int)
        self.ini['additional_proxy_seas_comp'] = np.array([], dtype='object')
        self.ini['additional_proxy_time_format'] = np.array([], dtype='object')
        self.ini['additional_proxy_header_size'] = np.array([], dtype=int)
        self.ini['additional_proxy_tag'] = np.array([], dtype='object')
        self.ini['additional_proxy_tag_array'] = np.array([], dtype='object')

    def toggle_2d(self):
        if self.is2d_check.isChecked() == True:
            self.tag_widget_1.setEnabled(True)
            self.tag_widget_2.setEnabled(True)
        else:
            self.tag_widget_1.setEnabled(False)
            self.tag_widget_2.setEnabled(False)

    def clear_dim_widget(self):
        while self.dim_layout.count():
            item = self.dim_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def populate_dim_widget(self):
        self.clear_dim_widget()
        if self.proxy_var_combo.currentIndex() == 0:
            self.clear_dim_widget()
            return

        dims = self.data.variables[self.proxy_var_combo.currentText()].dimensions

        self.combo_boxes = []
        self.line_edits = []
        for k, i in enumerate(dims):
            try:
                dim_index = self.keys.index(i)
            except:
                dim_index = 0
            frame = QtWidgets.QFrame()
            frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
            frame.setFrameShadow(QtWidgets.QFrame.Raised)
            frame_layout = QVBoxLayout(frame)

            # Add widget with variable input
            row_widget = QtWidgets.QWidget()
            row_layout = QHBoxLayout(row_widget)
            label = QtWidgets.QLabel(i + ' variable: ')
            row_layout.addWidget(label)
            spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            row_layout.addItem(spacer)
            combo = QtWidgets.QComboBox()
            combo.addItems(self.keys)
            combo.currentIndexChanged.connect(self.update_OK)
            combo.setCurrentIndex(dim_index)
            self.combo_boxes.append(combo)
            row_layout.addWidget(combo)
            frame_layout.addWidget(row_widget)

            # Add widget with tag input
            row_widget = QtWidgets.QWidget()
            row_layout = QHBoxLayout(row_widget)
            label = QtWidgets.QLabel(i + ' tag: ')
            row_layout.addWidget(label)
            spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            row_layout.addItem(spacer)
            line = QtWidgets.QLineEdit()
            row_layout.addWidget(line)
            frame_layout.addWidget(row_widget)

            match_key = [key for key in self.ini if 'tag_name_' in key]
            for ii in match_key:
                if i in [s.strip() for s in self.ini[ii].split(',')]:
                    line.setText(ii.split('_')[-1])
                    if ii.split('_')[-1] == 'time':
                        row_widget = QtWidgets.QWidget()
                        row_layout = QHBoxLayout(row_widget)
                        label = QtWidgets.QLabel('Time format: ')
                        row_layout.addWidget(label)
                        spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
                        row_layout.addItem(spacer)
                        line_time = QtWidgets.QLineEdit()
                        line_time.setText('%Y/%m')
                        row_layout.addWidget(line_time)
                        frame_layout.addWidget(row_widget)
            line.textChanged.connect(self.tag_change)
            self.dim_layout.addWidget(frame)

    def load_nc_file(self):
        self.keys = list(self.data.variables.keys())
        self.keys.insert(0, '-None-')
        self.proxy_var_combo.addItems(self.keys)

    def open_preview(self):
        try:
            proxy_raw = pd.read_csv(self.file, sep='\s+', header=None, skiprows=int(self.header_rows.text()))
            proxy_raw.dropna(axis=1, how='all', inplace=True)
        except:
            print('Could not load the proxy data. Please try changing the header rows.')
            return

        self.preview_window = PreviewWindow(np.array(proxy_raw))
        self.preview_window.show()

    def update_OK(self):
        self.bttn_ok.setEnabled(not any(combo.currentIndex() == 0 for combo in self.combo_boxes))

    def tag_change(self):
        line_text = self.sender().text()
        if line_text == 'time':
            row_widget = QtWidgets.QWidget()
            row_layout = QHBoxLayout(row_widget)
            label = QtWidgets.QLabel('Time format: ')
            row_layout.addWidget(label)
            spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            row_layout.addItem(spacer)
            line = QtWidgets.QLineEdit()
            line.setText('%Y/%m')
            row_layout.addWidget(line)
            self.sender().parent().parent().layout().addWidget(row_widget)
        else:
            if self.sender().parent().parent().layout().itemAt(2):
                self.sender().parent().parent().layout().removeWidget(self.sender().parent().parent().layout().itemAt(2).widget())

    def save_settings(self):
        # Saves all settings and closes the settings window
        # Save depending on current open page
        self.ini['additional_proxy_path'] = np.append(self.ini['additional_proxy_path'], self.file)
        self.ini['additional_proxy_name'] = np.append(self.ini['additional_proxy_name'], self.proxy_name.text())
        if self.proxy_widget.currentIndex() == 0:
            for widget in self.variable_stacked_widget.children():
                if isinstance(widget, QtWidgets.QFrame):
                    if widget.layout().itemAt(1).widget().layout().itemAt(2).widget().text() == 'time':
                        self.ini['additional_proxy_time_col'] = np.append(self.ini['additional_proxy_time_col'], widget.layout().itemAt(0).widget().layout().itemAt(2).widget().currentText())
                        self.ini['additional_proxy_time_format'] = np.append(self.ini['additional_proxy_time_format'], widget.layout().itemAt(2).widget().layout().itemAt(2).widget().text())
                    else:
                        self.ini['additional_proxy_tag_array'] = np.append(self.ini['additional_proxy_tag_array'], widget.layout().itemAt(0).widget().layout().itemAt(2).widget().currentText())
                        self.ini['additional_proxy_tag'] = np.append(self.ini['additional_proxy_tag'], widget.layout().itemAt(1).widget().layout().itemAt(2).widget().text())
            self.ini['additional_proxy_data_col'] = np.append(self.ini['additional_proxy_data_col'], self.proxy_var_combo.currentText())
            self.ini['additional_proxy_method'] = np.append(self.ini['additional_proxy_method'], self.ini.get('default_proxy_method', 1))
            self.ini['additional_proxy_seas_comp'] = np.append(self.ini['additional_proxy_seas_comp'], self.ini.get('intercept_method', 2))
            self.ini['additional_proxy_header_size'] = np.append(self.ini['additional_proxy_header_size'], 0)
        else:
            self.ini['additional_proxy_time_col'] = np.append(self.ini['additional_proxy_time_col'], self.proxy_time.text())
            if self.is2d_check.isChecked():
                self.ini['additional_proxy_tag_array'] = np.append(self.ini['additional_proxy_tag_array'], self.tag_values.text())
                self.ini['additional_proxy_tag'] = np.append(self.ini['additional_proxy_tag'], self.tag.text())
            else:
                self.ini['additional_proxy_tag_array'] = np.append(self.ini['additional_proxy_tag_array'], False)
                self.ini['additional_proxy_tag'] = np.append(self.ini['additional_proxy_tag'], False)
            self.ini['additional_proxy_data_col'] = np.append(self.ini['additional_proxy_data_col'], self.proxy_data.text())
            self.ini['additional_proxy_method'] = np.append(self.ini['additional_proxy_method'], self.ini.get('default_proxy_method', 1))
            self.ini['additional_proxy_seas_comp'] = np.append(self.ini['additional_proxy_seas_comp'], self.ini.get('intercept_method', 2))
            self.ini['additional_proxy_header_size'] = np.append(self.ini['additional_proxy_header_size'], self.header_rows.text())
            self.ini['additional_proxy_time_format'] = np.append(self.ini['additional_proxy_time_format'], '%Y%m')

        self.ini_signal.emit(self.ini)
        self.accept()

    def closeEvent(self, event):
        if self.data is not None:
            self.data.close()
        super().closeEvent(event)



# The UI and its functions
class AppWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.ui'), self)
        self.setWindowTitle("IUP Regression Model")
        self.setWindowIcon(QIcon('iupLogo.png'))

        # Loading default data and proxies
        self.ini = load_config_ini(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config folder/config.ini'))
        self.list_of_data = []
        if 'data_path' in self.ini:
            try:
                data = load_netCDF(self.ini['data_path'], self.ini)
            except:
                print('Error in loading the data file.')
        self.list_of_data.append(data)
        self.data_list.addItem(data.name)
        if self.data_list.count() > 0:
            self.data_list.setCurrentRow(0)

        self.combo_pairs = {}
        self.populate_dim_limits()

        self.load_presets()

        self.proxies = load_default_proxies(self.ini)
        self.proxies = load_additional_proxies(self.proxies, self.ini)
        self.infl_method_list = ['ind', 'pwl']

        # Fill lists with proxies and data
        self.update_trend_table()
        self.update_proxy_table()

        # Create important variables
        self.X = None
        self.beta = None
        self.betaa = None
        self.time = None

        self.define_palettes()

        # main UI functions
        self.infl_check.toggled.connect(self.inflection_enable)
        self.start_date.textChanged.connect(self.format_check)
        self.end_date.textChanged.connect(self.format_check)
        self.inflection_point.textChanged.connect(self.format_check)
        self.inflection_method.currentIndexChanged.connect(self.inflection_method_change)
        self.all_proxy_method.currentIndexChanged.connect(self.all_proxy_method_change)
        self.mean_line.textChanged.connect(self.text_check)
        self.anomaly_check.toggled.connect(self.anomaly_enable)
        self.radio_rel.toggled.connect(self.anomaly_method_toggle)
        self.radio_abs.toggled.connect(self.anomaly_method_toggle)
        self.preset_combo.currentIndexChanged.connect(self.change_preset)
        self.data_list.currentItemChanged.connect(self.data_change)

        # Diagnostic UI functions
        self.dia_proxy_combo.currentIndexChanged.connect(self.proxy_diagnostic)
        self.dim_data_layout = self.data_dim_widget.layout()
        self.dim_data_boxes = []
        self.dia_data_combo.currentIndexChanged.connect(self.populate_data_dim_widget)
        self.add_data_dia()
        self.dim_X_layout = self.X_dim_widget.layout()
        self.dim_X_boxes = []

        # Start trend analysis
        self.compute_button.clicked.connect(self.compute_trends)

        # Plotting Model
        self.dim_layout = self.dim_widget.layout()
        self.dim_boxes = []
        self.plot_button.clicked.connect(self.plot_model_figure)
        self.layout = QVBoxLayout(self.figure_widget)
        self.canvas = MplCanvas(self.figure_widget)
        self.layout.addWidget(self.canvas)

        # Plotting Contour
        self.dim_con_layout = self.dim_con_widget.layout()
        self.dim_con_boxes = []
        self.plot_button_con.clicked.connect(self.plot_contour_figure)
        self.con_layout = QVBoxLayout(self.contour_widget)
        self.con_canvas = MplCanvas(self.contour_widget)
        self.con_layout.addWidget(self.con_canvas)

        # Menu button connection
        self.menu_help.triggered.connect(self.print_ini)
        self.menu_load_data.triggered.connect(self.open_data_dialog)
        self.menu_load_proxy.triggered.connect(self.open_proxy_dialog)
        self.menu_save.triggered.connect(self.save_file)

        self.frozen_list.horizontalHeader().sectionResized.connect(self.sync_frozen_to_main)

        # Load ini settings and input the data into the UI
        self.load_ini_settings()
        QTimer.singleShot(0, self.sync_tables)

    def load_ini_settings(self):

        if 'inflection_point' in self.ini:
            self.inflection_point.setText(dt.datetime.strftime(dt.datetime.strptime(self.ini['inflection_point'], '%Y-%m').date(), '%Y-%m'))
        else:
            self.inflection_point.setText('YYYY-MM')

        if 'inflection_point' in self.ini and 'inflection_method' in self.ini:
            if self.ini['inflection_method'] == 'ind':
                self.inflection_method.setCurrentIndex(0)
            elif self.ini['inflection_method'] == 'pwl':
                self.inflection_method.setCurrentIndex(1)
            self.infl_check.setChecked(True)

        if 'start_date' in self.ini:
            self.start_date.setText(dt.datetime.strftime(dt.datetime.strptime(self.ini['start_date'], '%Y-%m').date(), '%Y-%m'))
        else:
            self.start_date.setText('YYYY-MM')

        if 'end_date' in self.ini:
            self.end_date.setText(dt.datetime.strftime(dt.datetime.strptime(self.ini['end_date'], '%Y-%m').date(), '%Y-%m'))
        else:
            self.end_date.setText('YYYY-MM')

        self.frozen_list.cellWidget(0, 1).setCurrentIndex(int(self.ini.get('trend_method', self.ini.get('default_method', 1))))
        self.frozen_list.cellWidget(1, 1).setCurrentIndex(int(self.ini.get('intercept_method', self.ini.get('default_method', 1))))

        self.mean_line.setText(self.ini.get('averaging_window', ''))

        if self.ini.get('anomaly', 'False') == 'True':
            self.anomaly_check.setChecked(True)
        else:
            self.anomaly_check.setChecked(False)

        for k, dim in enumerate(self.list_of_data[self.data_list.currentRow()].dim_array):
            if dim == 'time':
                continue
            else:
                min_combo, max_combo = self.combo_pairs[dim]
                limits = self.ini.get('additional_var_' + str(k + 1) + '_limit', None)
                if not limits:
                    continue
                elif ',' in limits:
                    min, max = list(map(int, self.ini.get('additional_var_' + str(k + 1) + '_limit', None).split(",")))
                    min_combo.setCurrentIndex(min)
                    max_combo.setCurrentIndex(max)
                else:
                    limits = int(self.ini.get('additional_var_' + str(k + 1) + '_limit', None))
                    min_combo.setCurrentIndex(limits)
                    max_combo.setCurrentIndex(limits)

    def save_file(self):
        # Stop the function if nothing was computed yet
        if self.X is None:
            QMessageBox.warning(self, "Warning", "No data to save yet. Please compute the data first.")
            return

        # Open a file dialog to select the save location
        save_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "NetCDF Files (*.nc)")

        data = self.current_data
        # If a path was selected, save the file
        if save_path:
            lat = data.lat
            alt = data.lev
            lon = data.lon
            dims = data.dim_array

            with nc.Dataset(save_path + '.nc', 'w') as f:
                var_list = []
                for k, i in enumerate(dims[1:]):
                    f.createDimension(i, data.o3.shape[k+1])
                    var_list.append(f.createVariable(i, 'f8', (i,)))
                    var_list[k][:] = getattr(data, i)
                    # var_list[k].units = 'degrees_north'
                    # lat_var.long_name = 'latitude'

                max_length = max(len(s) for s in self.proxy_string)
                f.createDimension('n_coefficients', len(self.proxy_string))
                f.createDimension('string_length', max_length)
                f.createDimension('time', len(self.time))
                f.createDimension('infl', 2)

                ind_var = f.createVariable('independent_variable_names', 'str', ('n_coefficients',))
                ind_var[:] = np.array(self.proxy_string)

                time_var = f.createVariable('date', 'S10', 'time')
                time_var.unit = 'YYYYMMDD'
                frac_var = f.createVariable('fractional_year', 'f4', ('time',), compression="zlib")

                dim_tuple = tuple(dim_name for dim_name in dims)
                X_var = f.createVariable('independent_variable_matrix', 'f4', dim_tuple + ('n_coefficients',), compression="zlib")
                X_var[:] = self.X
                beta_var = f.createVariable('beta', 'f4', dim_tuple[1:] + ('n_coefficients',), compression="zlib")
                beta_var[:] = self.betaa
                # covb_var = f.createVariable('beta_uncertainty', 'f4', dim_tuple[1:] + ('n_coefficients',), compression="zlib")
                # print(self.convbeta)
                # covb_var[:] = self.convbeta

                if len(self.trends.shape) == len(dim_tuple):
                    trend_var = f.createVariable('trend', 'f4', dim_tuple[1:] + ('infl',))
                    sig_var = f.createVariable('trend_uncertainty', 'f4', dim_tuple[1:] + ('infl',))
                else:
                    trend_var = f.createVariable('trend', 'f4', dim_tuple[1:])
                    sig_var = f.createVariable('trend_uncertainty', 'f4', dim_tuple[1:])
                trend_var[:] = self.trends
                sig_var[:] = self.signi

                X_var.long_name = 'Independent Variable matrix'
                beta_var.long_name = 'Fit Parameters'

                frac_year = convert_datetime_to_fractional(self.time)

                time_int = np.array([str_time.strftime('%Y-%m-%d') for str_time in self.time])
                time_var[:] = time_int
                frac_var[:] = frac_year

                f.program = 'IUP_regression_model'
                f.version = ver
                f.contact = '''Name: Brian Auffarth\rAffiliation: University of Bremen\rE-mail: brian@iup.physik.uni-bremen.de'''
                f.date_of_creation = dt.datetime.today().strftime('%Y-%m-%d')
                f.configuration_settings = "\n".join([f"{key} = {value}" for key, value in self.ini.items()])

    def add_data_dia(self):
        self.dia_data_combo.clear()
        for i in self.list_of_data:
            self.dia_data_combo.addItem(i.name)

    def populate_data_dim_widget(self):
        self.clear_dim_widgets(self.dim_data_layout)
        self.dim_data_boxes.clear()

        for dim_index in range(1, len(self.list_of_data[self.dia_data_combo.currentIndex()].o3.shape)):
            col_layout = QVBoxLayout()
            label = QtWidgets.QLabel(self.list_of_data[self.dia_data_combo.currentIndex()].dim_array[dim_index])
            col_layout.addWidget(label)

            combo = QtWidgets.QComboBox()
            values = getattr(self.list_of_data[self.dia_data_combo.currentIndex()], self.list_of_data[self.dia_data_combo.currentIndex()].dim_array[dim_index])
            combo.addItems([str(value) for value in values])
            col_layout.addWidget(combo)
            combo.currentIndexChanged.connect(self.data_diagnostic)

            self.dim_data_boxes.append(combo)

            self.dim_data_layout.addLayout(col_layout)
        self.data_diagnostic()
        # data = self.list_of_data[self.data_list.currentRow()]

    def proxy_diagnostic(self, index):
        start_date = str(np.array(self.proxies[index].time)[0])
        end_date = str(np.array(self.proxies[index].time)[-1])
        self.dia_proxy_start.setText(start_date)
        self.dia_proxy_end.setText(end_date)
        dim_str = ' '.join(map(str, self.proxies[index].data.shape))
        self.dia_proxy.setText(dim_str)

        # Fill Table
        if len(self.proxies[index].data.shape) >= 2:
            sec_dim = self.proxies[index].data.shape[1]
            self.dia_proxy_table.setColumnCount(sec_dim)
            self.dia_proxy_table.setHorizontalHeaderLabels(getattr(self.proxies[index], self.proxies[index].tag).astype(str))
        else:
            sec_dim = 1
            self.dia_proxy_table.setColumnCount(sec_dim)
        self.dia_proxy_table.setRowCount(self.proxies[index].data.shape[0])

        self.dia_proxy_table.setVerticalHeaderLabels(self.proxies[index].time.astype(str))


        for k, i in enumerate(self.proxies[index].data):
            if sec_dim == 1:
                self.dia_proxy_table.setItem(k, 0, QTableWidgetItem(str(self.proxies[index].data[k])))
            else:
                for kk in range(sec_dim):
                    self.dia_proxy_table.setItem(k, kk, QTableWidgetItem(str(self.proxies[index].data[k, kk])))

    def update_trend_table(self):
        # Update of the frozen table
        self.frozen_list.setRowCount(2)
        # Add method combo boxes for trend and intercept
        self.frozen_list.setItem(0, 0, QTableWidgetItem('Trend'))
        methodBox = ComboMethod(self)
        self.frozen_list.setCellWidget(0, 1, methodBox)
        methodBox.currentIndexChanged.connect(lambda index, methodBox=methodBox, row=0: self.method_update(methodBox, row))
        methodBox.setCurrentIndex(int(self.ini.get('trend_method', 1)))

        self.frozen_list.setItem(1, 0, QTableWidgetItem('Intercept'))
        methodBox = ComboMethod(self)
        self.frozen_list.setCellWidget(1, 1, methodBox)
        methodBox.currentIndexChanged.connect(lambda index, methodBox=methodBox, row=1: self.method_update(methodBox, row))
        methodBox.setCurrentIndex(int(self.ini.get('intercept_method', 1)))

        # Add seasonal component combo boxes for trend and intercept
        seasBox = ComboSeasonal(self)
        self.frozen_list.setCellWidget(0, 2, seasBox)
        seasBox.currentIndexChanged.connect(lambda index, seasBox=seasBox, row=0: self.seas_update(seasBox, row))
        seasBox.setCurrentIndex(int(self.ini.get('trend_seasonal_component', self.ini.get('default_seasonal_component', 2))) - 1)
        if self.frozen_list.cellWidget(0, 1).currentIndex() != 2:
            seasBox.setDisabled(True)

        seasBox = ComboSeasonal(self)
        self.frozen_list.setCellWidget(1, 2, seasBox)
        seasBox.currentIndexChanged.connect(lambda index, seasBox=seasBox, row=1: self.seas_update(seasBox, row))
        seasBox.setCurrentIndex(int(self.ini.get('intercept_seasonal_component', self.ini.get('intercept_seasonal_component', 2))) - 1)
        if self.frozen_list.cellWidget(1, 1).currentIndex() != 2:
            seasBox.setDisabled(True)
        self.frozen_list.setHorizontalHeaderLabels(["Variable", "Method", "Seasonal Component"])

        total_height = sum(self.frozen_list.rowHeight(row) for row in range(self.frozen_list.rowCount()))
        total_height += self.frozen_list.horizontalHeader().height()  # Add header height
        self.frozen_list.setFixedHeight(total_height)

        self.frozen_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

    def update_proxy_table(self):
        # Update of the main proxy table
        self.proxy_list.setRowCount(len(self.proxies))
        # Add method combo boxes for each available proxy
        for k, i in enumerate(self.proxies):
            self.proxy_list.setItem(k, 0, QTableWidgetItem(i.name))
            methodBox = ComboMethod(self)
            self.proxy_list.setCellWidget(k, 1, methodBox)
            methodBox.currentIndexChanged.connect(lambda index, methodBox=methodBox, row=k: self.method_update(methodBox, row))
            methodBox.setCurrentIndex(int(i.method))

        # Add seasonal component combo boxes for each available proxy
        for k, i in enumerate(self.proxies):
            # self.proxy_list.setItem(k, 0, QTableWidgetItem(i.name))
            seasBox = ComboSeasonal(self)
            self.proxy_list.setCellWidget(k, 2, seasBox)
            seasBox.currentIndexChanged.connect(lambda index, seasBox=seasBox, row=k: self.seas_update(seasBox, row))
            seasBox.setCurrentIndex(i.seas_comp - 1)
            if self.proxy_list.cellWidget(k, 1).currentIndex() != 2:
                seasBox.setDisabled(True)
        self.proxy_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.proxy_list.setHorizontalHeaderLabels(["Proxy", "Method", "Seas. Comp."])

        # Update of the combo box for diagnostic
        self.dia_proxy_combo.clear()
        for k, i in enumerate(self.proxies):
            self.dia_proxy_combo.addItem(i.name)
        self.proxy_diagnostic(0)

    def sync_tables(self):
        for col in range(self.proxy_list.columnCount()):
            self.frozen_list.horizontalHeader().resizeSection(col, self.proxy_list.horizontalHeader().sectionSize(col))
        self.proxy_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for col in range(self.proxy_list.columnCount()):
            self.proxy_list.horizontalHeader().resizeSection(col, self.frozen_list.horizontalHeader().sectionSize(col))

    def sync_frozen_to_main(self, logical_index, old_size, new_size):
        self.proxy_list.horizontalHeader().resizeSection(logical_index, new_size)

    def open_data_dialog(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilters(["NetCDF (*.nc)", "ASCII files (*.*)"])
        dialog.setViewMode(QFileDialog.Detail)

        if dialog.exec_():
            fileName = dialog.selectedFiles()
        else:
            return

        self.open_data_settings_dialog(fileName)

        for i in fileName:
            data = load_netCDF(i, self.ini)
            if data == None:
                continue
            else:
                self.list_of_data.append(data)
        self.reload_data_list()

    def open_proxy_dialog(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilters(["ASCII files (*.*)", "NetCDF (*.nc)"])
        dialog.setViewMode(QFileDialog.Detail)

        if dialog.exec_():
            fileName = dialog.selectedFiles()
        else:
            return

        self.open_proxy_settings_dialog(fileName)

        for k, i in enumerate(fileName):
            new_proxy = load_add_proxy_file(self.ini, -1)
            if new_proxy == None:
                continue
            else:
                self.proxies.append(new_proxy)

        self.update_proxy_table()

    def open_data_settings_dialog(self, filename):
        var_window = VariableWindow(self.ini, filename)
        var_window.ini_signal.connect(self.update_ini_settings)
        var_window.setWindowTitle('Variable Settings')
        var_window.exec_()

    def open_proxy_settings_dialog(self, filename):
        proxy_window = ProxyWindow(self.ini, filename)
        proxy_window.ini_signal.connect(self.update_ini_settings)
        proxy_window.setWindowTitle('Proxy Settings')
        proxy_window.exec_()

    def update_ini_settings(self, ini):
        self.ini = ini

    def reload_data_list(self):
        self.data_list.clear()
        for i in self.list_of_data:
            self.data_list.addItem(i.name)

        self.add_data_dia()

    def define_palettes(self):
        # Set palette
        self.palette_wrong = QPalette()
        self.palette_wrong.setColor(QPalette.Background, QColor(212, 19, 22))
        self.palette_wrong.setColor(QPalette.Base, QColor(212, 19, 22))

        self.palette_right = QPalette()
        self.palette_right.setColor(QPalette.ColorRole.WindowText, QColor(0, 170, 0))
        self.palette_right.setColor(QPalette.Text, QColor(0, 170, 0))
        self.palette_right.setColor(QPalette.Background, QColor(255, 255, 255, 0))

    def inflection_enable(self):
        # Enables/Disables the date entry
        if self.infl_check.isChecked() == True:
            self.inflection_point.setEnabled(True)
            self.inflection_method.setEnabled(True)
            self.ini['inflection_method'] = self.infl_method_list[self.inflection_method.currentIndex()]
            self.ini['inflection_point'] = self.inflection_point.text()
        else:
            self.inflection_point.setEnabled(False)
            self.ini.pop('inflection_point', None)
            self.inflection_method.setEnabled(False)
            self.ini.pop('inflection_method', None)

    def anomaly_enable(self):
        if self.anomaly_check.isChecked() == True:
            self.ini['anomaly'] = 'True'
            self.anom_frame.setEnabled(True)
        else:
            self.ini['anomaly'] = 'False'
            self.anom_frame.setEnabled(False)

    def anomaly_method_toggle(self):
        if self.radio_rel.isChecked():
            self.ini['anomaly_method'] = 'rel'
        elif self.radio_abs.isChecked():
            self.ini['anomaly_method'] = 'abs'

    def format_check(self):
        # Changes the checkmarks if the format of the date is being recongnized
        checkbox = getattr(self, 'check_' + str(self.sender().objectName()).split('_')[0], None)

        if str(self.sender().text()) == '':
            checkbox.setChecked(False)
            checkbox.setPalette(self.palette_wrong)
            self.ini.pop(self.sender().objectName(), None)
            return
        try:
            date = pd.to_datetime(str(self.sender().text()), format='%Y-%m').date()
            checkbox.setChecked(True)
            checkbox.setPalette(self.palette_right)
            self.ini[self.sender().objectName()] = dt.datetime.strftime(dt.datetime.strptime(str(self.sender().text()), '%Y-%m'), '%Y-%m')
        except:
            checkbox.setChecked(False)
            checkbox.setPalette(self.palette_wrong)
            self.ini.pop(self.sender().objectName(), None)

    def text_check(self):
        # Changes the checkmarks if the format of the input is being recognized
        check = averaging_window_text_check(str(self.sender().text()))
        self.ini['averaging_window'] = str(self.sender().text())

        months_str = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        if check == 0:
            self.check_mean.setChecked(False)
            self.check_mean.setPalette(self.palette_wrong)
            self.mean_line.setToolTip('<html><head/><body><p>Currently averaged months:</p><p>Months must be written with their respective number, seperated by &quot;,&quot;. To get a yearly average, use either &quot;yearly&quot; or &quot;all&quot;.</p></body></html>')
        else:
            self.check_mean.setChecked(True)
            self.check_mean.setPalette(self.palette_right)
            if check == 2:
                month_list = re.split(r',\s*', str(self.sender().text()))
                month_list = np.array([int(num) for num in month_list])
                string = [months_str[i-1] for i in month_list]
                self.mean_line.setToolTip('<html><head/><body><p>Currently averaged months:</p>' + ', '.join(string) + '</p><p>Months must be written with their respective number, seperated by &quot;,&quot;. To get a yearly average, use either &quot;yearly&quot; or &quot;all&quot;.</p></body></html>')
            else:
                self.mean_line.setToolTip('<html><head/><body><p>Currently averaged months:</p>' + 'all' + '</p><p>Months must be written with their respective number, seperated by &quot;,&quot;. To get a yearly average, use either &quot;yearly&quot; or &quot;all&quot;.</p></body></html>')

    def method_update(self, methodBox, row):
        table = self.sender().parent().parent()
        if table.objectName() != 'frozen_list':
            self.proxies[row].method = int(methodBox.currentIndex())
            if int(methodBox.currentIndex()) > int(self.frozen_list.cellWidget(1, 1).currentIndex()):
                self.frozen_list.cellWidget(1, 1).setCurrentIndex(int(methodBox.currentIndex()))
        else:
            if table.indexAt(methodBox.pos()).row() == 0:
                self.ini['trend_method'] = int(methodBox.currentIndex())
            elif table.indexAt(methodBox.pos()).row() == 1:
                self.ini['intercept_method'] = int(methodBox.currentIndex())

        if table.cellWidget(row, 2) is not None:
            if int(methodBox.currentIndex()) == 2:
                table.cellWidget(row, 2).setEnabled(True)
            else:
                table.cellWidget(row, 2).setEnabled(False)

    def seas_update(self, seasBox, row):
        table = self.sender().parent().parent()
        if table.objectName() != 'frozen_list':
            self.proxies[row].seas_comp = seasBox.currentIndex() + 1
        else:
            if table.indexAt(seasBox.pos()).row() == 0:
                self.ini['trend_seasonal_component'] = seasBox.currentIndex() + 1
            elif table.indexAt(seasBox.pos()).row() == 1:
                self.ini['intercept_seasonal_component'] = seasBox.currentIndex() + 1

    def load_presets(self):
        self.preset_list = ['-None-']
        for file in os.listdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config folder')):
            if file.endswith('.ini'):
                self.preset_list.append(file.split('.')[0])
        self.preset_combo.clear()
        self.preset_combo.addItems(self.preset_list)

    def change_preset(self):
        if self.preset_combo.currentIndex() == 0:
            return

        file_name = './config folder/' + self.preset_list[self.preset_combo.currentIndex()] + '.ini'

        ini = {}

        with open(file_name, 'r') as f:
            # Count the number of additional_proxy_path keys
            add_proxy_count = 0
            for line in f:
                if '=' not in line or line[0] == '#':
                    # Skip line in config file if no = sign is in there or if it starts with #
                    continue
                (key, val) = line.split('=')
                # cleaning the input data
                key = key.strip()
                if key == 'additional_proxy_path':
                    add_proxy_count += 1

            # Creating empty lists for the additional proxy data
            ini['additional_proxy_name'] = np.empty(add_proxy_count, dtype='object')
            ini['additional_proxy_path'] = np.empty(add_proxy_count, dtype='object')
            ini['additional_proxy_time_col'] = np.zeros(add_proxy_count, dtype='object')
            ini['additional_proxy_data_col'] = np.ones(add_proxy_count, dtype=int)
            ini['additional_proxy_method'] = np.ones(add_proxy_count, dtype=int)
            ini['additional_proxy_comment_symbol'] = np.empty(add_proxy_count, dtype='object')
            ini['additional_proxy_header_size'] = np.empty(add_proxy_count, dtype=int)
            ini['additional_proxy_time_format'] = np.empty(add_proxy_count, dtype='object')

        with open(file_name, 'r') as f:
            add_proxy_count = -1
            for line in f:
                if '=' not in line or line[0] == '#':
                    # Skip line in config file if no = sign is in there or if it starts with #
                    continue
                (key, val) = line.split('=')
                # cleaning the input data
                key = key.strip()
                val = val.strip()
                if key in ini.keys():
                    if key == 'additional_proxy_path':
                        add_proxy_count += 1
                    ini[key][add_proxy_count] = val
                else:
                    ini[key] = val

        ini['additional_proxy_method'] = ini.get('additional_proxy_method', ini.get('default_proxy_method', 1))

        # config ini loaded

        if 'inflection_point' in ini:
            self.inflection_point.setText(dt.datetime.strftime(dt.datetime.strptime(ini['inflection_point'], '%Y-%m').date(), '%Y-%m'))
        else:
            self.inflection_point.setText('YYYY-MM')

        if 'inflection_point' in ini and 'inflection_method' in ini:
            if ini['inflection_method'] == 'ind':
                self.inflection_method.setCurrentIndex(0)
            elif ini['inflection_method'] == 'pwl':
                self.inflection_method.setCurrentIndex(1)
            self.infl_check.setChecked(True)

        if 'start_date' in ini:
            self.start_date.setText(dt.datetime.strftime(dt.datetime.strptime(ini['start_date'], '%Y-%m').date(), '%Y-%m'))
        else:
            self.start_date.setText('YYYY-MM')

        if 'end_date' in ini:
            self.end_date.setText(dt.datetime.strftime(dt.datetime.strptime(ini['end_date'], '%Y-%m').date(), '%Y-%m'))
        else:
            self.end_date.setText('YYYY-MM')

        if 'trend_method' in ini:
            self.trend_method_combo.setCurrentIndex(int(ini['trend_method']))
        else:
            self.trend_method_combo.setCurrentIndex(1)
        if int(self.intercept_method_combo.currentIndex()) == 2:
            self.intercept_seas_combo.setDisabled(False)
        else:
            self.intercept_seas_combo.setDisabled(True)

        if 'intercept_method' in ini:
            self.intercept_method_combo.setCurrentIndex(int(ini['intercept_method']))
        else:
            self.intercept_method_combo.setCurrentIndex(1)
        if int(self.intercept_method_combo.currentIndex()) == 2:
            self.intercept_seas_combo.setDisabled(False)
        else:
            self.intercept_seas_combo.setDisabled(True)

        self.mean_line.setText(self.ini.get('averaging_window', ''))

        if ini.get('anomaly', 'False') == 'True':
            self.anomaly_check.setChecked(True)
        else:
            self.anomaly_check.setChecked(False)

    def all_proxy_method_change(self):
        index = int(self.all_proxy_method.currentIndex()) - 1
        if index < 0:       # Doesn't do anything if ComboBox changes to "mixed"
            return

        for row in range(self.proxy_list.rowCount()):
            combo_box = self.proxy_list.cellWidget(row, 1)
            combo_box.setCurrentIndex(index)
        for row in range(self.frozen_list.rowCount()):
            combo_box = self.frozen_list.cellWidget(row, 1)
            combo_box.setCurrentIndex(index)

    def inflection_method_change(self):
        self.ini['inflection_method'] = self.infl_method_list[self.inflection_method.currentIndex()]

    def data_change(self):
        # self.ini['time_format'] = self.list_of_data[self.data_list.currentRow()].time_format

        self.populate_dim_limits()

    def clear_dim_widgets(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    child_layout = item.layout()
                    if child_layout is not None:
                        self.clear_dim_widgets(child_layout)

    def populate_dim_widget(self):
        self.dim_boxes.clear()

        for dim_index in range(1, len(self.current_data.o3.shape)):
            col_layout = QVBoxLayout()
            label = QtWidgets.QLabel(self.current_data.dim_array[dim_index])
            col_layout.addWidget(label)

            combo = QtWidgets.QComboBox()
            values = getattr(self.current_data, self.current_data.dim_array[dim_index])
            combo.addItems([str(value) for value in values])
            col_layout.addWidget(combo)

            self.dim_boxes.append(combo)

            self.dim_layout.addLayout(col_layout)

    def populate_X_dim_widget(self):
        self.dim_X_boxes.clear()

        for dim_index in range(1, len(self.current_data.o3.shape)):
            col_layout = QVBoxLayout()
            label = QtWidgets.QLabel(self.current_data.dim_array[dim_index])
            col_layout.addWidget(label)

            combo = QtWidgets.QComboBox()
            values = getattr(self.current_data, self.current_data.dim_array[dim_index])
            combo.addItems([str(value) for value in values])
            col_layout.addWidget(combo)
            combo.currentIndexChanged.connect(self.X_diagnostic)

            self.dim_X_boxes.append(combo)

            self.dim_X_layout.addLayout(col_layout)
        self.X_diagnostic()

    def populate_con_dim_widget(self):
        self.dim_con_boxes.clear()

        for dim_index in range(1, len(self.current_data.o3.shape)):
            col_layout = QVBoxLayout()
            label = QtWidgets.QLabel(self.current_data.dim_array[dim_index])
            col_layout.addWidget(label)

            combo = QtWidgets.QComboBox()
            values = getattr(self.current_data, self.current_data.dim_array[dim_index])
            combo.addItem('---X Axis---')
            combo.addItem('---Y Axis---')
            combo.addItems([str(value) for value in values])
            col_layout.addWidget(combo)
            combo.currentIndexChanged.connect(self.sync_combo_boxes)

            self.dim_con_boxes.append(combo)

            self.dim_con_layout.addLayout(col_layout)
        self.dim_con_boxes[1].setCurrentIndex(1)

    def lim_update_min(self, dim, index):
        min_combo, max_combo = self.combo_pairs[dim]
        if index > max_combo.currentIndex():
            max_combo.setCurrentIndex(index)  # Adjust max to match min
        dim_index = self.list_of_data[self.data_list.currentRow()].dim_array.index(dim)
        self.ini['additional_var_' + str(dim_index + 1) + '_limit'] = str(min_combo.currentIndex()) + ', ' + str(max_combo.currentIndex())

    def lim_update_max(self, dim, index):
        min_combo, max_combo = self.combo_pairs[dim]
        if index < min_combo.currentIndex():
            min_combo.setCurrentIndex(index)  # Adjust min to match max
        dim_index = self.list_of_data[self.data_list.currentRow()].dim_array.index(dim)
        self.ini['additional_var_' + str(dim_index + 1) + '_limit'] = str(min_combo.currentIndex()) + ', ' + str(max_combo.currentIndex())

    def populate_dim_limits(self):
        data = self.list_of_data[self.data_list.currentRow()]
        # Clear existing widgets in data_lim_box
        for i in reversed(range(self.data_lim_box.layout().count())):
            widget = self.data_lim_box.layout().itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.combo_pairs.clear()

        # Get dimensions except 'time'
        dimensions = [dim for dim in data.dim_array if dim != 'time']

        main_layout = self.data_lim_box.layout()
        if main_layout is None:
            main_layout = QVBoxLayout()
            self.data_lim_box.setLayout(main_layout)

        # Loop through each dimension and create a pair of combo boxes
        for dim in dimensions:
            widget = QtWidgets.QWidget()  # Container widget
            h_layout = QHBoxLayout(widget)  # Horizontal layout for combo box pairs

            dim_values = list(map(str, getattr(data, dim)))
            # First combo box with label
            vbox1 = QVBoxLayout()
            label1 = QtWidgets.QLabel(f"{dim} Min:")
            combo1 = QtWidgets.QComboBox()
            combo1.addItems(dim_values)  # Populate with data
            vbox1.addWidget(label1)
            vbox1.addWidget(combo1)

            # Second combo box with label
            vbox2 = QVBoxLayout()
            label2 = QtWidgets.QLabel(f"{dim} Max:")
            combo2 = QtWidgets.QComboBox()
            combo2.addItems(dim_values)
            combo2.setCurrentIndex(len(dim_values) - 1)
            vbox2.addWidget(label2)
            vbox2.addWidget(combo2)

            self.combo_pairs[dim] = (combo1, combo2)

            # Connect signals to slot functions
            combo1.currentIndexChanged.connect(lambda index, d=dim: self.lim_update_min(d, index))
            combo2.currentIndexChanged.connect(lambda index, d=dim: self.lim_update_max(d, index))

            # Add both vertical layouts to the horizontal layout
            h_layout.addLayout(vbox1)
            h_layout.addLayout(vbox2)

            # Add the widget container to the group box layout
            main_layout.addWidget(widget)

    def sync_combo_boxes(self):
        # Get the indices of all combo boxes
        current_indices = [combo.currentIndex() for combo in self.dim_con_boxes]

        # Disable the plot button if X- and Y-axis are not picked exactly once and if one of these has not enough values
        valid_indices = current_indices.count(0) == 1 and current_indices.count(1) == 1
        valid_lengths = all(self.dim_con_boxes[i].count() > 3 for i, idx in enumerate(current_indices) if idx in (0, 1))
        self.plot_button_con.setDisabled(not (valid_indices and valid_lengths))

        sender_index = self.sender().currentIndex()
        if sender_index in {0, 1}:
            for i, combo in enumerate(self.dim_con_boxes):
                if combo != self.sender() and combo.currentIndex() == sender_index:
                    # Find a new valid index for the conflicting combo box
                    for new_index in range(combo.count()):
                        if new_index not in {0, 1} and new_index != sender_index:
                            combo.setCurrentIndex(new_index)
                            break

    def X_diagnostic(self):
        indices = [combo.currentIndex() for combo in self.dim_X_boxes]
        matrix = self.X[(slice(None), *indices, slice(None))]
        header = self.proxy_string
        date = self.time

        # Fill Table
        self.dia_X_table.setColumnCount(len(header))
        self.dia_X_table.setRowCount(len(date))

        self.dia_X_table.setHorizontalHeaderLabels(header)
        self.dia_X_table.setVerticalHeaderLabels(date.astype(str))

        for k in range(len(date)):
            for kk in range(len(header)):
                self.dia_X_table.setItem(k, kk, QTableWidgetItem(str(matrix[k, kk])))

    def data_diagnostic(self):
        indices = [combo.currentIndex() for combo in self.dim_data_boxes]
        matrix = self.list_of_data[self.dia_data_combo.currentIndex()].o3[(slice(None), *indices)]
        date = self.list_of_data[self.dia_data_combo.currentIndex()].time

        # Fill Table
        self.dia_data_table.setColumnCount(1)
        self.dia_data_table.setRowCount(len(date))

        self.dia_data_table.setVerticalHeaderLabels(date.astype(str))

        for k in range(len(date)):
            self.dia_data_table.setItem(k, 0, QTableWidgetItem(str(matrix[k])))

        # Fill information
        self.dia_data_start.setText(str(np.nanmin(date)))
        self.dia_data_end.setText(str(np.nanmax(date)))
        self.dia_data_time.setText(str(len(date)))
        self.dia_data_nan.setText(str(np.sum(np.isnan(matrix.filled(np.nan)))))

    def plot_model_figure(self):
        # Clear the figure
        self.canvas.figure.clf()

        # Preparing Plot values
        data = copy.deepcopy(self.current_data)

        # Get dimension combo boxes indices
        plot_indices = [combo.currentIndex() for combo in self.dim_boxes]
        indices = tuple([slice(None)] + list(plot_indices))

        X_og = data.time
        X = self.time
        Y_og = data.o3[indices]
        Y = self.trend_data[indices]

        valid_cols = ~np.isnan(self.X[indices]).all(axis=0)
        valid_rows = ~np.isnan(self.X[indices]).all(axis=1)

        time = pd.DatetimeIndex(data.time)

        # if self.anomaly_check.isChecked() and self.radio_abs.isChecked():
        #     for k in range(12):
        #         Y[time.month == k + 1] = data.o3[indices][time.month == k + 1] - np.nanmean(data.o3[indices][time.month == k + 1].filled(np.nan))
        # elif self.anomaly_check.isChecked() and self.radio_rel.isChecked():
        #     for k in range(12):
        #         Y[time.month == k + 1] = (data.o3[indices][time.month == k + 1] - np.nanmean(data.o3[indices][time.month == k + 1].filled(np.nan))) / np.nanmean(data.o3[indices][time.month == k + 1].filled(np.nan))

        Y_trend = self.trends[tuple(plot_indices)]
        if not isinstance(Y_trend, (list, np.ndarray)):
            Y_trend = [Y_trend]
        Y_signi = self.signi[tuple(plot_indices)]

        Y_model = np.matmul(self.X[indices][valid_rows][:, valid_cols], self.betaa[tuple(plot_indices)][valid_cols])

        slope_beta = []
        slope_X = []
        str_groups = get_string_groups(self.proxy_string)
        for key, i in str_groups.items():
            if key[1] == 'month-of-the-year':
                slope_beta.append(np.nanmean(self.betaa[tuple(plot_indices)][i], axis=0))
                slope_X.append([np.nanmax(row[tuple(plot_indices)][i]) for row in self.X])
            else:
                slope_beta.append(self.betaa[tuple(plot_indices)][i[0]])
                slope_X.append(self.X[indices][:, i[0]])
        trend_string = "\n".join([f"trend {k+1}: {v:.2f}%/decade" for k, v in enumerate(Y_trend)])

        Y_slope = np.array(slope_X).T @ np.array(slope_beta)
        plot_number = 1
        # print(slope_beta)
        self.canvas.axes_list = [self.canvas.figure.add_subplot(plot_number, 1, i + 1) for i in range(plot_number)]

        # bounds = [-7, -5, -3, -1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1, 3, 5, 7]
        bounds = np.arange(-9, 10, 1, dtype=int)
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list("", plt.get_cmap('RdBu_r')(np.arange(10, 245, 3).astype(int)))
        cmap.set_under(plt.get_cmap('RdBu_r')(0))
        cmap.set_over(plt.get_cmap('RdBu_r')(255))
        norm = mpl.colors.BoundaryNorm(bounds, cmap.N)

        for k, ax in enumerate(self.canvas.axes_list):
            if X_og.shape != X.shape and not self.anomaly_check.isChecked():
                    ax.plot(X_og, Y_og, label='Original Time Series', linewidth=1.4)
            ax.plot(X, Y, label='Time Series', linewidth=1.8)

            ax.plot(self.time[valid_rows], Y_model, label='Model', linewidth=1.8)
            ax.plot(self.time[valid_rows], Y_slope[valid_rows], path_effects=[pe.Stroke(linewidth=5, foreground='black'), pe.Normal()], label='Trend', linewidth=1.3)
            y_label_cor = 0.025
            self.canvas.figure.text(0.45, y_label_cor, 'Time [yr]', ha='center', va='center', rotation='horizontal', fontsize=12)
            x_label_cor = 0.02
            self.canvas.figure.text(x_label_cor, 0.5, 'Number Density [molec/cm³]', ha='center', va='center', rotation='vertical', fontsize=12)
            ax.legend(loc='upper right')

            props = dict(boxstyle='round', facecolor='white', alpha=1)
            ax.text(0.05, 0.95, trend_string, transform=ax.transAxes, fontsize=10, verticalalignment='top', horizontalalignment='left', bbox=props)
            ax.set_title(data.name + '\nat ' + ', '.join(f"{dim} {val}" for dim, val in zip(data.dim_array[1:], list([combo.currentText() for combo in self.dim_boxes]))))
        toolbar = NavigationToolbar(self.canvas, self)

        self.canvas.draw()

    def plot_contour_figure(self):
        # Clear the figure
        self.con_canvas.figure.clf()

        trends = self.trends
        signis = self.signi

        data = copy.deepcopy(self.current_data)

        # Get dimension combo boxes indices
        plot_indices = ()
        for k, combo in enumerate(self.dim_con_boxes):
            if combo.currentIndex() == 0:
                plot_indices += (slice(None),)
                x_grid = getattr(data, data.dim_array[1:][k])
                x_label = data.dim_array[1:][k]
            elif combo.currentIndex() == 1:
                plot_indices += (slice(None),)
                y_grid = getattr(data, data.dim_array[1:][k])
                y_label = data.dim_array[1:][k]
            else:
                plot_indices += (combo.currentIndex() - 2,)
        if trends[plot_indices].shape != (len(y_grid), len(x_grid)):
            trend = trends[plot_indices].T
            signi = signis[plot_indices].T > 2
        else:
            trend = trends[plot_indices]
            signi = signis[plot_indices] > 2
        masked_uncertainty = np.where(np.isnan(trend), np.nan, signi)
        # Calculate max and min for both axis
        # row_start, row_end = np.where(np.any(~np.isnan(trend), axis=1))[0][[0, -1]]
        # col_start, col_end = np.where(np.any(~np.isnan(trend), axis=0))[0][[0, -1]]
        #
        # # print(col_start, col_end)
        # # print(row_start, row_end)
        # magnitude = 10 ** int(math.log10(max(abs(y_grid[row_start]), abs(y_grid[row_end]), 1)))
        # y_min = math.floor(y_grid[row_start] / magnitude) * magnitude
        # y_max = math.ceil((y_grid[row_end]) / magnitude) * magnitude
        #
        # magnitude = 10 ** int(math.log10(max(abs(x_grid[col_start]), abs(x_grid[col_end]), 1)))
        # x_min = math.floor(x_grid[col_start] / magnitude) * magnitude
        # x_max = math.ceil((x_grid[col_end]) / magnitude) * magnitude

        self.con_canvas.axes = self.con_canvas.figure.add_subplot(1, 1, 1)

        # bounds = np.arange(-9, 10, 1, dtype=int)
        bounds = [-7, -5, -4, -3, -2.5, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 7]
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list("", plt.get_cmap('RdBu_r')(np.arange(10, 245, 3).astype(int)))
        cmap.set_under(plt.get_cmap('RdBu_r')(0))
        cmap.set_over(plt.get_cmap('RdBu_r')(255))
        norm = mpl.colors.BoundaryNorm(bounds, cmap.N)

        if self.con_alternative.isChecked() == True:
            cf = self.con_canvas.axes.imshow(trend, cmap=cmap, norm=norm, extent=[x_grid[0] + (x_grid[0]-x_grid[1])/2, x_grid[-1] + (x_grid[-1]-x_grid[-2])/2, y_grid[0] + (y_grid[0]-y_grid[1])/2, y_grid[-1] + (y_grid[-1]-y_grid[-2])/2], origin='lower', aspect='auto')
            if self.con_uncertainty.isChecked() == True:
                for i in range(trend.shape[0]):
                    for j in range(trend.shape[1]):
                        if not masked_uncertainty[i, j]:
                            if i+1 == trend.shape[0] and j+1 == trend.shape[1]:
                                self.con_canvas.axes.add_patch(patches.Rectangle((x_grid[j] + (x_grid[j - 1] - x_grid[j]) / 2, y_grid[i] + (y_grid[i - 1] - y_grid[i]) / 2), (x_grid[j] - x_grid[j - 1]), (y_grid[i] - y_grid[i - 1]), hatch="////", fill=False, edgecolor='black'))
                            elif i+1 == trend.shape[0]:
                                self.con_canvas.axes.add_patch(patches.Rectangle((x_grid[j] + (x_grid[j] - x_grid[j + 1]) / 2, y_grid[i] + (y_grid[i - 1] - y_grid[i]) / 2), (x_grid[j + 1] - x_grid[j]), (y_grid[i] - y_grid[i-1]), hatch="////", fill=False, edgecolor='black'))
                            elif j+1 == trend.shape[1]:
                                self.con_canvas.axes.add_patch(patches.Rectangle((x_grid[j] + (x_grid[j - 1] - x_grid[j]) / 2, y_grid[i] + (y_grid[i] - y_grid[i + 1]) / 2), (x_grid[j] - x_grid[j - 1]), (y_grid[i + 1] - y_grid[i]), hatch="////", fill=False, edgecolor='black'))
                            else:
                                self.con_canvas.axes.add_patch(patches.Rectangle((x_grid[j] + (x_grid[j] - x_grid[j + 1]) / 2, y_grid[i] + (y_grid[i] - y_grid[i + 1]) / 2), (x_grid[j + 1] - x_grid[j]), (y_grid[i + 1] - y_grid[i]), hatch="////", fill=False, edgecolor='black'))
                            # self.con_canvas.axes.add_patch(patches.Rectangle((x_grid[0] + (x_grid[0]-x_grid[1])/2 + j * (x_grid[1] - x_grid[0]), y_grid[0] + (y_grid[0]-y_grid[1])/2 + i * (y_grid[1] - y_grid[0])), (x_grid[1] - x_grid[0]), (y_grid[1] - y_grid[0]), hatch="////", fill=False, edgecolor='black'))
        else:
            cf = self.con_canvas.axes.contourf(x_grid, y_grid, trend, cmap=cmap, levels=bounds, norm=norm, extend='both')
            self.con_canvas.axes.contour(x_grid, y_grid, trend, levels=bounds, colors=('k',), alpha=0.7, norm=norm, extend='both', linewidths=1)
            if self.con_uncertainty.isChecked() == True:
                self.con_canvas.axes.contourf(x_grid, y_grid, masked_uncertainty, levels=[0, 0.5], colors='none', hatches=['\\\\'])
                self.con_canvas.axes.contourf(x_grid, y_grid, masked_uncertainty, levels=[0, 0.5], colors='#DBDBDB', norm=norm, alpha=0.65)
        self.con_canvas.axes.set_xlim([np.nanmin(x_grid), np.nanmax(x_grid)])
        self.con_canvas.axes.set_ylim([np.nanmin(y_grid), np.nanmax(y_grid)])
        self.con_canvas.axes.tick_params(axis='both')
        # self.con_canvas.axes.set_title(data.name + ' at ' + ', '.join(f"{dim} {val}" for dim, val in zip(data.dim_array[1:], list([combo.currentText() for combo in self.dim_boxes]))))
        self.con_canvas.axes.set_xlabel(x_label, fontsize=14)
        self.con_canvas.axes.set_ylabel(y_label, fontsize=14)

        divider = make_axes_locatable(self.con_canvas.axes)
        cbar_ax = divider.append_axes("right", size="5%", pad=0.2)
        cbar = self.con_canvas.figure.colorbar(cf, cax=cbar_ax, label='[%/decade]')
        cbar.set_ticks(bounds)
        self.con_canvas.figure.tight_layout()
        toolbar = NavigationToolbar(self.con_canvas, self)

        self.con_canvas.draw()

    def print_ini(self):
        print('brian@iup.physik.uni-bremen.de')

    def compute_trends(self):
        self.setDisabled(True)
        self.trends, self.signi, diagnostic = iup_reg_model(self.list_of_data[self.data_list.currentRow()], self.proxies, self.ini)
        self.setDisabled(False)

        self.X = diagnostic[0]
        self.beta = diagnostic[1]
        self.betaa = diagnostic[2]
        self.convbeta = diagnostic[3]
        self.proxy_string = diagnostic[4]
        self.time = diagnostic[5]
        self.trend_data = diagnostic[6]
        self.current_ini = copy.copy(self.ini)
        self.current_data = copy.deepcopy(self.list_of_data[self.data_list.currentRow()])
        self.current_data = set_data_limits(self.current_data, self.current_ini)

        # Enable Plotting
        self.plot_button.setDisabled(False)

        self.clear_dim_widgets(self.dim_layout)
        self.populate_dim_widget()
        self.clear_dim_widgets(self.dim_X_layout)
        self.populate_X_dim_widget()
        self.clear_dim_widgets(self.dim_con_layout)
        self.populate_con_dim_widget()


def load_config_ini(ini_path):
    # create a dictionary with all options loaded in, the config.ini file must be in the folder of the python program
    ini = {}

    with open(ini_path, 'r') as f:
        # Count the number of additional_proxy_path keys
        add_proxy_count = 0
        for line in f:
            if '=' not in line or line[0] == '#':
                # Skip line in config file if no = sign is in there or if it starts with #
                continue
            (key, val) = line.split('=')
            # cleaning the input data
            key = key.strip()
            if key == 'additional_proxy_path':
                add_proxy_count += 1
        if add_proxy_count > 0:
            # Creating empty lists for the additional proxy data
            ini['additional_proxy_name'] = np.empty(add_proxy_count, dtype='object')
            ini['additional_proxy_path'] = np.empty(add_proxy_count, dtype='object')
            ini['additional_proxy_time_col'] = np.zeros(add_proxy_count, dtype='object')
            ini['additional_proxy_data_col'] = np.ones(add_proxy_count, dtype='object')
            ini['additional_proxy_method'] = np.ones(add_proxy_count, dtype=int)
            ini['additional_proxy_seas_comp'] = np.ones(add_proxy_count, dtype=int)*2
            ini['additional_proxy_tag'] = np.empty(add_proxy_count, dtype='object')
            # ini['additional_proxy_comment_symbol'] = np.empty(add_proxy_count, dtype='object')
            ini['additional_proxy_header_size'] = np.zeros(add_proxy_count, dtype=int)
            ini['additional_proxy_time_format'] = np.empty(add_proxy_count, dtype='object')
            ini['additional_proxy_tag_array'] = np.empty(add_proxy_count, dtype='object')

    with open(ini_path, 'r') as f:
        add_proxy_count = -1
        for line in f:
            if '=' not in line or line[0] == '#':
                # Skip line in config file if no = sign is in there or if it starts with #
                continue
            (key, val) = line.split('=')
            # Cleaning the input data
            key = key.strip()
            val = val.strip()
            if key in ini.keys():
                if key == 'additional_proxy_path':
                    add_proxy_count += 1
                ini[key][add_proxy_count] = val
            else:
                ini[key] = val
    # ini['additional_proxy_method'] = ini.get('additional_proxy_method', ini.get('default_proxy_method', 1))

    return ini


def proxies_to_class(proxy_raw):
    # Convert each proxy in the list to the proxy class
    proxy_list = []
    proxy_array = np.array(proxy_raw)

    for count, proxy in enumerate(proxy_raw):
        proxy_list.append(Proxy(proxy))
        proxy_list[count].time = pd.to_datetime(pd.Series(proxy_raw.index)).dt.date.map(lambda t: t.replace(day=15))
        proxy_list[count].data = proxy_array[:, count]

    return proxy_list


def get_enso_lag(enso, enso_lag, date_start, date_end):
    # Function to get the ENSO data with 1 year prior and 1 year after the actual time series
    # If the actual time series ends or start without 1 year puffer to ENSO, take the rest of the ENSO data and
    # combine it with the last year of the data
    for k, i in enumerate(enso.time):
        if i.year == date_start.year and i.month == date_start.month:
            ind_start = k
    for k, i in enumerate(enso.time):
        if i.year == date_end.year and i.month == date_end.month:
            ind_end = k
            break
        else:
            ind_end = len(enso.time)

    if ind_start-12 < 0:
        dif_start = abs(ind_start-12)
        enso_start = np.concatenate([enso.data[ind_start:ind_start+dif_start], enso.data[:ind_start]])
    else:
        enso_start = enso.data[ind_start-12:ind_start]

    if ind_end+12 > len(enso.data):
        dif_end = abs(ind_end+12-len(enso.data))
        enso_end = np.concatenate([enso.data[ind_end+1:], enso.data[ind_end-dif_end:ind_end+1]])
    else:
        enso_end = enso.data[ind_end:ind_end+12]

    enso_new = np.concatenate([enso_start, enso.data[ind_start:ind_end+1], enso_end])

    enso.data = enso_new[12+enso_lag:-12+enso_lag]

    return enso


def get_proxy_time_overlap(ini, proxies, data):
    # Create a copy of the data and proxies that will get overwritten
    new_data = copy.deepcopy(data)
    new_proxies = copy.deepcopy(proxies)

    new_data.time = np.array([date.replace(day=15) for date in data.time])

    # Load dates when calculation should start or else use the first and last date of the data time series
    if 'start_date' in ini:
        date_start = dt.datetime.strptime(ini['start_date'], '%Y-%m').date().replace(day=15)
        if date_start < new_data.time[0]:
            date_start = new_data.time[0]
    else:
        date_start = new_data.time[0]

    for i in new_proxies:
        if date_start < np.array(i.time)[0]:
            date_start = np.array(i.time)[0]

    if 'end_date' in ini:
        date_end = dt.datetime.strptime(ini['end_date'], '%Y-%m').date().replace(day=15)
        if date_end > new_data.time[-1]:
            date_end = new_data.time[-1]
            # raise Exception('The input for the end date of the trend calculation is later than the last date of the time series.')
    else:
        date_end = new_data.time[-1]

    for i in new_proxies:
        if date_end > np.array(i.time)[-1] and i.method != 0:
            date_end = np.array(i.time)[np.max(np.where(np.isin(np.array(i.time), new_data.time))[0])]

    new_data.date_start = np.where(new_data.time == date_start)[0][0]
    new_data.date_end = np.where(new_data.time == date_end)[0][0]

    for i in new_proxies:
        if i.method == 0:
            continue
        i.data = i.data[np.where(i.time == new_data.time[new_data.date_start])[0][0]:np.where(i.time == new_data.time[new_data.date_end])[0][0]]
        i.time = i.time[np.where(i.time == new_data.time[new_data.date_start])[0][0]:np.where(i.time == new_data.time[new_data.date_end])[0][0]]

    # for k, i in enumerate(new_proxies):
    #     if 'Nino' in i.name or 'ENSO' in i.name:
    #         # Shift the data of ENSO to incorporate the lag of the enso impact for the ozone
    #         enso_lag = -2
    #         enso = get_enso_lag(i, enso_lag, date_start, date_end)
    #         new_proxies[k].data = enso.data
    #     else:
    #         new_proxies[k].data = i.data[(i.time >= date_start.replace(day=15)) & (i.time <= date_end.replace(day=15))]

    return new_data, new_proxies


def set_data_limits(data, ini):
    slices = []

    for k, dim in enumerate(data.dim_array):
        if dim == 'time':
            slices.append(slice(None))  # Keep all time values
        else:
            limits = ini.get('additional_var_' + str(k + 1) + '_limit', None)
            if not limits:
                continue
            elif ',' in limits:
                min, max = list(map(int, ini.get('additional_var_' + str(k + 1) + '_limit', None).split(",")))
                slices.append(slice(min, max + 1))
                setattr(data, dim, getattr(data, dim)[slice(min, max + 1)])
            else:
                limits = int(ini.get('additional_var_' + str(k + 1) + '_limit', None))
                slices.append(slice(limits, limits + 1))
                setattr(data, dim, [getattr(data, dim)[limits]])

    data.o3 = data.o3[tuple(slices)]
    return data


def convert_to_datetime(time, ini=None):
    # Converting every possible time to datetime

    try:
        format = ini.get('time_format', None)
        if format:
            if np.issubdtype(time.dtype, 'O') or np.issubdtype(time.dtype, str):
                time = np.array([dt.datetime.strptime(str(x), format).date() for x in time])
            elif (time.astype(int) == time).all():
                time = np.array([dt.datetime.strptime(str(int(x)), format).date() for x in time])
            elif np.issubdtype(time.dtype, np.datetime64):
                time = pd.to_datetime(time)
            else:
                time = pd.Series(time).apply(lambda index: parse_time(index, format=format))
        else:
            print('There was no time format given. The IUP Regression Model will try to find a working format. Please check if the date is shown correctly afterwards.')
            time = pd.Series(time).apply(parse_time)

    except:
        time = pd.Series(time).apply(lambda index: parse_time(index, format=format))

    return np.array(time)


def convert_datetime_to_fractional(time):
    frac_array = np.empty(len(time))
    for k, i in enumerate(time):
        datetime_var = dt.datetime(i.year, i.month, i.day)
        year = datetime_var.year
        start_of_year = dt.datetime(year, 1, 1)
        next_year = dt.datetime(year + 1, 1, 1)
        total_seconds = (datetime_var - start_of_year).total_seconds()
        total_seconds_next_year = (next_year - start_of_year).total_seconds()
        frac_array[k] = year + total_seconds / total_seconds_next_year
    return frac_array


def parse_time(value, month=None, format=None):

    # If there is a month value, combine value (year) and month to one string
    if month:
        return dt.date(int(value), int(month), 15)
        # value = dt.date(int(value), int(month), 15).strftime('%Y-%m')

    if format:
        try:
            dt.datetime.strptime(value, format).date()
        except:
            print('The format did not work with the loaded time data. The IUP Regression Model will try to find a working format. Please check if the date is shown correctly afterwards.')

    # Convert value to string
    if float(value) - int(value) == 0:
        value = int(value)
    value = str(value)

    # Check for fractional year (e.g., 1997.0145)
    if re.match(r"^\d{4}\.\d+$", value):
        year = int(value[:4])
        fractional_year = float(value)
        start_of_year = dt.datetime(year, 1, 1)
        year_fraction = fractional_year - year
        days_in_year = 366 if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0) else 365
        result_date = start_of_year + dt.timedelta(days=year_fraction * days_in_year)
        return result_date.date()

    # Check for integer format with year and month (e.g., 199701)
    elif re.match(r"^\d{6}$", value):
        return dt.datetime.strptime(value, "%Y%m").date()

    # Check for integer format with year, month, and day (e.g., 19970101)
    elif re.match(r"^\d{8}$", value):
        return dt.datetime.strptime(value, "%Y%m%d").date()

    # Check for string formats with various separators (e.g., 1997-01, 1997_01)
    elif re.match(r"^\d{4}[-_/]\d{2}$", value):
        return dt.datetime.strptime(value, "%Y-%m").date() if '-' in value else dt.datetime.strptime(value, "%Y_%m").date() if '_' in value else dt.datetime.strptime(value, "%Y/%m").date()

    # Check for string formats with year, month, and day with various separators (e.g., 1997-01-01, 1997_01_01)
    elif re.match(r"^\d{4}[-_/]\d{2}[-_/]\d{2}$", value):
        return dt.datetime.strptime(value, "%Y-%m-%d").date() if '-' in value else dt.datetime.strptime(value, "%Y_%m_%d").date() if '_' in value else dt.datetime.strptime(value, "%Y/%m/%d").date()

    # If none of the formats match, raise an error
    else:
        raise ValueError(f"Unrecognized date format: {value}")


def get_string_groups(string_list):
    # This function will look into a list of strings and create a dictionary with different groups and their respective indices of the original list
    pattern_group = re.compile(r'(intercept|trend) #(\d+)')
    pattern_no_group = re.compile(r'(intercept|trend)')
    groups = {}
    attribute_list = ['single', 'harmonic', 'month-of-the-year']

    for k, i in enumerate(string_list):
        match = pattern_group.search(i)
        index = [kk for kk, s in enumerate(attribute_list) if s in i]
        if index[0] == None:
            continue
        if match and attribute_list[index[0]] in i:
            type_ = match.group(1)
            number = int(match.group(2))
            key = (type_, str(attribute_list[index[0]]), number)
            if key not in groups:
                groups[key] = []
            groups[key].append(k)
        else:
            match = pattern_no_group.search(i)
            if match and attribute_list[index[0]] in i:
                type_ = match.group(1)
                key = (type_, str(attribute_list[index[0]]), None)
                if key not in groups:
                    groups[key] = []
                groups[key].append(k)
    return groups


def averaging_window_text_check(input):
    # Returns 0 if the format is not recongnized, 1 if it's a yearly mean and 2 if it's the mean of certain months
    input = str(input)

    # If the input text is "yearly" or "all", then it will recognize it and return 1, returns 2 if the inputs include different months
    try:
        if input == 'yearly' or input == 'all':
            return 1
        else:
            month_list = re.split(r',\s*', input)
            month_list = np.array([int(num) for num in month_list])
            if (month_list >= 13).any() or (month_list <= -13).any() or len(np.unique(month_list)) < len(month_list):
                return 0
            else:
                return 2
    except:
        return 0


def load_default_proxies(ini):
    path = ini['proxy_path']
    # NEEDS TO BE MORE FLEXIBLE
    format = '%Y%m'

    proxy_raw = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), path), sep='\s+', index_col=0)
    proxy_raw.dropna(axis=1, how='all', inplace=True)
    proxy_raw.index = proxy_raw.index.to_series().apply(parse_time)
    proxy_raw = proxy_raw.drop('Month', axis=1)

    # Convert raw data to the proxy class
    proxy_list = proxies_to_class(proxy_raw)

    # Load AOD data
    path = ini['aod_path']
    aod = Proxy('AOD')

    aod_data = np.genfromtxt(os.path.join(os.path.dirname(os.path.abspath(__file__)), path), skip_header=1)
    try:
        aod.time = pd.Series([dt.datetime.strptime(str(int(date)), format).date() for date in aod_data[:, 0]])     # str(int(date)) is not perfect and should be improved upon
        aod.time = aod.time.apply(lambda dt: dt.replace(day=15))
    except:
        raise Exception(
            'The time format is not correct. Please follow the datetime format: hhttps://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior\nFor exammple "%Y-%M-%d" for the date format "2012-01-17"')

    aod.data = aod_data[:, 1:]
    aod.lat = np.arange(-85, 95, 10)

    # Add the AOD data to the proxy list
    proxy_list.append(aod)
    proxy_list[-1].tag = 'lat'

    if int(ini.get('default_proxy_limit', 0)) == 1:
        proxy_list = default_boundary_settings(proxy_list)

    for k, i in enumerate(proxy_list):
        proxy_method_str = 'default_proxy_' + str(k) + '_method'
        proxy_seasonal_str = 'default_proxy_' + str(k) + '_seasonal'
        i.method = int(ini.get(proxy_method_str, ini.get('default_proxy_method', 2)))
        i.seas_comp = int(ini.get(proxy_seasonal_str, ini.get('default_seasonal_component', 2)))
        i.source = [ini['proxy_path'], int(2 + k)]

    return proxy_list


def load_add_proxy_file(ini, prox_num):
    files = ini.get('additional_proxy_path', None)
    file = ini.get('additional_proxy_path', None)[prox_num]
    if not file:
        print('No additional proxy files found.')
        return None

    time_col = ini.get('additional_proxy_time_col', [0] * len(files))[prox_num]
    # Check for a split date, year and month
    if ',' in time_col:
        month_col = list(map(str.strip, time_col.split(',')))[1]
        time_col = list(map(str.strip, time_col.split(',')))[0]
    else:
        month_col = None
    proxy_name = ini.get('additional_proxy_name', [None] * len(files))[prox_num]
    proxy_col = ini.get('additional_proxy_data_col', [1] * len(files))[prox_num]
    method = ini.get('additional_proxy_method', [int(ini.get('default_proxy_method', 1))] * len(files))[prox_num]
    seas = ini.get('additional_proxy_seas_comp', [int(ini.get('default_seasonal_component', 2))] * len(files))[prox_num]
    format = ini.get('additional_proxy_time_format', ['%Y%m'] * len(files))[prox_num]
    header_size = ini.get('additional_proxy_header_size', [0] * len(files))[prox_num]
    tag = ini.get('additional_proxy_tag', [False] * len(files))[prox_num]
    tag_values = ini.get('additional_proxy_tag_array', [False] * len(files))[prox_num]

    # Trying to get the proxy name by using the file name
    if proxy_name:
        name = proxy_name
    else:
        name = file.split('/')[-1].split('.')[0]
    proxy = Proxy(name)

    if file.endswith('.nc'):
        dataset = nc.Dataset(file, 'r')
        setattr(proxy, 'data', dataset.variables[proxy_col][:].filled(np.nan))
        dependencies = dataset.variables[proxy_col].dimensions

        if month_col:
            time = pd.Series([parse_time(year, format=format, month=month) for year, month in zip(dataset.variables[time_col][:], dataset.variables[month_col][:])])
        else:
            time = pd.Series([parse_time(year, format=format, month=None) for year in dataset.variables[time_col][:]])
        setattr(proxy, 'time', time)
        if len(dependencies) >= 2:
            setattr(proxy, tag, dataset.variables[dependencies[dependencies.index(tag_values)]][:])
            setattr(proxy, 'tag', tag)

    else:
        proxy_raw = pd.read_csv(file, comment=ini.get('comment_symbol', None), sep='\s+', header=None, skiprows=int(header_size))
        proxy_raw.dropna(axis=1, how='all', inplace=True)
        proxy_raw.index = np.array(proxy_raw)[:, int(time_col)]
        if month_col:
            proxy_raw.index = pd.Series([parse_time(year, format=format, month=month)for year, month in zip(proxy_raw.index.to_series(), pd.Series(np.array(proxy_raw)[:, month_col]))])
        else:
            proxy_raw.index = pd.Series([parse_time(year, format=format, month=None) for year in proxy_raw.index.to_series()])

        if tag:
            tag_values = list(map(float, tag_values.split(',')))
            if len(tag_values) == 3:
                # Create an array depending on the three tag value inputs
                tag_values = np.arange(tag_values[0], tag_values[1] + tag_values[2], tag_values[2])
            proxy_data = np.array(proxy_raw)[:, int(proxy_col):]
            setattr(proxy, tag, tag_values)
            setattr(proxy, 'tag', tag)
        else:
            proxy_data = np.array(proxy_raw)[:, int(proxy_col)]

        proxy.time = pd.Series(proxy_raw.index).apply(lambda dt: dt.replace(day=15))
        proxy.data = proxy_data
        proxy.source = [file, proxy_col]
        proxy.method = method
        proxy.seas_comp = seas

    # If the proxy data is 2 dimensional, reshape the data so the time dimensions is the first
    time_dim_index = proxy.data.shape.index(proxy.time.size)
    if time_dim_index != 0:
        new_order = [time_dim_index] + [i for i in range(proxy.data.ndim) if i != time_dim_index]
        proxy.data = np.transpose(proxy.data, axes=new_order)
    proxy.time = proxy.time.apply(lambda dt: dt.replace(day=15))

    return proxy


def load_additional_proxies(proxies, ini):
    if 'additional_proxy_path' not in ini:
        return proxies
    add_proxies = []
    # Loop over every path in the ini file
    for k, i in enumerate(ini['additional_proxy_path']):
        additional_proxy = load_add_proxy_file(ini, k)
        if additional_proxy == None:
            continue
        add_proxies.append(additional_proxy)

    proxies = proxies + add_proxies

    return proxies


def predict_alt_unit(alt):
    # Predicting the unit of the altitude depending on the scale of the values
    if np.nanmax(alt) >= 10000:
        return 'm'
    elif np.nanmax(alt) < 100:
        return 'km'
    else:
        return 'hPa'


def load_netCDF(filename, ini):
    try:
        dataset = nc.Dataset(filename, 'r')

        group_name = ini.get('group_name')
        group = dataset[group_name] if group_name else dataset

        # Create a dataset class
        try:
            data = Dataset(filename.split('/')[-1].split('.')[0])
        except:
            data = Dataset('New Dataset')

        # Getting the ozone data from the netCDF file
        try:
            setattr(data, 'o3', group.variables[ini.get('o3_var')][:])
        except:
            raise Exception('Loading the variable names from the netCDF file was not successful.')

        # Getting the variables that the ozone data depends on with either the exact variable names or the ones provided by the user (e.g. "time" to "date" or something similar)
        dependencies = group.variables[ini['o3_var']].dimensions
        for k, i in enumerate(dependencies):
            if k == int(ini.get('time_dim', 1)) - 1:
                if ',' in ini.get('time_var', 'time'):
                    # With two variable names in the config.ini, both will be read and combined as strings (year-month)
                    months = np.array(group.variables[list(map(str, ini.get('time_var', 'time').split(',')))[1]][:], dtype=str)
                    years = np.array(group.variables[list(map(str, ini.get('time_var', 'time').split(',')))[0]][:], dtype=str)
                    setattr(data, 'time', years + '-' + months)
                else:
                    setattr(data, 'time', group.variables[ini.get('time_var', 'time')][:])
            else:
                setattr(data, i, group.variables[ini.get('additional_var_' + str(k + 1) + '_index', i)][:])
                setattr(data, i + '_unit', ini.get('additional_var_' + str(k + 1) + '_unit', ''))
                setattr(data, i + '_tag', ini.get('additional_var_' + str(k + 1) + '_tag', ''))

        new_order = [int(ini.get('time_dim', 1)) - 1] + [i for i in range(len(dependencies)) if i != int(ini.get('time_dim', 1)) - 1]
        data.o3 = np.transpose(data.o3, axes=new_order)
        data.o3 = np.ma.masked_invalid(data.o3)
        data.dim_array = [dependencies[i] for i in new_order]
        data.time = convert_to_datetime(data.time, ini)
        data.time_format = ini.get('time_format', '%Y%m')

        dataset.close()
        return data

    except Exception as e:
        print('Error loading NetCDF file:', e)
        return None


def save_netCDF(current_data, trends, signi, diagnostic, ini):
        # Open a file dialog to select the save location
        # save_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "NetCDF Files (*.nc)")
        if 'save_folder_path' not in ini:
            save_path = 'Trends_' + current_data.name
        else:
            save_path = ini['save_folder_path'] + '/Trends_' + current_data.name

        data = current_data
        # If a path was selected, save the file
        if save_path:
            lat = data.lat
            alt = data.lev
            lon = data.lon
            dims = data.dim_array

            with nc.Dataset(save_path + '.nc', 'w') as f:
                if lat is not None:
                    f.createDimension('lat', len(lat))
                    lat_var = f.createVariable('lat', 'f8', ('lat',))
                    lat_var[:] = lat
                    lat_var.units = 'degrees_north'
                    lat_var.long_name = 'latitude'
                if lon is not None:
                    f.createDimension('lon', len(lon))
                    lon_var = f.createVariable('lon', 'f8', ('lon',))
                    lon_var[:] = lon
                    lon_var.units = 'degrees_east'
                    lon_var.long_name = 'longitude'
                if alt is not None:
                    f.createDimension('alt', len(alt))
                    alt_var = f.createVariable('alt', 'f8', ('alt',))
                    alt_var[:] = alt
                    alt_var.units = 'km'
                    alt_var.long_name = 'altitude'

                max_length = max(len(s) for s in diagnostic[3])
                f.createDimension('n_coefficients', len(diagnostic[3]))
                f.createDimension('string_length', max_length)
                f.createDimension('time', len(diagnostic[4]))
                f.createDimension('infl', 2)

                ind_var = f.createVariable('independent_variable_names', 'str', ('n_coefficients',))
                ind_var[:] = np.array(diagnostic[3])

                time_var = f.createVariable('date', 'S10', 'time', compression="zlib")
                time_var.unit = 'YYYYMMDD'
                frac_var = f.createVariable('fractional_year', 'f4', ('time',), compression="zlib")

                dim_tuple = tuple(dim_name for dim_name in dims)
                X_var = f.createVariable('independent_variable_matrix', 'f4', dim_tuple + ('n_coefficients',), compression="zlib")
                X_var[:] = diagnostic[0]
                beta_var = f.createVariable('beta', 'f4', dim_tuple[1:] + ('n_coefficients',), compression="zlib")
                beta_var[:] = diagnostic[2]
                covb_var = f.createVariable('beta_uncertainty', 'f4', dim_tuple[1:] + ('n_coefficients',), compression="zlib")
                covb_var[:] = diagnostic[3]

                if len(trends.shape) == len(dim_tuple):
                    trend_var = f.createVariable('trend', 'f4', dim_tuple[1:] + ('infl',), compression="zlib")
                    sig_var = f.createVariable('trend_uncertainty', 'f4', dim_tuple[1:] + ('infl',), compression="zlib")
                else:
                    trend_var = f.createVariable('trend', 'f4', dim_tuple[1:], compression="zlib")
                    sig_var = f.createVariable('trend_uncertainty', 'f4', dim_tuple[1:], compression="zlib")
                trend_var[:] = trends
                sig_var[:] = signi

                X_var.long_name = 'Independent Variable matrix'
                beta_var.long_name = 'Fit Parameters'

                frac_year = convert_datetime_to_fractional(diagnostic[4])

                time_int = np.array([str_time.strftime('%Y-%m-%d') for str_time in diagnostic[4]])
                time_var[:] = time_int
                frac_var[:] = frac_year

                f.program = 'IUP_regression_model'
                f.version = ver
                f.contact = '''Name: Brian Auffarth\rAffiliation: University of Bremen\rE-mail: brian@iup.physik.uni-bremen.de'''
                f.date_of_creation = dt.datetime.today().strftime('%Y-%m-%d')
                f.configuration_settings = "\n".join([f"{key} = {value}" for key, value in ini.items()])


def is_between(val, low_lim, up_lim):
    if val is None:
        return True
    elif low_lim is not None and up_lim is not None:
        return low_lim <= val <= up_lim
    elif low_lim is not None:
        return low_lim <= val
    elif up_lim is not None:
        return val <= up_lim
    else:
        return True


def get_inflection_index(ini, data):
    # Get the index of the inflection point for the dataset and check if it is in the dataset timeframe
    inflection_index = None
    if 'inflection_point' in ini and 'inflection_method' in ini:
        inflection_date = dt.datetime.strptime(ini['inflection_point'], '%Y-%m').date()
    else:
        return inflection_index

    for k, i in enumerate(data.time.astype(dt.datetime)):
        if i.year == inflection_date.year and i.month == inflection_date.month:
            inflection_index = k
    inflection_index = inflection_index - data.date_start

    return inflection_index


def calc_new_Xstring(X_string, ini):
    # intercept_ind = np.where(np.array(X_string) == 'intercept')[0]
    intercept_ind = [j for j, s in enumerate(np.array(X_string)) if 'intercept' in s]

    new_X_string = []
    size_array = [0, 1, 1, 12]
    method_name = ['disabled', 'single', 'harmonic', 'month-of-the-year']
    seas_name = ['annual', 'semi-annual', 'tri-annual', 'quarter-annual']

    for k, i in enumerate(X_string):
        if k in intercept_ind:
            method = int(ini['intercept_method'])
            seas_comp = int(ini.get('intercept_seasonal_component', ini.get('default_seasonal_component', 2)))
        else:
            method = int(ini['trend_method'])
            seas_comp = int(ini.get('trend_seasonal_component', ini.get('default_seasonal_component', 2)))
        if method == 2:
            for kk in range(size_array[method] + int(seas_comp * 2)):
                new_X_string.append(X_string[k] + ' - ' + method_name[method] + ' ' + seas_name[seas_comp-1] + ' - ' + str(kk + 1))
        else:
            for kk in range(size_array[method]):
                new_X_string.append(X_string[k] + ' - ' + method_name[method] + ' - ' + str(kk + 1))

    return new_X_string


def calc_proxy_size(proxies):
    X_proxy_size = 0
    X_2_string = []
    size_array = [0, 1, 1, 12]
    method_name = ['disabled', 'single', 'harmonic', 'month-of-the-year']
    seas_name = ['annual', 'semi-annual', 'tri-annual', 'quarter-annual']

    for i in proxies:
        X_proxy_size = X_proxy_size + size_array[i.method]
        if i.method == 2:
            X_proxy_size += int(i.seas_comp * 2)
            for k in range(size_array[i.method] + int(i.seas_comp * 2)):
                X_2_string.append(i.name + ' - ' + method_name[i.method] + ' ' + seas_name[i.seas_comp - 1] + ' - ' + str(k + 1))
        else:
            for k in range(size_array[i.method]):
                X_2_string.append(i.name + ' - ' + method_name[i.method] + ' - ' + str(k + 1))

    return X_proxy_size, X_2_string


def default_boundary_settings(proxy_list):
    # proxy_list[0].alt_max = 25000   # Only use ENSO under 25 km; NEEDS A CHANGE TO INCLUDE DIFFERENT ALT UNITS
    # proxy_list[8].alt_max = 25000   # Only use AOD under 25 km; NEEDS A CHANGE TO INCLUDE DIFFERENT ALT UNITS
    proxy_list[4].lat_min = 0       # Only use EHF NH over 0°
    proxy_list[5].lat_max = 0       # Only use EHF SH under 0°
    proxy_list[6].lat_min = 0       # Only use AO over 0°
    proxy_list[7].lat_max = 0       # Only use AAO under 0°

    return proxy_list


def get_X_1(nanmask, ini, X_1_string, data):
    mask_time = np.where(nanmask == True)[0]  # Array which has every index of actual values of the original data

    if 'inflection_method' not in ini:
        X_raw = [1, 0]
    elif ini['inflection_method'] == 'pwl':
        X_raw = [1, 0, 0]
    elif ini['inflection_method'] == 'ind':
        X_raw = [1, 0, 1, 0]
    else:
        raise Exception('The inflection method in the config.ini file is not being recognized. Either use "pwl" for piece-wise linear trends or "ind" for independent trends. If none of these should be used, please delete the inflection method line or comment it out with "#".')

    X_1 = np.zeros((len(nanmask), len(X_1_string)), dtype=float)
    # MULTIPLE INFLECTION POINTS ARE NOT YET SUPPORTED! THE PROGRAM WILL ALWAYS USE THE FIRST INFLECTION POINT

    col = 0
    first_part = True
    for k, i in enumerate(X_raw):
        # Get an array of values (either the intercept values 1 or the ongoing trend values)
        # Depends on the inflection, trend and intercept method
        val = np.zeros(len(nanmask), dtype=float)  # Empty array to be filled with values depending on methods
        if i == 1:  # Rules for intercept column
            seas_comp = int(ini.get('intercept_seasonal_component', ini.get('default_seasonal_component', 2)))
            method = int(ini['intercept_method'])
            if 'inflection_method' not in ini:
                val = 1
            elif ini['inflection_method'] == 'pwl':
                val = 1
            elif ini['inflection_method'] == 'ind':
                if first_part == True:  # UGLY, needs fixing
                    val[:data.inflection_index[0]] = 1
                else:
                    val[data.inflection_index[0]:] = 1

        else:      # Rules for trend column
            seas_comp = int(ini.get('trend_seasonal_component', ini.get('default_seasonal_component', 2)))
            method = int(ini['trend_method'])
            if 'inflection_method' not in ini:
                val = np.arange(1, len(nanmask)+1)
            elif ini['inflection_method'] == 'pwl':
                if first_part == True:
                    val = np.arange(1, len(nanmask)+1)
                    first_part = False
                else:
                    val[data.inflection_index[0]:] = np.arange(1, len(nanmask)-data.inflection_index[0]+1)
            elif ini['inflection_method'] == 'ind':
                if first_part == True:  # UGLY, needs fixing
                    val[:data.inflection_index[0]] = np.arange(1, data.inflection_index[0]+1)
                    first_part = False
                else:
                    val[data.inflection_index[0]:] = np.arange(1, len(nanmask)-data.inflection_index[0]+1)

        if method == 0:
            continue
        elif method == 1:
            X_1[:, col] = val
            col += 1
        elif method == 2:
            X_1[:, col] = val
            col += 1
            for kk in range(int(seas_comp)):
                X_1[:, col] = val * np.sin(((kk + 1) * 2 * np.pi * np.arange(1, len(nanmask)+1))/12)
                col += 1
                X_1[:, col] = val * np.cos(((kk + 1) * 2 * np.pi * np.arange(1, len(nanmask)+1))/12)
                col += 1

        elif method == 3:
            month_array = np.array(pd.to_datetime(data.time[data.date_start:data.date_end]).month)
            for kk in range(12):
                X_1[:, col] = val
                X_1[np.where((month_array % 13) != kk + 1), col] = 0
                col += 1

    X_1[~nanmask, :] = np.nan

    return X_1


def get_X_2(proxies, nanmask, X_proxy_size, it, data):
    mask_time = np.where(nanmask == True)[0]    # Array which has every index of actual values of the original data
    X_2 = np.zeros((len(nanmask), X_proxy_size), dtype=float)  # Size of the proxy part of the X matrices depends on which method to use for each proxy as well as the seasonal cycle
    X_2[:] = np.nan

    col = 0

    # Setting columns as NaNs if they don't fall inbetween the min and max lat and alt specifications of the proxy
    for i in proxies:
        if i.method == 0:
            continue
        # if not is_between(lat, i.lat_min, i.lat_max) or not is_between(alt, i.alt_min, i.alt_max):
        #     if i.method == 1:
        #         X_2[:, col] = np.nan
        #         col += 1
        #     elif i.method == 2:
        #         for kk in range(i.seas_comp*2 + 1):
        #             X_2[:, col] = np.nan
        #             col += 1
        #     elif i.method == 3:
        #         for kk in range(12):
        #             X_2[:, col] = np.nan
        #             col += 1
        #     continue

        # Get the proxy data that correlates to the current data, depending on the tags of the proxy data (e.g. the specific latitude band will be looked at for AOD or an interpolation will be done
        if len(i.data.shape) > 1:
            for kk, ii in enumerate(data.dim_array[1:]):
                if getattr(data, ii + '_tag') == i.tag:
                    tag = i.tag
                    tag_val = getattr(data, ii)[it.multi_index[kk]]
            if tag_val in getattr(i, tag):
                proxy_data = i.data[nanmask, np.where(getattr(i, tag) == tag_val)]
            else:
                closest_val = sorted([(val_close, abs(val_close - tag_val)) for val_close in getattr(i, tag)], key=lambda x: x[1:])[:2]
                val1, val2 = closest_val[0][0], closest_val[1][0]
                data1, data2 = i.data[nanmask, np.where(getattr(i, tag) == val1)[0][0]], i.data[nanmask, np.where(getattr(i, tag) == val2)[0][0]]
                temp_data = np.empty(len(data1))
                for kk, ii in enumerate(data1):
                    temp_data[kk] = np.interp(tag_val, [val1, val2], [data1[kk], data2[kk]])
                proxy_data = temp_data
        else:
            proxy_data = i.data[nanmask]

        if i.method == 0:
            continue
        elif i.method == 1:
            X_2[nanmask, col] = proxy_data
            col += 1
        elif i.method == 2:
            X_2[nanmask, col] = proxy_data
            col += 1
            for kk in range(int(i.seas_comp)):
                X_2[nanmask, col] = proxy_data * np.sin(((kk + 1) * 2 * np.pi * mask_time)/12)
                col += 1
                X_2[nanmask, col] = proxy_data * np.cos(((kk + 1) * 2 * np.pi * mask_time)/12)
                col += 1
        elif i.method == 3:
            month_array = np.array(pd.to_datetime(data.time[data.date_start:data.date_end]).month)
            for kk in range(12):
                X_2[nanmask, col] = proxy_data
                X_2[np.where((month_array % 13) != kk+1), col] = 0
                col += 1

    # Removing all columns with only NaNs (columns that got skipped because of limitations)
    X_2[~nanmask] = np.nan

    return X_2


def normalize(X_2):

    for k in range(X_2.shape[1]):
        current_proxy = X_2[X_2[:, k] != 0, k]
        X_2[X_2[:, k] != 0, k] = ((current_proxy - np.nanmin(current_proxy)) / (np.nanmax(current_proxy) - np.nanmin(current_proxy)))*2 - 1

    return X_2


def calc_trend(X_clean, data_arr, ini, X_string, inflection_index):
    nanmask = ~np.isnan(data_arr.filled(np.nan))

    # Get the indices of the intercept and trend to get a mean value for the coefficient
    trend_string_index = [j for j, s in enumerate(X_string) if 'trend' in s]
    groups = get_string_groups(X_string)
    # trend_index = trend_string_index[0]     # To get the first trend index so that the autoregression works

    try:
        beta = np.linalg.inv(X_clean.T @ X_clean) @ X_clean.T @ data_arr[nanmask]
    except:
        print('Calculation failed: NaNs')
        return [np.nan] * len(trend_string_index), [np.nan] * len(trend_string_index), np.nan, np.nan, np.nan

    # Carlos autoregression program, not yet completely reworked

    fity = np.matmul(X_clean, beta)
    N = data_arr[nanmask] - fity  # what I cosider the error matrix N

    k, sumN = 1, 0
    for t in range(len(nanmask))[1:]:
        if nanmask[t - 1] == False or nanmask[t] == False:  # it means that before there was a gap or I am in a gap (and N is not def for gaps)
            continue
        else:
            sumN = sumN + (N[k] * N[k - 1])
            k += 1
    phi = (1.0 / np.var(N)) * (sumN / (len(data_arr[nanmask]) - 1))  # autocorrelation estimator excluding gaps

    P, epsilon = np.zeros((len(data_arr[nanmask]), len(data_arr[nanmask]))), np.zeros((len(data_arr[nanmask])))
    for i in range(len(X_clean))[1:]:  # I am starting from the second line
        for g in range(len(X_clean)):
            if i == g:
                if X_clean[i, 1] - X_clean[i - 1, 1] > 1:
                    P[i, g] = np.sqrt(1 - phi ** 2)
                    epsilon[i] = N[i] * np.sqrt(1 - phi ** 2)
                else:
                    P[i, g] = 1
                    epsilon[i] = N[i] - phi * N[i - 1]
            elif i == g + 1:
                if X_clean[i, 1] - X_clean[i - 1, 1] > 1:
                    P[i, g] = 0
                else:
                    P[i, g] = -phi
    P[0, 0] = np.sqrt(1 - phi ** 2)  # this is the first line
    epsilon[0] = N[0] * np.sqrt(1 - phi ** 2)

    Xstar = np.matmul(P, X_clean)
    Ystar = np.matmul(P, data_arr[nanmask])
    try:
        betaa = np.linalg.inv(Xstar.T @ Xstar) @ Xstar.T @ Ystar
        covbetaa = np.var(epsilon) * (np.linalg.inv(np.matmul(np.transpose(Xstar), Xstar)))
    except:
        print('Two or more proxies are dependent to each other. A linear regression is not possible. Please either turn of linear regression or turn off one of the proxies.')
        return np.nan, np.nan, np.nan, np.nan, np.nan

    Xmask2, Ymask2 = np.zeros((len(X_clean), X_clean.shape[1])), np.zeros((len(X_clean)))
    count = 0
    timok = list()
    comb_trend_col = np.array([np.nanmax(row[trend_string_index]) for row in X_clean])        # A combined column of all trend columns, for better comparison of consecutive values
    if inflection_index[0]:
        continuity_jumps = [inflection_index[i] - sum(inflection_index[:i]) for i in range(len([inflection_index]))]        # A list of indices at which the continuity will jump back to 1
    else:
        continuity_jumps = []
    jump_num = 0

    for k, i in enumerate(comb_trend_col):
        if k == 0:
            Xmask2[count, 0:len(Xstar[k, :])] = Xstar[k, :]
            Ymask2[count] = Ystar[k]
            count += 1
            timok.append(k)
            continue
        if i - comb_trend_col[k - 1] == 1:
            Xmask2[count, 0:len(Xstar[k, :])] = Xstar[k, :]
            Ymask2[count] = Ystar[k]
            count += 1
            timok.append(k)
        elif jump_num >= len(continuity_jumps):
            continue    # if all inflection points were already found, then the program will not look for another one
        elif comb_trend_col[k - 1] == continuity_jumps[jump_num] and i == 1:
            Xmask2[count, 0:len(Xstar[k, :])] = Xstar[k, :]
            Ymask2[count] = Ystar[k]
            count += 1
            timok.append(k)
            jump_num += 1
        else:
            # print('gap in X1, ', k, i)
            continue

    Xmask2ok = Xmask2[0:k, :]

    mult = 1
    if ini.get('o3_var_unit', '').split('_')[0] == 'anom':
        mult *= 1
    else:
        mult *= 100 / np.nanmean(data_arr)
    if ini.get('averaging_window', None):
        mult *= 10
    else:
        mult *= 120

    # Calculate the trend coefficients
    try:
        if len(beta) == 1 or len(Xmask2ok) < 10:
            trenda_z = [np.nan] * len(trend_string_index)
            siga_z = [np.nan] * len(trend_string_index)
        else:
            if ini.get('anomaly', '') == 'True' and ini.get('anomaly_method', 'rel') == 'rel':
                trenda_z = np.nanmean(betaa[trend_string_index]) * 120 * 100
                siga_z = np.abs(np.nanmean(betaa[trend_string_index]) / np.sqrt(np.nanmean(np.diag(covbetaa)[trend_string_index])))
            elif ini.get('anomaly', '') == 'True' and ini.get('anomaly_method', 'abs') == 'rel':
                print('NOT YET FINISHED')
            else:
                trenda_z = []
                siga_z = []
                for keys, indices in groups.items():
                    if keys[0] == 'intercept':
                        continue
                    if keys[1] == 'month-of-the-year':
                        trenda_z.append(np.nanmean(betaa[indices]) * mult)
                        siga_z.append(np.abs(betaa[indices[0]] / np.sqrt(np.diag(covbetaa)[indices[0]])))
                    else:
                        trenda_z.append(betaa[indices[0]] * mult)
                        siga_z.append(np.abs(betaa[indices[0]] / np.sqrt(np.diag(covbetaa)[indices[0]])))
                # siga_z = np.abs(betaa[trend_string_index] / np.sqrt(np.diag(covbetaa)[trend_string_index])) if len(trend_string_index) == 1 else [np.abs(betaa[i] / np.sqrt(np.diag(covbetaa)[i])) for i in trend_string_index]
                # trenda_z = betaa[trend_string_index] * mult if len(trend_string_index) == 1 else [betaa[i] * mult for i in trend_string_index]

    except:
        trenda_z = [np.nan] * len(trend_string_index)
        siga_z = [np.nan] * len(trend_string_index)
        print('Failed to calculate the trend and significants')

    if len(trenda_z) == 1:
        return trenda_z.pop(), siga_z.pop(), beta, betaa, np.diag(covbetaa)
    else:
        return np.array(trenda_z), np.array(siga_z), beta, betaa, np.diag(covbetaa)



# Main program to run
def iup_reg_model(data, proxies, ini):
    data, proxies = get_proxy_time_overlap(ini, proxies, data)
    data = set_data_limits(data, ini)

    # Get index of the inflection point
    data.inflection_index = get_inflection_index(ini, data)
    if not isinstance(data.inflection_index, list):
        data.inflection_index = [data.inflection_index]

    # Creating the empty arrays for the trends and the uncertainty
    if 'inflection_method' not in ini:
        trenda_z = np.empty(np.atleast_1d(data.o3[0, ...]).shape) * np.nan
        siga_z = np.empty(np.atleast_1d(data.o3[0, ...]).shape) * np.nan
        X_string = ['intercept', 'trend']
    elif ini['inflection_method'] == 'pwl':
        trenda_z = np.empty(np.atleast_1d((data.o3[0, ...] + (2,))).shape) * np.nan
        siga_z = np.empty(np.atleast_1d((data.o3[0, ...] + (2,))).shape) * np.nan
        X_string = ['intercept', 'piece-wise linear trend #1', 'piece-wise linear trend #2']
    elif ini['inflection_method'] == 'ind':
        trenda_z = np.empty(np.atleast_1d((data.o3[0, ...] + (2,))).shape) * np.nan
        siga_z = np.empty(np.atleast_1d((data.o3[0, ...] + (2,))).shape) * np.nan
        X_string = ['intercept #1', 'independent trend #1', 'intercept #2', 'independent trend #2']

    # Expand dimension of trends and uncertainties, depending on number of inflection points
    if data.inflection_index[0]:
        trenda_z = np.expand_dims(trenda_z, axis=-1)
        trenda_z = np.tile(trenda_z, (1,) * (trenda_z.ndim - 1) + (len(data.inflection_index) + 1,))
        siga_z = np.expand_dims(siga_z, axis=-1)
        siga_z = np.tile(siga_z, (1,) * (siga_z.ndim - 1) + (len(data.inflection_index) + 1,))

    ini['trend_method'] = ini.get('trend_method', 1)
    ini['intercept_method'] = ini.get('intercept_method', 1)

    # check how the data should be averaged
    check = averaging_window_text_check(ini.get('averaging_window', ''))
    anom_check = ini.get('anomaly', 'False')
    time = pd.DatetimeIndex(data.time[data.date_start:data.date_end])
    time_log = np.unique(time.year, return_index=True)[1] if check != 0 else slice(None)

    # Creating new X_string depending on method used for trend and intercept
    X_1_string = calc_new_Xstring(X_string, ini)

    # Get size of the X matrices by either not using proxies or using proxies with different methods
    X_proxy_size, X_2_string = calc_proxy_size(proxies)

    X_string = X_1_string + X_2_string
    groups = get_string_groups(X_string)

    if check == 0:
        X_all = np.full((data.o3[data.date_start:data.date_end, ...].shape + (len(X_string),)), np.nan, dtype='f4')
    elif check == 1:
        X_all = np.full(((len(np.unique(time.year)),) + data.o3[0, ...].shape + (len(X_string),)), np.nan, dtype='f4')
        for i in proxies:
            for kk, ii in enumerate(np.unique(time.year)):
                if len(np.nonzero(i.data[np.where(time.year == ii)])[0]) / len(np.where(time.year == ii)[0]) <= float(ini.get('skip_percentage', 0.75)):
                    i.data[kk] = np.nan
                    continue
                i.data[kk] = np.nanmean(i.data[np.where(time.year == ii)])
            i.data = i.data[:len(np.unique(time.year))]
        if getattr(data, 'inflection_index', None)[0]:
            for k, i in enumerate(data.inflection_index):
                data.inflection_index[k] = np.where(np.unique(time.year) == time[i].year)[0][0]  # Change inflection point to reflect the yearly data
    elif check == 2:
        month_index = re.split(r',\s*', ini.get('averaging_window', ''))
        month_index = np.array([int(num) for num in month_index])
        X_all = np.full(((len(np.unique(time.year)),) + data.o3[0, ...].shape + (len(X_string),)), np.nan, dtype='f4')
        for i in proxies:
            for kk, ii in enumerate(np.unique(time.year)):
                if kk * 12 > len(time):
                    break
                elif len(np.arange((kk * 12), min((kk * 12) + 12, len(time)), 1)) / len(month_index) <= float(ini.get('skip_percentage', 0.75)):
                    i.data[kk] = np.nan
                    continue
                i.data[kk] = np.nanmean(i.data[np.arange((kk * 12), min((kk * 12) + 12, len(time)), 1)])
            i.data = i.data[:len(np.unique(time.year))]

            # for kk, ii in enumerate(np.unique(time.year)):
            #     if len(np.in1d(time[time.year == ii].month, month_index).nonzero()[0])/len(month_index) <= 0.8:     # If there are less than 80% of the values in this year, skip it
            #         i.data[kk] = np.nan
            #         continue
            #     i.data[kk] = np.nanmean(i.data[np.where(time.year == ii)][np.in1d(time[time.year == ii].month, month_index)])
            # i.data = i.data[:len(np.unique(time.year))]
        if getattr(data, 'inflection_index', None)[0]:
            for k, i in enumerate(data.inflection_index):
                data.inflection_index[k] = np.where(np.unique(time.year) == time[i].year)[0][0]      # Change inflection point to reflect the yearly data
    beta_all = np.empty((data.o3[0, ...].shape + (len(X_string),)), dtype='f4') * np.nan
    betaa_all = np.empty((data.o3[0, ...].shape + (len(X_string),)), dtype='f4') * np.nan
    data_all = np.empty(X_all.shape[:-1])

    # Looping over every dimension but the first (time), to calculate the trends for every latitude, longitude and altitude
    it = np.nditer(data.o3[0, ...], flags=['multi_index'])

    while not it.finished:
        print(str(it.multi_index) + ': calculating trend')

        data_arr = data.o3[(slice(None),) + it.multi_index]
        data_arr = data_arr[data.date_start:data.date_end]

        if check == 0 and anom_check == 'True':
            for k in range(12):
                if ini.get('anomaly_method', 'rel') == 'abs':
                    data_arr[time.month == k + 1] = data_arr[time.month == k + 1] - np.nanmean(data_arr[time.month == k + 1].filled(np.nan))
                else:
                    data_arr[time.month == k + 1] = (data_arr[time.month == k + 1] - np.nanmean(data_arr[time.month == k + 1].filled(np.nan))) / np.nanmean(data_arr[time.month == k + 1].filled(np.nan))
        elif check == 1:
            for k, i in enumerate(np.unique(time.year)):
                if len(np.nonzero(data_arr[np.where(time.year == i)])[0]) / len(np.where(time.year == i)[0]) <= float(ini.get('skip_percentage', 0.75)):
                    data_arr[k] = np.nan
                    continue
                data_arr[k] = np.nanmean(data_arr[np.where(time.year == i)])
            data_arr = data_arr[:len(np.unique(time.year))]
            if anom_check == 'True':
                if ini.get('anomaly_method', 'rel') == 'abs':
                    data_arr = data_arr - np.nanmean(data_arr)
                else:
                    data_arr = (data_arr - np.nanmean(data_arr)) / np.nanmean(data_arr)
        elif check == 2:
            for k, i in enumerate(np.unique(time.year)):
                time_index = np.arange((k * 12), min((k * 12) + 12, len(time)), 1)
                if len(data_arr[time_index][np.in1d(time[time_index].month, month_index)].nonzero()[0]) / len(month_index) <= float(ini.get('skip_percentage', 0.75)):
                    data_arr[k] = np.nan
                    continue
                data_arr[k] = np.nanmean(data_arr[time_index][np.in1d(time[time_index].month, month_index)])

            data_arr = data_arr[:len(np.unique(time.year))]
            if anom_check == 'True':
                if ini.get('anomaly_method', 'rel') == 'abs':
                    data_arr = data_arr - np.nanmean(data_arr)
                else:
                    data_arr = (data_arr - np.nanmean(data_arr)) / np.nanmean(data_arr)

        nanmask = ~np.isnan(data_arr.filled(np.nan))
        mask_time = np.where(nanmask == True)[0]

        # Inquery if there are enough datapoints to even calculate a trend
        if len(mask_time) / len(nanmask) < float(ini.get('skip_percentage', 0.75)):
            print('Not enough values to compute the trend! ' + f'{len(mask_time) / len(nanmask)*100:.2f}' + '% of data available.')
            it.iternext()
            continue

        X_1 = get_X_1(nanmask, ini, X_1_string, data)
        X_2 = get_X_2(proxies, nanmask, X_proxy_size, it, data)

        X = np.concatenate([X_1, X_2], axis=1)
        X[:, np.all(X[nanmask] == 0, axis=0)] = np.nan

        # Only use the X matrix without empty rows and columns
        X[:, np.all(X[nanmask] == 0, axis=0)] = np.nan  # This changes the rows with only 0 and NaNs to only NaN rows
        for k in range(len(X_string)):
            nonzerosum = np.sum((X[:, k] != 0) & ~np.isnan(X[:, k]))
            if nonzerosum <= 2:
                X[:, k] = np.nan
        row_mask = np.isnan(X).all(axis=1)
        col_mask = np.isnan(X).all(axis=0)
        X_clean = X[~row_mask][:, ~col_mask]
        X_clean[np.isnan(X_clean)] = 0

        # Normalize
        X_clean[:, len(X_1_string):] = normalize(X_clean[:, len(X_1_string):])
        # Calculation of the trends and uncertainties for each cell
        trenda_z[it.multi_index], siga_z[it.multi_index], beta, betaa, covbetaa = calc_trend(X_clean, data_arr, ini, np.array(X_string)[~np.all(np.isnan(X), axis=0)], data.inflection_index)

        # Save X, beta and betaa
        X_all[(slice(None),) + it.multi_index + (slice(None),)][np.ix_(~row_mask, ~col_mask)] = X_clean
        beta_all[it.multi_index + (slice(None),)][~col_mask] = beta
        betaa_all[it.multi_index + (slice(None),)][~col_mask] = betaa
        data_all[(slice(None),) + it.multi_index] = data_arr.filled(np.nan)
        # Go to next iteration:
        it.iternext()

    diagnostic = [X_all, beta_all, betaa_all, data.dim_array, X_string, data.time[data.date_start:data.date_end][time_log], data_all]

    return trenda_z, siga_z, diagnostic


# How to load data and proxies into the model:
# Load the config.ini from the correct path
# ini = load_config_ini('config.ini')

# Load netCDF data file
# data = load_netCDF(ini['data_path', ini)

# Or load the data from pyton values
# data = load_data(ini, lat=data.lat, lon=None, alt=data.lev, time=data.time, atmo_parameter=data.o3, name=data.name)

# Load the default proxies for the timeframe of the data
# proxies = load_default_proxies(ini)

# Add additional proxies
# proxies = load_additional_proxies(proxies, ini)

# Deciding which of the provided proxies to use and how to use them (Harmonic, Month-of-the-year).
# Proxies are innately used in the model unless specificly turned off
# proxies[4].method = 0 would disable the fifth proxy
# proxies[0].method = 1 would enable the first proxy (normally enabled)
# proxies[-1].method = 2 would enable the last added proxy with harmonic components
# proxies[3].method = 3 would enable the fourth proxy with monthly components

# Putting the proxies, the data and the config.ini into the module will give out the trends as well as the significant values, and a list of data that consists of the X matrix, beta and betaa values, the proxy names and the time series for the proxies
# trends, signi, diagnostic = iup_reg_model(data, proxies, ini)

def iup_ui(ui=False, config='config.ini'):

    # Console Arguments
    parser = argparse.ArgumentParser(description="The IUP Regression Model can compute trends from different .netCDF ozone files with a range of default proxies aswell as the option to include additional proxies.")
    parser.add_argument('-u', '--ui', action='store_true', help='Run the IUP Regression Model with a graphical user interface.')
    parser.add_argument('-c', '--config', type=str, help='Specify a configuration file for the regression model.')
    args = parser.parse_args()
    if args.ui:
        ui = True

    if args.config:
        config = args.config

    if not ui:
        ini = load_config_ini('config folder/' + config)
        data = load_netCDF(ini['data_path'], ini)
        proxies = load_default_proxies(ini)
        proxies = load_additional_proxies(proxies, ini)
        trends, signi, diagnostic = iup_reg_model(data, proxies, ini)
        save_netCDF(data, trends, signi, diagnostic, ini)
    else:
        app = QtWidgets.QApplication(sys.argv)
        Window = AppWindow()
        Window.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    iup_ui()
