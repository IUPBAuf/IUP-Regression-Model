import argparse
import sys
import os

import numpy as np
import pandas as pd
import copy
import netCDF4 as nc
import datetime as dt
import re

import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib
import matplotlib.patheffects as pe
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
from cmcrameri import cm
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.ticker import (MultipleLocator, AutoMinorLocator)
from statsmodels.stats.stattools import durbin_watson

from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QPalette, QColor, QIcon
from PyQt5.QtCore import pyqtSignal, QTimer, Qt
from PyQt5.QtWidgets import QTableWidgetItem, QVBoxLayout, QHBoxLayout, QHeaderView, QFileDialog, QMessageBox
# from regression_model_ui import Ui_MainWindow

ver = 'alpha 1.10'

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


class SavePlotWindow(QtWidgets.QDialog):
    def __init__(self, original_size, parent=None):
        super(SavePlotWindow, self).__init__()
        uic.loadUi('save_plot.ui', self)
        self.width_line.setText(str(original_size[0]))
        self.height_line.setText(str(original_size[1]))

        self.btn_cancel.clicked.connect(self.close)
        self.btn_save.clicked.connect(self.accept)

    def get_options(self):
        try:
            size = (float(self.width_line.text()), float(self.height_line.text()))
        except:
            size = False
        include_title = self.radio_with.isChecked()
        return size, include_title


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

        o3_ln = getattr(self.data.variables[self.o3_var_combo.currentText()], 'long_name', getattr(self.data.variables[self.o3_var_combo.currentText()], 'name', ''))
        o3_units = getattr(self.data.variables[self.o3_var_combo.currentText()], 'units', '')
        if o3_ln or o3_units:
            self.o3_unit.setText(o3_ln + ' [' + o3_units + ']')

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

            # Add widget with unit input
            row_widget = QtWidgets.QWidget()
            row_layout = QHBoxLayout(row_widget)
            label = QtWidgets.QLabel(i + ' unit: ')
            row_layout.addWidget(label)
            spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            row_layout.addItem(spacer)
            unit_line = QtWidgets.QLineEdit()
            try:
                ln = getattr(self.data.variables[i], 'long_name', getattr(self.data.variables[i], 'name', ''))
                units = getattr(self.data.variables[i], 'units', '')
                if ln or units:
                    unit_line.setText(ln + ' [' + units + ']')
            except:
                unit_line.setText('')
            row_layout.addWidget(unit_line)
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
        var_name = self.sender().currentText()

        if self.sender().parent():
            ln = getattr(self.data.variables[var_name], 'long_name', getattr(self.data.variables[var_name], 'name', ''))
            units = getattr(self.data.variables[var_name], 'units', '')
            if ln or units:
                self.sender().parent().parent().layout().itemAt(1).widget().layout().itemAt(2).widget().setText(ln + ' [' + units + ']')

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
            if self.sender().parent().parent().layout().itemAt(3):
                self.sender().parent().parent().layout().removeWidget(self.sender().parent().parent().layout().itemAt(3).widget())

    def save_settings(self):
        # Saves all settings and closes the settings window

        # Change ini
        if self.o3_var_combo.currentIndex() != 0:
            self.ini['o3_var'] = self.o3_var_combo.currentText()
            self.ini['o3_var_unit'] = self.o3_unit.text()
        else:
            self.ini['o3_var'] = None

        for i in range(self.dim_layout.count()):
            combo_text = self.dim_layout.itemAt(i).widget().layout().itemAt(0).widget().layout().itemAt(2).widget().currentText()
            unit_text = self.dim_layout.itemAt(i).widget().layout().itemAt(1).widget().layout().itemAt(2).widget().text()
            line_text = self.dim_layout.itemAt(i).widget().layout().itemAt(2).widget().layout().itemAt(2).widget().text()

            if line_text == 'time':
                self.ini['time_var'] = combo_text
                self.ini['time_dim'] = i + 1
                self.ini['time_format'] = self.dim_layout.itemAt(i).widget().layout().itemAt(3).widget().layout().itemAt(2).widget().text()
            else:
                self.ini['additional_var_' + str(i + 1) + '_index'] = combo_text
                self.ini['additional_var_' + str(i + 1) + '_tag'] = line_text
                self.ini['additional_var_' + str(i + 1) + '_unit'] = unit_text

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
        self.all_proxy_method.currentIndexChanged.connect(self.all_proxy_method_change)
        self.mean_line.textChanged.connect(self.text_check)
        self.anomaly_check.toggled.connect(self.anomaly_enable)
        self.radio_rel.toggled.connect(self.anomaly_method_toggle)
        self.radio_abs.toggled.connect(self.anomaly_method_toggle)
        self.preset_combo.currentIndexChanged.connect(self.change_preset)
        self.data_list.currentItemChanged.connect(self.data_change)
        self.data_list.itemChanged.connect(self.data_name_change)
        self.inflection_boxes = []
        self.update_inflection_boxes(1)

        # Diagnostic UI functions
        self.dia_proxy_combo.currentIndexChanged.connect(self.proxy_diagnostic)
        self.dia_proxy_table.itemChanged.connect(self.dia_proxy_change)
        self.proxy_dim_reset.clicked.connect(self.proxy_reset_dataset)
        self.dim_data_layout = self.data_dim_widget.layout()
        self.dim_data_boxes = []
        self.dia_data_combo.currentIndexChanged.connect(self.populate_data_dim_widget)
        self.add_data_dia()
        self.dia_data_table.itemChanged.connect(self.dia_data_change)
        self.data_dim_reset.clicked.connect(self.data_dim_reset_dataset)
        self.dim_X_layout = self.X_dim_widget.layout()
        self.dim_X_boxes = []

        # Start trend analysis
        self.compute_button.clicked.connect(self.compute_trends)

        # Plotting Model
        self.dim_model_layout = self.dim_model_widget.layout()
        self.dim_model_boxes = []
        self.plot_button_model.clicked.connect(self.plot_model_figure)
        self.model_layout = QVBoxLayout(self.model_fig_widget)
        self.model_canvas = MplCanvas(self.model_fig_widget)
        self.model_layout.addWidget(self.model_canvas)
        self.model_toolbar = NavigationToolbar(self.model_canvas, self.model_fig_widget)
        self.model_layout.addWidget(self.model_toolbar)

        # Plotting Contour
        self.dim_con_layout = self.dim_con_widget.layout()
        self.dim_con_boxes = []
        self.plot_button_con.clicked.connect(self.plot_contour_figure)
        self.con_layout = QVBoxLayout(self.contour_fig_widget)
        self.con_canvas = MplCanvas(self.contour_fig_widget)
        self.con_layout.addWidget(self.con_canvas)
        self.con_toolbar = NavigationToolbar(self.con_canvas, self.contour_fig_widget)
        self.con_layout.addWidget(self.con_toolbar)

        # Plotting Residuals
        self.dim_resi_layout = self.dim_resi_widget.layout()
        self.dim_resi_boxes = []
        self.plot_button_resi.clicked.connect(self.plot_resi_figure)
        self.resi_layout = QVBoxLayout(self.resi_fig_widget)
        self.resi_canvas = MplCanvas(self.resi_fig_widget)
        self.resi_layout.addWidget(self.resi_canvas)
        self.resi_toolbar = NavigationToolbar(self.resi_canvas, self.resi_fig_widget)
        self.resi_layout.addWidget(self.resi_toolbar)

        # Plotting Measurement Density
        self.dim_cell_layout = self.dim_cell_widget.layout()
        self.dim_cell_boxes = []
        # self.plot_button_cell.clicked.connect(self.plot_observations_figure)
        self.cell_layout = QVBoxLayout(self.cell_fig_widget)
        self.cell_canvas = MplCanvas(self.cell_fig_widget)
        self.cell_layout.addWidget(self.cell_canvas)

        # Plotting Proxies
        self.dim_proxy_layout = self.dim_proxy_widget.layout()
        self.dim_proxy_layout_checks = self.dim_proxy_widget_checks.layout()
        self.dim_proxy_boxes = []
        self.dim_proxy_checks = []
        self.plot_button_proxy.clicked.connect(self.plot_proxy_figure)
        self.proxy_layout = QVBoxLayout(self.proxy_fig_widget)
        self.proxy_canvas = MplCanvas(self.proxy_fig_widget)
        self.proxy_layout.addWidget(self.proxy_canvas)
        self.proxy_toolbar = NavigationToolbar(self.proxy_canvas, self.proxy_fig_widget)
        self.proxy_layout.addWidget(self.proxy_toolbar)

        # Plotting Proxy Contour
        self.dim_proxy_con_layout = self.dim_proxy_con_widget.layout()
        self.dim_proxy_con_boxes = []
        self.plot_button_proxy_con.clicked.connect(self.plot_proxy_con_figure)
        self.proxy_con_layout = QVBoxLayout(self.proxy_con_fig_widget)
        self.proxy_con_canvas = MplCanvas(self.proxy_con_fig_widget)
        self.proxy_con_layout.addWidget(self.proxy_con_canvas)
        self.proxy_con_toolbar = NavigationToolbar(self.proxy_con_canvas, self.proxy_con_fig_widget)
        self.proxy_con_layout.addWidget(self.proxy_con_toolbar)

        # Menu button connection
        self.menu_help.triggered.connect(self.print_ini)
        self.menu_load_data.triggered.connect(self.open_data_dialog)
        self.menu_load_proxy.triggered.connect(self.open_proxy_dialog)
        self.menu_save.triggered.connect(self.save_file)
        self.menu_save_plot.triggered.connect(self.save_plot)

        self.frozen_list.horizontalHeader().sectionResized.connect(self.sync_frozen_to_main)

        # Load ini settings and input the data into the UI
        self.load_ini_settings()
        QTimer.singleShot(0, self.sync_tables)

    def load_ini_settings(self):

        if 'inflection_point' in self.ini:
            parts = [p.strip() for p in str(self.ini['inflection_point']).split(',')]
            for p in parts:
                dt.datetime.strptime(p, '%Y-%m')
            date = ', '.join(dt.datetime.strptime(p, '%Y-%m').strftime('%Y-%m') for p in parts)

            self.inflection_point.setText(date)
        else:
            self.inflection_point.setText('YYYY-MM')

        if 'inflection_point' in self.ini and 'inflection_method' in self.ini:
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
            dims = data.dim_array

            with nc.Dataset(save_path + '.nc', 'w') as f:
                var_list = []
                for k, dim_name in enumerate(dims[1:]):
                    dim_values = getattr(data, dim_name)

                    f.createDimension(dim_name, len(dim_values))

                    if isinstance(dim_values[0], str):
                        # Save string array as 1D variable using 'str' dtype
                        var = f.createVariable(dim_name, str, (dim_name,))
                        var[:] = np.array(dim_values, dtype='str')
                    else:
                        var = f.createVariable(dim_name, 'f8', (dim_name,))
                        var[:] = dim_values

                    var_list.append(var)

                max_length = max(len(s) for s in self.proxy_string)
                f.createDimension('n_coefficients', len(self.proxy_string))
                f.createDimension('string_length', max_length)
                f.createDimension('time', len(self.time))
                f.createDimension('infl', len(self.current_ini['inflection_method']) - self.current_ini.get('inflection_method', '').count('gap'))

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
                og_ozone = f.createVariable('ozone_time_series', 'f4', dim_tuple, compression="zlib")
                og_ozone[:] = self.trend_data

                if len(self.trends.shape) == len(dim_tuple):
                    trend_var = f.createVariable('trend', 'f4', dim_tuple[1:] + ('infl',))
                    sig_var = f.createVariable('significance', 'f4', dim_tuple[1:] + ('infl',))
                    uncer_var = f.createVariable('trend_uncertainty', 'f4', dim_tuple[1:] + ('infl',))
                else:
                    trend_var = f.createVariable('trend', 'f4', dim_tuple[1:])
                    sig_var = f.createVariable('significance', 'f4', dim_tuple[1:])
                    uncer_var = f.createVariable('trend_uncertainty', 'f4', dim_tuple[1:])

                trend_var[:] = self.trends
                sig_var[:] = self.signi
                uncer_var[:] = self.uncertainty

                X_var.long_name = 'Independent Variable matrix'
                beta_var.long_name = 'Fit Parameters'
                og_ozone.long_name = 'Original Ozone Time Series'
                og_ozone.unit = self.current_ini.get("o3_var_unit", "")

                frac_year = convert_datetime_to_fractional(self.time)

                time_int = np.array([str_time.strftime('%Y-%m-%d') for str_time in self.time])
                time_var[:] = time_int
                frac_var[:] = frac_year

                f.program = 'IUP_regression_model'
                f.version = ver
                f.contact = '''Name: Brian Auffarth\rAffiliation: University of Bremen\rE-mail: brian@iup.physik.uni-bremen.de'''
                f.date_of_creation = dt.datetime.today().strftime('%Y-%m-%d')
                f.configuration_settings = "\n".join([f"{key} = {value}" for key, value in self.ini.items()])

    def save_plot(self):
        canvas = self.figure_tabs.widget(self.figure_tabs.currentIndex()).findChild(FigureCanvas)
        if canvas:
            if not canvas.figure.axes:
                print('Canvas is empty. Please plot something before saving.')
                return
            save_path, _ = QFileDialog.getSaveFileName(self, "Save Figure", canvas.figure.axes[0].get_title().replace('\n', ' ') + '.png', "PNG Files (*.png);;All Files (*)")
            if save_path:
                original_size = tuple(canvas.figure.get_size_inches())
                dialog = SavePlotWindow(original_size, self)
                if dialog.exec_() == QtWidgets.QDialog.Accepted:
                    fig_size, include_title = dialog.get_options()
                    if not fig_size:
                        return
                else:
                    return  # User canceled the operation
                canvas.figure.set_size_inches(fig_size)
                original_title = canvas.figure.axes[0].get_title()
                if not include_title:
                    canvas.figure.axes[0].set_title('')
                self.model_canvas.figure.tight_layout()
                canvas.figure.savefig(save_path, dpi=300)
                canvas.figure.set_size_inches(original_size)
                canvas.figure.axes[0].set_title(original_title)
                self.model_canvas.figure.tight_layout()

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

        accepted = self.open_data_settings_dialog(fileName)
        if not accepted:
            return

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
        result = var_window.exec_()
        return result == QtWidgets.QDialog.Accepted

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
            item = QtWidgets.QListWidgetItem(i.name)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.data_list.addItem(item)

        # Select last item
        self.data_list.setCurrentItem(self.data_list.item(self.data_list.count() - 1))

        self.add_data_dia()

    def data_name_change(self, item):
        new_name = item.text()
        index = self.data_list.row(item)
        self.list_of_data[index].name = new_name

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
        infl_list = ['ind', 'pwl', 'gap']
        # Enables/Disables the date entry
        if self.infl_check.isChecked() == True:
            self.inflection_point.setEnabled(True)
            # self.inflection_method.setEnabled(True)
            layout = self.inflection_widget.layout()
            if layout is None:
                return
            infl_string = []
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if isinstance(widget, QtWidgets.QComboBox):
                    widget.setEnabled(True)
                infl_string.append(infl_list[widget.currentIndex()])
            self.ini['inflection_method'] = ', '.join(infl_string)
            # self.ini['inflection_method'] = self.infl_method_list[self.inflection_method.currentIndex()]
            self.ini['inflection_point'] = self.inflection_point.text()
        else:
            self.inflection_point.setEnabled(False)
            self.ini.pop('inflection_point', None)
            # self.inflection_method.setEnabled(False)
            layout = self.inflection_widget.layout()
            if layout is None:
                return
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if isinstance(widget, QtWidgets.QComboBox):
                    widget.setEnabled(False)
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

    def update_inflection_boxes(self, count):
        layout = self.inflection_widget.layout()
        # Remove extra boxes
        while len(self.inflection_boxes) > count:
            box = self.inflection_boxes.pop()
            layout.removeWidget(box)
            box.deleteLater()

        # Add missing boxes
        while len(self.inflection_boxes) < count:
            index = len(self.inflection_boxes) + 1
            box = QtWidgets.QComboBox()
            box.setObjectName(f'inflection_method_{index}')
            box.addItems(['Independent Trend', 'Piece-wise Linear trend', 'Gap'])
            box.currentIndexChanged.connect(self.inflection_method_change)

            layout.addWidget(box)
            self.inflection_boxes.append(box)

    def format_check(self):
        # Changes the checkmarks if the format of the date is being recongnized
        checkbox = getattr(self, 'check_' + str(self.sender().objectName()).split('_')[0], None)

        if str(self.sender().text()) == '':
            checkbox.setChecked(False)
            checkbox.setPalette(self.palette_wrong)
            self.ini.pop(self.sender().objectName(), None)
            return
        try:
            if self.sender().objectName() == 'inflection_point':
                parts = [p.strip() for p in str(self.sender().text()).split(',')]
                for p in parts:
                    dt.datetime.strptime(p, '%Y-%m')    # Raises an error and goes out of the try case, if not in the correct format
                date_check = ', '.join(dt.datetime.strptime(p, '%Y-%m').strftime('%Y-%m') for p in parts)
                self.update_inflection_boxes(len(parts) + 1)
            else:
                date = pd.to_datetime(str(self.sender().text()), format='%Y-%m').date()

            checkbox.setChecked(True)
            checkbox.setPalette(self.palette_right)
            self.ini[self.sender().objectName()] = str(self.sender().text())

            # self.ini[self.sender().objectName()] = dt.datetime.strftime(dt.datetime.strptime(str(self.sender().text()), '%Y-%m'), '%Y-%m')
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
            for row in range(self.frozen_list.rowCount()):
                if int(self.frozen_list.cellWidget(row, 1).currentIndex()) >= 2:
                    self.frozen_list.cellWidget(row, 1).setCurrentIndex(1)
            for row in range(self.proxy_list.rowCount()):
                if int(self.proxy_list.cellWidget(row, 1).currentIndex()) >= 2:
                    self.proxy_list.cellWidget(row, 1).setCurrentIndex(1)

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
            # Reset the method to single method if the user also wants to average over the year
            if self.check_mean.isChecked() == True and int(methodBox.currentIndex()) >= 2:
                table.cellWidget(row, 1).setCurrentIndex(1)

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
        # self.ini['inflection_method'] = self.infl_method_list[self.inflection_method.currentIndex()]
        infl_list = ['ind', 'pwl', 'gap']

        layout = self.inflection_widget.layout()
        if layout is None:
            return
        infl_string = []
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if isinstance(widget, QtWidgets.QComboBox):
                widget.setEnabled(True)
            infl_string.append(infl_list[widget.currentIndex()])
        self.ini['inflection_method'] = ', '.join(infl_string)

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

    def populate_dim_widgets_1d(self, var_string):
        boxes_name = 'dim_' + var_string + '_boxes'
        layout_name = 'dim_' + var_string + '_layout'
        button_name = 'plot_button_' + var_string

        boxes = getattr(self, boxes_name, None)
        layout = getattr(self, layout_name, None)
        button = getattr(self, button_name, None)

        button.setDisabled(False)

        boxes.clear()

        for dim_index in range(1, len(self.current_data.o3.shape)):
            col_layout = QVBoxLayout()
            label = QtWidgets.QLabel(self.current_data.dim_array[dim_index])
            col_layout.addWidget(label)

            combo = QtWidgets.QComboBox()
            values = getattr(self.current_data, self.current_data.dim_array[dim_index])
            combo.addItems([str(value) for value in values])
            col_layout.addWidget(combo)

            boxes.append(combo)

            layout.addLayout(col_layout)

    def populate_dim_widgets_2d(self, var_string):
        boxes_name = 'dim_' + var_string + '_boxes'
        layout_name = 'dim_' + var_string + '_layout'
        button_name = 'plot_button_' + var_string

        boxes = getattr(self, boxes_name, None)
        layout = getattr(self, layout_name, None)
        button = getattr(self, button_name, None)

        boxes.clear()
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
            combo.currentIndexChanged.connect(lambda: self.sync_combo_boxes(var_string))

            boxes.append(combo)

            layout.addLayout(col_layout)
        for k, i in enumerate(self.dim_con_boxes):
            i.setCurrentIndex(k)

    def populate_dim_widgets_proxy(self):
        checks = self.dim_proxy_checks
        layout = self.dim_proxy_layout_checks

        checks.clear()

        str_groups = get_string_groups(self.proxy_string)
        for key, i in str_groups.items():
            if key[0] == 'proxy':
                col_layout = QVBoxLayout()
                check = QtWidgets.QCheckBox()
                check.setText(key[3])
                col_layout.addWidget(check)
                checks.append(check)
                layout.addLayout(col_layout)

            elif key[0] == 'intercept':
                col_layout = QVBoxLayout()
                check = QtWidgets.QCheckBox()
                check.setText(key[0])
                col_layout.addWidget(check)
                checks.append(check)
                layout.addLayout(col_layout)

    def populate_dim_widgets_proxy_con(self):
        self.proxy_con_combo.clear()
        combo = self.proxy_con_combo

        proxies = []

        str_groups = get_string_groups(self.proxy_string)
        for key, i in str_groups.items():
            if key[0] == 'proxy':
                proxies.append(key[3])

        combo.addItems(proxies)

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
            widget = QtWidgets.QWidget()
            h_layout = QHBoxLayout(widget)

            dim_values = list(map(str, getattr(data, dim)))
            # First combo box
            vbox1 = QVBoxLayout()
            label1 = QtWidgets.QLabel(f"{dim} Min:")
            combo1 = QtWidgets.QComboBox()
            combo1.addItems(dim_values)
            vbox1.addWidget(label1)
            vbox1.addWidget(combo1)

            # Second combo box
            vbox2 = QVBoxLayout()
            label2 = QtWidgets.QLabel(f"{dim} Max:")
            combo2 = QtWidgets.QComboBox()
            combo2.addItems(dim_values)
            combo2.setCurrentIndex(len(dim_values) - 1)
            vbox2.addWidget(label2)
            vbox2.addWidget(combo2)

            self.combo_pairs[dim] = (combo1, combo2)

            combo1.currentIndexChanged.connect(lambda index, d=dim: self.lim_update_min(d, index))
            combo2.currentIndexChanged.connect(lambda index, d=dim: self.lim_update_max(d, index))

            # Reset Limits
            keys_to_delete = [k for k in self.ini if 'additional_var_' in k and '_limit' in k]
            for k in keys_to_delete:
                del self.ini[k]

            h_layout.addLayout(vbox1)
            h_layout.addLayout(vbox2)

            main_layout.addWidget(widget)

    def sync_combo_boxes(self, var_string):
        # Get the indices of all combo boxes
        boxes = getattr(self, 'dim_' + var_string + '_boxes', None)
        button = getattr(self, 'plot_button_' + var_string, None)
        current_indices = [combo.currentIndex() for combo in boxes]

        # Disable the plot button if X- and Y-axis are not picked exactly once and if one of these has not enough values
        valid_indices = current_indices.count(0) == 1 and current_indices.count(1) == 1
        valid_lengths = all(self.dim_con_boxes[i].count() > 3 for i, idx in enumerate(current_indices) if idx in (0, 1))
        button.setDisabled(not (valid_indices and valid_lengths))

        sender_index = self.sender().currentIndex()
        if sender_index in {0, 1}:
            for i, combo in enumerate(boxes):
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

        data_index = self.dia_data_combo.currentIndex()
        dataset = self.list_of_data[data_index]

        matrix = dataset.o3[(slice(None), *indices)]
        matrix_orig = dataset.o3_og[(slice(None), *indices)]

        date = dataset.time

        # Fill Table
        self.dia_data_table.blockSignals(True)
        self.dia_data_table.setColumnCount(1)
        self.dia_data_table.setRowCount(len(date))

        self.dia_data_table.setVerticalHeaderLabels(date.astype(str))

        for k in range(len(date)):
            val = matrix[k]
            orig_val = matrix_orig[k]

            item = QTableWidgetItem(str(val))

            changed = False
            if np.ma.is_masked(val) != np.ma.is_masked(orig_val):
                changed = True
            elif not np.ma.is_masked(val):
                if not np.isclose(val, orig_val, equal_nan=True):
                    changed = True
            if changed:
                item.setBackground(QColor(255, 220, 220))
            else:
                item.setBackground(QColor(255, 255, 255))

            self.dia_data_table.setItem(k, 0, item)

        self.dia_data_table.blockSignals(False)

        # Fill information
        self.dia_data_start.setText(str(np.nanmin(date)))
        self.dia_data_end.setText(str(np.nanmax(date)))
        self.dia_data_time.setText(str(len(date)))
        self.dia_data_nan.setText(str(np.sum(np.isnan(matrix.filled(np.nan)))))

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

    def dia_data_change(self, item):
        row = item.row()
        text = item.text().strip()
        data_index = self.dia_data_combo.currentIndex()
        dataset = self.list_of_data[data_index]
        indices = [combo.currentIndex() for combo in self.dim_data_boxes]
        idx = (row, *indices)

        if text == '':
            dataset.o3.mask[idx] = True
            item.setText('')  # optional visuell leer lassen
            item.setBackground(QColor(255, 220, 220))
            return

        if text.lower() == 'nan':
            dataset.o3[idx] = np.nan
            dataset.o3.mask[idx] = False
            item.setBackground(QColor(255, 220, 220))
            return

        try:
            value = float(text)
            dataset.o3[idx] = value
            dataset.o3.mask[idx] = False
            item.setBackground(QColor(255, 220, 220))
        except ValueError:
            orig_val = dataset.o3_og[idx]
            print(f'Ungültiger Wert: {text}')
            self.dia_data_table.blockSignals(True)
            if np.ma.is_masked(orig_val):
                dataset.o3.mask[idx] = True
                item.setText('')
            else:
                dataset.o3[idx] = orig_val
                dataset.o3.mask[idx] = False
                item.setText(str(orig_val))
            item.setBackground(QColor(255, 255, 255))
            self.dia_data_table.blockSignals(False)

    def data_dim_reset_dataset(self):
        data_index = self.dia_data_combo.currentIndex()
        dataset = self.list_of_data[data_index]
        dataset.o3 = dataset.o3_og.copy()

        self.data_diagnostic()

    def proxy_diagnostic(self, index):
        proxy = self.proxies[index]
        start_date = str(np.array(proxy.time)[0])
        end_date = str(np.array(proxy.time)[-1])
        self.dia_proxy_start.setText(start_date)
        self.dia_proxy_end.setText(end_date)

        dim_str = ' '.join(map(str, proxy.data.shape))
        self.dia_proxy.setText(dim_str)

        data = proxy.data
        data_orig = proxy.data_og

        # Fill Table
        self.dia_proxy_table.blockSignals(True)

        if len(data.shape) >= 2:
            sec_dim = data.shape[1]
            self.dia_proxy_table.setColumnCount(sec_dim)
            self.dia_proxy_table.setHorizontalHeaderLabels(getattr(proxy, proxy.tag).astype(str))
        else:
            sec_dim = 1
            self.dia_proxy_table.setColumnCount(1)

        self.dia_proxy_table.setRowCount(data.shape[0])
        self.dia_proxy_table.setVerticalHeaderLabels(proxy.time.astype(str))

        for k in range(data.shape[0]):
            for kk in range(sec_dim):
                val = data[k] if sec_dim == 1 else data[k, kk]
                orig_val = data_orig[k] if sec_dim == 1 else data_orig[k, kk]
                item = QTableWidgetItem(str(val))

                changed = False

                if np.ma.is_masked(val) != np.ma.is_masked(orig_val):
                    changed = True

                elif not np.ma.is_masked(val) and not np.ma.is_masked(orig_val):
                    try:
                        if not np.isclose(float(val), float(orig_val), equal_nan=True):
                            changed = True
                    except Exception:
                        changed = True

                if changed:
                    item.setBackground(QColor(255, 220, 220))
                self.dia_proxy_table.setItem(k, kk, item)

        self.dia_proxy_table.blockSignals(False)

    def dia_proxy_change(self, item):
        row = item.row()
        col = item.column()
        text = item.text().strip()

        proxy_index = self.dia_proxy_combo.currentIndex()
        proxy = self.proxies[proxy_index]

        if proxy.data.ndim == 1:
            idx = (row,)
        else:
            idx = (row, col)

        if text == '':
            proxy.data.mask[idx] = True
            item.setText('')
            item.setBackground(QColor(255, 220, 220))
            return

        if text.lower() == 'nan':
            proxy.data[idx] = np.nan
            proxy.data.mask[idx] = False
            item.setBackground(QColor(255, 220, 220))
            return

        try:
            value = float(text)
            proxy.data[idx] = value
            proxy.data.mask[idx] = False
            item.setBackground(QColor(255, 220, 220))
        except ValueError:
            orig_val = proxy.data_og[idx]
            print(f'Ungültiger Wert: {text}')
            self.dia_proxy_table.blockSignals(True)
            if np.ma.is_masked(orig_val):
                proxy.data.mask[idx] = True
                item.setText('')
            else:
                proxy.data[idx] = orig_val
                proxy.data.mask[idx] = False
                item.setText(str(orig_val))
            item.setBackground(QColor(255, 255, 255))
            self.dia_proxy_table.blockSignals(False)

    def proxy_reset_dataset(self):
        proxy_index = self.dia_proxy_combo.currentIndex()
        proxy = self.proxies[proxy_index]

        proxy.data = proxy.data_og.copy()

        self.proxy_diagnostic(proxy_index)

    def plot_model_figure(self):
        # Clear the figure
        self.model_canvas.figure.clf()

        # Preparing Plot values
        data = copy.deepcopy(self.current_data)

        # Get dimension combo boxes indices
        plot_indices = [combo.currentIndex() for combo in self.dim_model_boxes]
        indices = tuple([slice(None)] + list(plot_indices))

        valid_cols = ~np.isnan(self.X[indices]).all(axis=0)
        valid_rows = ~np.isnan(self.X[indices]).all(axis=1)

        X_og = data.time
        Y_og = data.o3[indices]
        Y = self.trend_data[indices]
        X = self.time
        X_slope = copy.deepcopy(self.time[valid_rows])

        Y_trend = self.trends[tuple(plot_indices)]
        Y_uncert = self.uncertainty[tuple(plot_indices)]
        if not isinstance(Y_trend, (list, np.ndarray)):
            Y_trend = [Y_trend]
            Y_uncert = [Y_uncert]

        Y_model = np.matmul(self.X[indices][valid_rows][:, valid_cols], np.nan_to_num(self.betaa[tuple(plot_indices)][valid_cols], nan=0))
        common_time, idx_Y, idx_Y_model = np.intersect1d(X_og, X, return_indices=True)
        residuals = Y[idx_Y] - Y_model[idx_Y_model]
        rms = np.sqrt(np.nanmean(residuals ** 2))
        r2 = 1.0 - (np.nansum(residuals ** 2)) / (np.nansum((Y - np.nanmean(Y)) ** 2))
        slope_beta = []
        slope_X = []
        str_groups = get_string_groups(self.proxy_string)
        for key, i in str_groups.items():
            if key[0] == 'proxy' or key[-1] == None:
                continue
            else:
                if key[1] == 'month-of-the-year':
                    slope_beta.append(np.nanmean(self.betaa[tuple(plot_indices)][i], axis=0))
                    slope_X.append([np.nanmax(row[tuple(plot_indices)][i]) for row in self.X])
                else:
                    slope_beta.append(self.betaa[tuple(plot_indices)][i[0]])
                    slope_X.append(self.X[indices][:, i[0]])

        # generate list if we have inflection dates
        inflections = self.current_ini.get('inflection_point', '')
        inflection_dates = [s.strip() for s in inflections.split(',') if s.strip()]
        n_plots = 1 if not inflection_dates else len(inflection_dates) + 1 - self.current_ini.get('inflection_method', '').count('gap')
        subtitles = []
        if n_plots == 1:
            subtitles = [None]  # no subtitle, just one plot
        else:
            subtitles.append(f"before {inflection_dates[0]}")
            for i in range(len(inflection_dates) - 1):
                subtitles.append(f"between {inflection_dates[i]} and {inflection_dates[i + 1]}")
            subtitles.append(f"after {inflection_dates[-1]}")

        trend_lines = [f'trend {subtitles[k]}: {v:.2f} ± {Y_uncert[k] * 2:.2f} %/decade' for k, v in enumerate(Y_trend)]
        trend_lines.append(f'   r² = {r2:.2f}, RMS = {rms:.2f} {self.current_ini.get("o3_var_unit", "")}')
        trend_string = '\n'.join(trend_lines)

        Y_slope = np.array(slope_X).T @ np.array(slope_beta)
        Y_slope = Y_slope[valid_rows]
        plot_number = 1

        # inflection_methods = [str(m).strip().lower() for m in self.current_ini.get('inflection_method', '')]
        if self.current_ini.get('inflection_point', None):
            inflection_points = [dt.datetime.strptime(d.strip(), '%Y-%m').date() for d in self.current_ini.get('inflection_point').split(',')]
            for k, inflection_point in enumerate(sorted(inflection_points)):
                # Find index where time >= inflection point
                # breakpoint_index = np.where([(t.year, t.month) >= (inflection_point.year, inflection_point.month) for t in self.time[valid_rows]])[0][0]
                times = np.array(self.time[valid_rows])
                idx = np.where(times >= inflection_point)[0]
                if idx.size == 0:
                    continue
                breakpoint_index = idx[0]

                # Insert NaN into both X_slope and Y_slope at the breakpoint
                X_slope = np.insert(X_slope, breakpoint_index + k, X_slope[breakpoint_index + k])
                Y_slope = np.insert(Y_slope, breakpoint_index + k, np.nan)

        Y_slope_clean = Y_slope.copy()

        nan_idx = np.where(np.isnan(Y_slope_clean))[0]
        segment_edges = np.concatenate(([-1], nan_idx, [len(Y_slope_clean)]))
        for start, end in zip(segment_edges[:-1], segment_edges[1:]):
            seg = Y_slope_clean[start + 1:end]
            if seg.size == 0:
                continue
            if np.allclose(seg, 0.0, atol=1e-10, equal_nan=False):
                Y_slope_clean[start + 1:end] = np.nan
        Y_slope = Y_slope_clean

        self.model_canvas.axes_list = [self.model_canvas.figure.add_subplot(plot_number, 1, i + 1) for i in range(plot_number)]

        bounds = np.arange(-9, 10, 1, dtype=int)
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list("", plt.get_cmap('RdBu_r')(np.arange(10, 245, 3).astype(int)))
        cmap.set_under(plt.get_cmap('RdBu_r')(0))
        cmap.set_over(plt.get_cmap('RdBu_r')(255))
        norm = mpl.colors.BoundaryNorm(bounds, cmap.N)

        for k, ax in enumerate(self.model_canvas.axes_list):
            # if X_og.shape != X.shape and not self.anomaly_check.isChecked():
            ax.plot(X_og, Y_og, label='Original Time Series', linewidth=1.4)
            ax.plot(X, Y, label='Time Series', linewidth=1.8)

            ax.plot(self.time[valid_rows], Y_model, label='Model', linewidth=1.8)
            ax.plot(X_slope, Y_slope, path_effects=[pe.Stroke(linewidth=5, foreground='black'), pe.Normal()], label='Trend', linewidth=1.3)
            ax.legend(loc='upper right')

            props = dict(boxstyle='round', facecolor='white', alpha=1)
            ax.text(0.05, 0.95, trend_string, transform=ax.transAxes, fontsize=10, verticalalignment='top', horizontalalignment='left', bbox=props)
            ax.set_title(data.name + '\nat ' + ', '.join(f"{dim} {val}" for dim, val in zip(data.dim_array[1:], list([combo.currentText() for combo in self.dim_model_boxes]))))
        self.model_canvas.axes_list[0].set_xlabel('Time [yr]', fontsize=14)
        self.model_canvas.axes_list[0].set_ylabel(self.current_ini.get('o3_var_unit', ''), fontsize=14)
        self.model_canvas.figure.tight_layout()

        self.model_canvas.draw()

    def plot_contour_figure(self):
        self.con_canvas.figure.clf()

        trends = self.trends
        uncert = self.uncertainty
        # signis = self.signi
        signis = abs(trends / uncert)
        data = copy.deepcopy(self.current_data)

        # Get dimension combo boxes indices
        plot_indices = ()
        for k, combo in enumerate(self.dim_con_boxes):
            if combo.currentIndex() == 0:
                plot_indices += (slice(None),)
                x_grid = getattr(data, data.dim_array[1:][k])
                x_label = getattr(data, data.dim_array[1:][k] + '_unit')
            elif combo.currentIndex() == 1:
                plot_indices += (slice(None),)
                y_grid = getattr(data, data.dim_array[1:][k])
                y_label = getattr(data, data.dim_array[1:][k] + '_unit')
            else:
                plot_indices += (combo.currentIndex() - 2,)

        # determine how many subplots to make
        inflections = self.current_ini.get('inflection_point', '')
        inflection_dates = [s.strip() for s in inflections.split(',') if s.strip()]
        n_plots = 1 if not inflection_dates else len(inflection_dates) + 1 - self.current_ini.get('inflection_method', '').count('gap')

        # generate subtitles if we have inflection dates
        subtitles = []
        if n_plots == 1:
            subtitles = [None]  # no subtitle, just one plot
        else:
            subtitles.append(f"before {inflection_dates[0]}")
            for i in range(len(inflection_dates) - 1):
                subtitles.append(f"between {inflection_dates[i]} and {inflection_dates[i + 1]}")
            subtitles.append(f"after {inflection_dates[-1]}")

        # prepare figure and axes
        fig = self.con_canvas.figure
        fig.clf()
        axes = fig.subplots(1, n_plots, squeeze=False)[0]
        # axes = axes[0]  # flatten row

        bounds = np.arange(-10, 11, 1, dtype=int)
        colors = ["#08306b", "#0b4d6e", "#136b88", "#198aa2", "#1fa8bb", "#26c6d5", "#52dce1", "#7ee8eb", "#a5f2f3", "#e0ffff", "#fff4d6", "#fdd49e", "#fbc27b", "#fdae6b", "#fc8d3c", "#f16913",
                  "#e6550d", "#d94801", "#b94702", "#a63603"]
        cmap = LinearSegmentedColormap.from_list('custom_diverging', colors, N=255)
        cmap.set_under(colors[0])
        cmap.set_over(colors[-1])
        norm = mpl.colors.BoundaryNorm(bounds, cmap.N)

        for idx in range(n_plots):
            ax = axes[idx]

            # select slice of trend and signi depending on subplot
            this_indices = plot_indices + (idx,) if n_plots > 1 else plot_indices
            if trends[this_indices].shape != (len(y_grid), len(x_grid)):
                trend = trends[this_indices].T
                signi = signis[this_indices].T > 2
            else:
                trend = trends[this_indices]
                signi = signis[this_indices] > 2
            masked_uncertainty = np.where(np.isnan(trend), np.nan, signi)

            # plotting
            if self.con_alternative.isChecked():
                cf = ax.imshow(trend, cmap=cmap, norm=norm,
                               extent=[x_grid[0] + (x_grid[0] - x_grid[1]) / 2,
                                       x_grid[-1] + (x_grid[-1] - x_grid[-2]) / 2,
                                       y_grid[0] + (y_grid[0] - y_grid[1]) / 2,
                                       y_grid[-1] + (y_grid[-1] - y_grid[-2]) / 2],
                               origin='lower', aspect='auto', alpha=0.7)
                if self.con_uncertainty.isChecked():
                    x_edges = np.zeros(len(x_grid) + 1)
                    y_edges = np.zeros(len(y_grid) + 1)

                    # internal edges = midpoints
                    x_edges[1:-1] = (x_grid[:-1] + x_grid[1:]) / 2
                    y_edges[1:-1] = (y_grid[:-1] + y_grid[1:]) / 2

                    # extrapolate the boundaries
                    x_edges[0] = x_grid[0] - (x_grid[1] - x_grid[0]) / 2
                    x_edges[-1] = x_grid[-1] + (x_grid[-1] - x_grid[-2]) / 2
                    y_edges[0] = y_grid[0] - (y_grid[1] - y_grid[0]) / 2
                    y_edges[-1] = y_grid[-1] + (y_grid[-1] - y_grid[-2]) / 2

                    # loop and add hatched rectangles
                    for i in range(trend.shape[0]):
                        for j in range(trend.shape[1]):
                            if not masked_uncertainty[i, j]:
                                rect = patches.Rectangle(
                                    (x_edges[j], y_edges[i]),
                                    x_edges[j + 1] - x_edges[j],
                                    y_edges[i + 1] - y_edges[i],
                                    linewidth=0, fill=None, hatch='//', edgecolor='grey'
                                )
                                ax.add_patch(rect)

            else:
                cf = ax.contourf(x_grid, y_grid, trend, cmap=cmap, levels=bounds, norm=norm, extend='both')
                ax.contour(x_grid, y_grid, trend, levels=bounds, colors=('k',), alpha=0.7, norm=norm, extend='both', linewidths=1)
                if self.con_uncertainty.isChecked():
                    ax.contourf(x_grid, y_grid, masked_uncertainty, levels=[0, 0.5], colors='none', hatches=['\\\\'])
                    ax.contour(x_grid, y_grid, masked_uncertainty, levels=[0.5], colors='#DBDBDB', norm=norm)

            ax.set_xlim([np.nanmin(x_grid), np.nanmax(x_grid)])
            ax.set_ylim([np.nanmin(y_grid), np.nanmax(y_grid)])
            if self.con_invert.isChecked():
                ax.set_ylim(ax.get_ylim()[::-1])

            # axis labels
            ax.set_xlabel(x_label, fontsize=14)
            if idx == 0:
                ax.set_ylabel(y_label, fontsize=14)
            else:
                ax.set_yticklabels([])  # hide y tick labels
                ax.set_ylabel('')

            # add subplot subtitle if applicable
            if subtitles[idx]:
                ax.set_title(subtitles[idx], fontsize=12)

            # log scaling
            if 'pressure' in x_label.lower():
                ax.set_xscale('log')
            if 'pressure' in y_label.lower():
                ax.set_yscale('log')

        # one big title for the whole figure
        fig.suptitle(data.name + ' at ' + ', '.join(f"{dim} {val}" for dim, val in zip(data.dim_array[1:], list([combo.currentText() for combo in self.dim_con_boxes]))), fontsize=16)

        # add colorbar to the last subplot
        divider = make_axes_locatable(axes[-1])
        cbar_ax = divider.append_axes("right", size="5%", pad=0.2)
        cbar = fig.colorbar(cf, cax=cbar_ax, label='[%/decade]')
        cbar.set_ticks(bounds)

        self.con_canvas.figure = fig
        self.con_canvas.axes = axes
        self.con_canvas.figure.tight_layout(rect=[0, 0, 1, 0.95])  # leave space for suptitle
        self.con_canvas.draw()

    def plot_resi_figure(self):
        # Clear the figure
        self.resi_canvas.figure.clf()

        # Preparing Plot values
        data = copy.deepcopy(self.current_data)

        # Get dimension combo boxes indices
        plot_indices = [combo.currentIndex() for combo in self.dim_resi_boxes]
        indices = tuple([slice(None)] + list(plot_indices))

        Y = self.trend_data[indices]

        valid_cols = ~np.isnan(self.X[indices]).all(axis=0)
        valid_rows = ~np.isnan(self.X[indices]).all(axis=1)
        X = copy.deepcopy(self.time[valid_rows])

        Y_trend = self.trends[tuple(plot_indices)]
        if not isinstance(Y_trend, (list, np.ndarray)):
            Y_trend = [Y_trend]

        slope_beta = []
        slope_X = []
        resi_beta = []
        resi_X = []

        str_groups = get_string_groups(self.proxy_string)
        for key, i in str_groups.items():
            if key[0] == 'proxy' or key[0] == 'intercept':
                if key[1] == 'month-of-the-year':
                    resi_beta.append(np.nanmean(self.betaa[tuple(plot_indices)][i], axis=0))
                    resi_X.append([np.nanmax(row[tuple(plot_indices)][i]) for row in self.X])
                else:
                    resi_beta.append(self.betaa[tuple(plot_indices)][i[0]])
                    resi_X.append(self.X[indices][:, i[0]])
            elif key[0] == 'trend':
                if key[1] == 'month-of-the-year':
                    slope_beta.append(np.nanmean(self.betaa[tuple(plot_indices)][i], axis=0))
                    slope_X.append([np.nanmax(row[tuple(plot_indices)][i]) for row in self.X])
                else:
                    slope_beta.append(self.betaa[tuple(plot_indices)][i[0]])
                    slope_X.append(self.X[indices][:, i[0]])

        trend_string = "\n".join([f"trend {k + 1}: {v:.2f}%/decade" for k, v in enumerate(Y_trend)])

        # Model, slope, residuals
        Y_model = np.matmul(self.X[indices][valid_rows][:, valid_cols],
                            np.nan_to_num(self.betaa[tuple(plot_indices)][valid_cols], nan=0))
        Y_slope = np.array(slope_X).T @ np.array(slope_beta)
        Y_slope = Y_slope[valid_rows]
        Y_all_but_trend = np.array(resi_X).T @ np.array(resi_beta)
        Y_resi = Y - Y_all_but_trend
        Y_resi_2 = Y[valid_rows] - Y_model
        plot_number = 1

        # (optional) inflection points → adapt to multi-point scheme if needed
        # if self.current_ini.get('inflection_point', None):
        #     inflection_points = [dt.datetime.strptime(d.strip(), '%Y-%m')
        #                          for d in self.current_ini.get('inflection_point').split(',')]
        #     for inflection_point in sorted(inflection_points):
        #         breakpoint_index = np.where([(t.year, t.month) >= (inflection_point.year, inflection_point.month)
        #                                      for t in self.time[valid_rows]])[0][0]
        #         X = np.insert(X, breakpoint_index, X[breakpoint_index])
        #         Y_slope = np.insert(Y_slope, breakpoint_index, np.nan)
        #         Y_resi_2 = np.insert(Y_resi_2, breakpoint_index, np.nan)

        self.resi_canvas.axes_list = [self.resi_canvas.figure.add_subplot(plot_number, 1, i + 1)
                                      for i in range(plot_number)]

        for k, ax in enumerate(self.resi_canvas.axes_list):
            ax.plot(X, Y_resi_2 + Y_slope, label='Residuals', linewidth=1.8)
            ax.plot(X, Y_slope, path_effects=[pe.Stroke(linewidth=5, foreground='black'),
                                              pe.Normal()],
                    label='Trend', linewidth=1.3)

            props = dict(boxstyle='round', facecolor='white', alpha=1)
            ax.text(0.05, 0.95, trend_string, transform=ax.transAxes,
                    fontsize=10, verticalalignment='top', horizontalalignment='left', bbox=props)
            ax.set_title(data.name + '\n residuals at ' + ', '.join(
                f"{dim} {val}" for dim, val in zip(data.dim_array[1:],
                                                   [combo.currentText() for combo in self.dim_resi_boxes])))

        toolbar = NavigationToolbar(self.resi_canvas, self)
        self.resi_canvas.axes_list[0].set_xlabel('Time [yr]', fontsize=14)
        self.resi_canvas.axes_list[0].set_ylabel(self.current_ini.get('o3_var_unit', ''), fontsize=14)
        self.resi_canvas.axes_list[0].legend()
        self.resi_canvas.figure.tight_layout()
        self.resi_canvas.draw()

    def plot_proxy_figure(self):
        # Clear the figure
        self.proxy_canvas.figure.clf()

        # Get dimension combo boxes indices
        plot_indices = [combo.currentIndex() for combo in self.dim_proxy_boxes]
        indices = tuple([slice(None)] + list(plot_indices))
        data = copy.deepcopy(self.current_data)
        X = copy.deepcopy(self.X[indices])
        beta = copy.deepcopy(self.betaa[tuple(plot_indices)])
        checks = [check.isChecked() for check in self.dim_proxy_checks]
        if not any(checks):
            return      # Stops the function if nothing was checked

        valid_cols = ~np.isnan(self.X[indices]).all(axis=0)
        valid_rows = ~np.isnan(self.X[indices]).all(axis=1)
        date = copy.deepcopy(self.time[valid_rows])

        mean_ozone = np.nanmean(self.trend_data[indices])

        Y_og = self.trend_data[indices][valid_rows]
        Y_model = np.matmul(self.X[indices][valid_rows][:, valid_cols], self.betaa[tuple(plot_indices)][valid_cols])
        Y_resi = Y_og - Y_model

        Y = []
        Y_label = []
        Y_method = []
        Y_beta = []

        str_groups = get_string_groups(self.proxy_string)

        check_idx = 0
        for key, i in str_groups.items():
            if key[0] == 'proxy':
                if checks[check_idx]:
                    if key[1] == 'month-of-the-year':
                        Y.append(np.nansum(np.array(X[:, i]) * np.array(beta[i]), axis=1))
                        Y_beta.append([np.nanmean(beta[i], axis=-1)])
                    else:
                        Y.append(np.array(X[:, i]) @ np.array(beta[i]))
                        Y_beta.append(beta[i])
                    Y_label.append(key[-1])
                    Y_method.append(key[1])
                check_idx += 1
            elif key[0] == 'intercept':
                if checks[check_idx]:
                    if key[1] == 'month-of-the-year':
                        Y.append(np.nansum(np.array(X[:, i]) * np.array(beta[i]), axis=1))
                    else:
                        Y.append(np.array(X[:, i]) @ np.array(beta[i]))
                    Y_label.append(key[0])
                    Y_method.append(key[1])
                    Y_beta.append(None)
                check_idx += 1

        self.proxy_canvas.axes_list = [self.proxy_canvas.figure.add_subplot(len(Y), 1, i + 1) for i in range(len(Y))]
        colors = cm.cmaps['hawaii'](np.linspace(0, 0.6, len(Y)))

        for k, ax in enumerate(self.proxy_canvas.axes_list):
            ax.plot(date, Y[k][valid_rows] + Y_resi, label=Y_label[k] + ' + residual', color='black', linewidth=1.4)
            ax.plot(date, Y[k][valid_rows], label=Y_label[k], color=colors[k], linewidth=1.8)
            ax.yaxis.set_label_position("right")
            ax.set_ylabel(Y_label[k] + '\n' + Y_method[k])
            if k == 0:
                ax.set_title('Proxies at ' + ', '.join(f"{dim} {val}" for dim, val in zip(data.dim_array[1:], list([combo.currentText() for combo in self.dim_proxy_boxes]))) + '\n mean ozone: ' + "{:.2e}".format(mean_ozone) + ' ' + self.current_ini.get('o3_var_unit', ''))
            if k < len(self.proxy_canvas.axes_list) - 1:
                ax.set_xticklabels([])
            else:
                ax.set_xlabel('Time [yr]', fontsize=14)
            ax.xaxis.set_minor_locator(AutoMinorLocator())
            ax.yaxis.set_minor_locator(AutoMinorLocator())
            ax.tick_params(which='major', length=7)
            ax.tick_params(which='minor', length=4)

            if Y_beta[k] is not None:
                beta_str = f"beta: {Y_beta[k][0]:.2e}"
                props = dict(boxstyle='round', facecolor='white', alpha=1)
                ax.text(0.05, 0.95, beta_str, transform=ax.transAxes, fontsize=10, verticalalignment='top', horizontalalignment='left', bbox=props)
        self.proxy_canvas.figure.supylabel(self.current_ini.get('o3_var_unit', ''), fontsize=14)

        self.proxy_canvas.figure.tight_layout()

        self.proxy_canvas.draw_idle()
        self.proxy_canvas.flush_events()

    def plot_proxy_con_figure(self):
        # Clear the figure
        self.proxy_con_canvas.figure.clf()

        beta = copy.deepcopy(self.betaa)
        data = copy.deepcopy(self.current_data)

        # Get dimension combo boxes indices
        plot_indices = ()
        for k, combo in enumerate(self.dim_proxy_con_boxes):
            if combo.currentIndex() == 0:
                plot_indices += (slice(None),)
                x_grid = getattr(data, data.dim_array[1:][k])
                x_label = getattr(data, data.dim_array[1:][k] + '_unit')
            elif combo.currentIndex() == 1:
                plot_indices += (slice(None),)
                y_grid = getattr(data, data.dim_array[1:][k])
                y_label = getattr(data, data.dim_array[1:][k] + '_unit')
            else:
                plot_indices += (combo.currentIndex() - 2,)

        str_groups = get_string_groups(self.proxy_string)
        count = 0
        for key, i in str_groups.items():
            if key[0] == 'proxy':
                if key[1] == 'month-of-the-year':
                    if self.proxy_con_combo.currentIndex() == count:
                        proxy_indices = i
                        plot_indices += (proxy_indices,)
                        beta = np.nanmean(beta[plot_indices], axis=-1)
                        break
                else:
                    if self.proxy_con_combo.currentIndex() == count:
                        proxy_indices = i[0]
                        plot_indices += (proxy_indices,)
                        beta = beta[plot_indices]
                        break
                count += 1

        if beta.shape != (len(y_grid), len(x_grid)):
            beta = beta.T

        if np.isnan(beta).all():
            return

        self.proxy_con_canvas.axes = self.proxy_con_canvas.figure.add_subplot(1, 1, 1)

        cmap = matplotlib.colors.LinearSegmentedColormap.from_list("", plt.get_cmap('RdBu_r')(np.arange(10, 245, 3).astype(int)))
        cmap.set_under(plt.get_cmap('RdBu_r')(0))
        cmap.set_over(plt.get_cmap('RdBu_r')(255))
        vmax = np.ceil(np.nanmax(np.abs(beta)) / 10 ** np.floor(np.log10(np.nanmax(np.abs(beta))))) * 10 ** np.floor(np.log10(np.nanmax(np.abs(beta))))
        bounds = np.concatenate((np.arange(-vmax, 0, (vmax/7)), np.arange(0, vmax + (vmax/7), (vmax/7))))

        norm = mpl.colors.BoundaryNorm(bounds, cmap.N)

        if self.proxy_con_alternative.isChecked() == True:
            cf = self.proxy_con_canvas.axes.imshow(beta, cmap=cmap, norm=norm, extent=[x_grid[0] + (x_grid[0]-x_grid[1])/2, x_grid[-1] + (x_grid[-1]-x_grid[-2])/2, y_grid[0] + (y_grid[0]-y_grid[1])/2, y_grid[-1] + (y_grid[-1]-y_grid[-2])/2], origin='lower', aspect='auto', alpha=0.7)
        else:
            cf = self.proxy_con_canvas.axes.contourf(x_grid, y_grid, beta, norm=norm, levels=bounds, cmap=cmap, extend='both')
            self.proxy_con_canvas.axes.contour(x_grid, y_grid, beta, norm=norm, levels=bounds, colors=('k',), alpha=0.7, extend='both', linewidths=1)
        self.proxy_con_canvas.axes.set_xlim([np.nanmin(x_grid), np.nanmax(x_grid)])
        self.proxy_con_canvas.axes.set_ylim([np.nanmin(y_grid), np.nanmax(y_grid)])
        if self.proxy_con_invert.isChecked() == True:
            self.proxy_con_canvas.axes.set_ylim(self.proxy_con_canvas.axes.get_ylim()[::-1])
        self.proxy_con_canvas.axes.tick_params(axis='both')
        self.proxy_con_canvas.axes.set_title(self.proxy_con_combo.currentText() + ' at ' + ', '.join(f"{dim} {val}" for dim, val in zip(data.dim_array[1:], list([combo.currentText() for combo in self.dim_proxy_con_boxes]))))
        self.proxy_con_canvas.axes.set_xlabel(x_label, fontsize=14)
        self.proxy_con_canvas.axes.set_ylabel(y_label, fontsize=14)

        divider = make_axes_locatable(self.proxy_con_canvas.axes)
        cbar_ax = divider.append_axes("right", size="5%", pad=0.2)
        cbar = self.proxy_con_canvas.figure.colorbar(cf, cax=cbar_ax, label=self.current_ini.get('o3_var_unit', ''))
        cbar.set_ticks(bounds)
        self.proxy_con_canvas.figure.tight_layout()
        toolbar = NavigationToolbar(self.proxy_con_canvas, self)

        self.proxy_con_canvas.draw()

    def populate_all(self):
        self.clear_dim_widgets(self.dim_model_layout)
        self.populate_dim_widgets_1d('model')
        self.clear_dim_widgets(self.dim_X_layout)
        self.populate_X_dim_widget()
        self.clear_dim_widgets(self.dim_con_layout)
        self.populate_dim_widgets_2d('con')
        self.clear_dim_widgets(self.dim_resi_layout)
        self.populate_dim_widgets_1d('resi')
        self.clear_dim_widgets(self.dim_cell_layout)
        self.populate_dim_widgets_2d('cell')
        self.clear_dim_widgets(self.dim_proxy_layout_checks)
        self.populate_dim_widgets_proxy()
        self.clear_dim_widgets(self.dim_proxy_layout)
        self.populate_dim_widgets_1d('proxy')
        self.clear_dim_widgets(self.dim_proxy_con_layout)
        self.populate_dim_widgets_2d('proxy_con')
        self.populate_dim_widgets_proxy_con()

    def print_ini(self):
        print('brian@iup.physik.uni-bremen.de')

    def compute_trends(self):
        self.setDisabled(True)
        self.trends, self.signi, diagnostic = iup_reg_model(self.list_of_data[self.data_list.currentRow()], self.proxies, self.ini)
        self.setDisabled(False)

        self.X = diagnostic[0]
        self.beta = diagnostic[1]
        self.betaa = diagnostic[2]
        self.covbeta = diagnostic[3]
        self.proxy_string = diagnostic[4]
        self.time = diagnostic[5]
        self.trend_data = diagnostic[6]
        self.uncertainty = diagnostic[-1]
        self.current_ini = copy.copy(self.ini)
        self.current_data = copy.deepcopy(self.list_of_data[self.data_list.currentRow()])
        self.current_data = set_data_limits(self.current_data, self.current_ini)

        self.populate_all()


def load_config_ini(ini_path):
    # create a dictionary with all options loaded in, the config.ini file must be in the folder of the python program
    ini = {}

    with open(ini_path, 'r') as f:
        # Count the number of additional_proxy_path keys
        add_proxy_count = 0
        for line in f:
            if '=' not in line or line[0] == '#' or line[0] == ';':
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
            if '=' not in line or line[0] == '#' or line[0] == ';':
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
    new_data = copy.deepcopy(data)
    new_proxies = copy.deepcopy(proxies)

    # --- Normalize times to 15th of month ---
    new_data.time = np.array([t.replace(day=15) for t in new_data.time], dtype=object)
    for p in new_proxies:
        p.time = np.array([t.replace(day=15) for t in p.time], dtype=object)

    # --- Parse ini dates ---
    if 'start_date' in ini:
        date_start = dt.datetime.strptime(ini['start_date'], '%Y-%m').date().replace(day=15)
    else:
        date_start = dt.date.min

    if 'end_date' in ini:
        date_end = dt.datetime.strptime(ini['end_date'], '%Y-%m').date().replace(day=15)
    else:
        date_end = dt.date.max

    # --- Find overall proxy time span ---
    proxy_times_all = []
    for p in new_proxies:
        if getattr(p, 'method', 1) == 0:
            continue
        proxy_times_all.extend(p.time.tolist())

    if proxy_times_all:
        proxy_min, proxy_max = min(proxy_times_all), max(proxy_times_all)
    else:
        proxy_min, proxy_max = new_data.time[0], new_data.time[-1]

    # --- Common overlap for dataset + proxies + ini ---
    overall_start = max(date_start, new_data.time[0], proxy_min)
    overall_end = min(date_end,   new_data.time[-1], proxy_max)

    # --- Build continuous monthly axis (always 15th) ---
    y, m = overall_start.year, overall_start.month
    all_times = []
    while (y, m) <= (overall_end.year, overall_end.month):
        all_times.append(dt.date(y, m, 15))
        m += 1
        if m == 13:
            m = 1
            y += 1
    all_times = np.array(all_times, dtype=object)

    # --- Expand main dataset to all_times with NaNs ---
    data_arr = getattr(new_data, 'data', getattr(new_data, 'o3'))
    in_window = np.isin(new_data.time, all_times)
    tgt_slots = np.isin(all_times, new_data.time)
    expanded_data = np.full((len(all_times),) + data_arr.shape[1:], np.nan, dtype=float)
    data_arr_filled = np.ma.filled(data_arr, np.nan)  # masked → NaN
    expanded_data[tgt_slots] = data_arr_filled[in_window]
    new_data.time = all_times
    if hasattr(new_data, 'data'):
        new_data.data = expanded_data
    else:
        new_data.o3 = expanded_data

    # Monthly/yearly mean check
    check = averaging_window_text_check(ini.get('averaging_window', ''))

    # --- Normalize proxies and expand ---
    for p in new_proxies:
        if getattr(p, 'method', 1) == 0:
            # still align with NaNs
            arr = getattr(p, 'data')
            shape = (len(all_times),) + arr.shape[1:]
            if hasattr(p, 'data'):
                p.data = np.full(shape, np.nan)
            else:
                p.o3 = np.full(shape, np.nan)
            p.time = all_times
            continue

        arr = getattr(p, 'data')

        if check == 2:  # If the trends gets taken over a monthly average (e.g. Sep) then the normalization is also only over this specific month or the specific months
            month_index = re.split(r',\s*', ini.get('averaging_window', ''))
            month_index_set = {int(m) for m in month_index}
            mask = np.array([d.month in month_index_set for d in p.time])
        else:
            mask = np.ones(len(p.time), dtype=bool)

        try_start = dt.date(1979, 1, 15)
        start_idx = np.where(p.time == try_start)[0]
        start_idx = int(start_idx[0]) if start_idx.size > 0 else 0

        mask = mask[start_idx:]  # boolean mask for the tail
        temp = arr[start_idx:][mask]  # values extracted (masked)

        if arr.ndim == 1:
            vmin, vmax = np.nanmin(temp), np.nanmax(temp)
            if vmax > vmin:
                # norm = (temp - vmin) / (vmax - vmin)
                # norm = norm - 0.5
                norm = (temp - np.nanmean(temp)) / np.nanstd(temp)
                sub = arr[start_idx:]
                sub[mask] = norm
        else:
            sub = arr[start_idx:]
            for idx in np.ndindex(arr.shape[1:]):
                sub_masked = temp[(slice(None),) + idx]  # shape (Nmasked,)
                vmin, vmax = np.nanmin(sub_masked), np.nanmax(sub_masked)
                if vmax > vmin:
                    if 'aod' not in p.name.lower():
                        norm = (sub_masked - np.nanmean(sub_masked)) / np.nanstd(sub_masked)
                        # norm = (sub_masked - vmin) / (vmax - vmin)
                        # norm = norm - 0.5
                    else:
                        sub_masked[sub_masked == 0] = np.nan
                        norm = (sub_masked - np.nanmin(sub_masked)) / (vmax - np.nanmin(sub_masked))
                        # norm = norm - 0.5
                    sub[(mask,) + idx] = norm
        arr[start_idx:] = sub

        # --- Expand to all_times with NaNs ---
        tgt_slots = np.isin(all_times, p.time)
        src_rows = np.isin(p.time, all_times)
        expanded = np.full((len(all_times),) + arr.shape[1:], np.nan, dtype=float)
        arr_filled = np.ma.filled(arr, np.nan)  # masked → NaN
        expanded[tgt_slots] = arr_filled[src_rows]
        p.time = all_times
        if hasattr(p, 'data'):
            p.data = expanded
        else:
            p.o3 = expanded

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
            if 'days since' in format.lower() or format.lower().startswith('ds'):
                match = re.match(r'(ds|days since)\s+(\d{4}-\d{2}-\d{2})', format.lower().strip())
                time = np.array([(dt.datetime.strptime(match.group(2), '%Y-%m-%d') + dt.timedelta(days=float(t))).date() for t in time])
            elif np.issubdtype(time.dtype, 'O') or np.issubdtype(time.dtype, str):
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


def filter_time_series(data_arr, data, monthly=True, min_window_years=2, min_valid_fraction=0.75, check_yearly_validity=True):
    data_arr = np.ma.masked_invalid(data_arr)

    months_per_year = 12 if monthly else 1
    total_len = len(data_arr)

    # --- build segment boundaries ---
    # ensure sorted, unique, and within bounds
    inflections = sorted(i for i in getattr(data, 'inflection_index', []) if 0 < i < total_len)

    # segment start/end indices
    segment_starts = [0] + inflections
    segment_ends = inflections + [total_len]

    # output array: fully masked by default
    filtered_arr = np.ma.masked_all_like(data_arr)

    # --- process each segment independently ---
    for seg_start, seg_end in zip(segment_starts, segment_ends):

        segment = data_arr[seg_start:seg_end]
        seg_len = len(segment)

        if seg_len == 0:
            continue

        # minimum window size for this segment
        window_size = min_window_years * months_per_year

        if seg_len < window_size:
            # segment too short to ever be valid
            continue

        # find first valid window inside this segment
        start_idx = None
        for i in range(seg_len - window_size + 1):
            window = segment[i:i + window_size]
            if window.count() / window_size >= min_valid_fraction:
                start_idx = i
                break

        if start_idx is None:
            # whole segment invalid
            continue

        # provisional copy from valid start onward
        seg_filtered = np.ma.masked_all_like(segment)
        seg_filtered[start_idx:] = segment[start_idx:]

        # optional yearly validity check
        if check_yearly_validity:
            n_months = seg_len - start_idx
            n_years = n_months // months_per_year

            for y in range(n_years):
                year_start = start_idx + y * months_per_year
                year_end = year_start + months_per_year

                year_slice = segment[year_start:year_end]
                actual_len = len(year_slice)

                if actual_len == 0:
                    continue

                if year_slice.count() / actual_len >= min_valid_fraction:
                    seg_filtered[year_start:year_end] = year_slice
                else:
                    seg_filtered[year_start:year_end] = np.ma.masked

        # insert filtered segment back into full array
        filtered_arr[seg_start:seg_end] = seg_filtered

    return filtered_arr


def filter_by_time_coverage(data_arr, data, min_fraction=0.7, min_internal_fraction=0.5):
    arr = data_arr.filled(np.nan).copy()
    n = len(arr)

    inf_idx = list(getattr(data, 'inflection_index', []) or [])
    inf_idx = sorted([int(i) for i in inf_idx])

    bounds = [0] + inf_idx + [n]

    for seg in range(len(bounds) - 1):
        start, end = bounds[seg], bounds[seg + 1]

        segment = arr[start:end]
        valid_mask = ~np.isnan(segment)

        if np.sum(valid_mask) == 0:
            print(f'Segment {seg}: no valid data → set to NaN')
            arr[start:end] = np.nan
            continue

        valid_indices = np.where(valid_mask)[0]

        first_idx = valid_indices[0]
        last_idx = valid_indices[-1]

        segment_length = end - start
        covered_length = last_idx - first_idx + 1

        coverage = covered_length / segment_length

        internal_valid = np.sum(valid_mask[first_idx:last_idx + 1])
        internal_fraction = internal_valid / covered_length

        if coverage < float(min_fraction):
            print(f'Segment {seg}: coverage too small ({coverage:.2f}) → set to NaN')
            arr[start:end] = np.nan
            continue

        if internal_fraction < float(min_internal_fraction):
            print(f'Segment {seg}: internal fraction too small ({internal_fraction:.2f}) → set to NaN')
            arr[start:end] = np.nan
            continue

    return np.ma.masked_invalid(arr)


def filter_by_time_density_coverage(data_arr, data, min_fraction=0.7):
    arr = data_arr.filled(np.nan).copy()
    n = len(arr)

    # Segment boundaries
    inf_idx = sorted([int(i) for i in getattr(data, 'inflection_index', []) or []])
    bounds = [0] + inf_idx + [n]

    for seg in range(len(bounds) - 1):
        start, end = bounds[seg], bounds[seg + 1]
        segment = arr[start:end]

        valid_indices = np.where(~np.isnan(segment))[0]
        if len(valid_indices) == 0:
            print(f'Segment {seg}: no valid data → set to NaN')
            arr[start:end] = np.nan
            continue

        first_idx, last_idx = valid_indices[0], valid_indices[-1]
        segment_length = end - start
        print(segment_length)
        print(first_idx, last_idx)
        # Prüfen, ob der Anfang oder das Ende des Segments zu groß ist
        if first_idx / segment_length > (1 - float(min_fraction)) or (segment_length - last_idx - 1) / segment_length > (1 - float(min_fraction)):
            print(f'Segment {seg}: coverage too small → set to NaN')
            arr[start:end] = np.nan

    return np.ma.masked_invalid(arr)


def get_string_groups(string_list):
    # This function will look into a list of strings and create a dictionary with different groups and their respective indices of the original list
    pattern_group = re.compile(r'(intercept|trend) #(\d+)')
    pattern_no_group = re.compile(r'(intercept|trend)')

    groups = {}
    attribute_list = ['single', 'harmonic', 'month-of-the-year']

    for k, i in enumerate(string_list):
        match = pattern_group.search(i)
        index = [kk for kk, s in enumerate(attribute_list) if s in i]
        if index:
            index = index[0]  # Only take the first match
        else:
            index = None

        if index is not None:
            if match and attribute_list[index] in i:
                type_ = match.group(1)
                number = int(match.group(2))
                key = (type_, attribute_list[index], number)
                if key not in groups:
                    groups[key] = []
                groups[key].append(k)
            else:
                match = pattern_no_group.search(i)
                if match and attribute_list[index] in i:
                    type_ = match.group(1)
                    key = (type_, attribute_list[index], None)
                    if key not in groups:
                        groups[key] = []
                    groups[key].append(k)
                else:
                    # Does not match either "trend" or "intercept" -> proxy
                    parts = i.split(' - ')
                    name, attribute, number = parts[:3]

                    key = ('proxy', attribute_list[index], None, name)
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
        i.data = np.ma.array(i.data)
        if i.data.mask is np.ma.nomask or isinstance(i.data.mask, np.bool_):
            i.data.mask = np.zeros(i.data.shape, dtype=bool)
        i.data_og = i.data.copy()

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
    proxy.data = np.ma.array(proxy.data)
    if proxy.data.mask is np.ma.nomask or isinstance(proxy.data.mask, np.bool_):
        proxy.data.mask = np.zeros(proxy.data.shape, dtype=bool)
    proxy.data_og = proxy.data.copy()

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
        data.o3_og = data.o3.copy()
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
                # covb_var = f.createVariable('beta_uncertainty', 'f4', dim_tuple[1:] + ('n_coefficients',), compression="zlib")
                # covb_var[:] = diagnostic[-1]

                if len(trends.shape) == len(dim_tuple):
                    trend_var = f.createVariable('trend', 'f4', dim_tuple[1:] + ('infl',), compression="zlib")
                    sig_var = f.createVariable('significance', 'f4', dim_tuple[1:] + ('infl',), compression="zlib")
                    covb_var = f.createVariable('trend_uncertainty', 'f4', dim_tuple[1:] + ('infl',), compression="zlib")
                else:
                    trend_var = f.createVariable('trend', 'f4', dim_tuple[1:], compression="zlib")
                    sig_var = f.createVariable('significance', 'f4', dim_tuple[1:], compression="zlib")
                    covb_var = f.createVariable('trend_uncertainty', 'f4', dim_tuple[1:], compression="zlib")
                trend_var[:] = trends
                sig_var[:] = signi
                covb_var[:] = diagnostic[-1]

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
    inflection_index = []
    inflection_date = []
    if 'inflection_point' in ini and 'inflection_method' in ini:
        inflection_array = re.findall(r'\d{4}-(?:0[1-9]|1[0-2])(?:-(?:0[1-9]|[12][0-9]|3[01]))?', ini['inflection_point'])
        for date in inflection_array:
            inflection_date.append(dt.datetime.strptime(date, '%Y-%m').date())
    else:
        return None

    for date in inflection_date:
        for k, i in enumerate(data.time.astype(dt.datetime)):
            if i.year == date.year and i.month == date.month:
                inflection_index.append(k)

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
    if 'inflection_method' not in ini:
        X_raw = [1, 0]
    elif 'pwl' in ini['inflection_method']:
        X_raw = [1] + [0] * len(ini['inflection_method'])
    elif 'ind' in ini['inflection_method']:
        X_raw = [1, 0] * len(ini['inflection_method'])
        if 'gap' in ini['inflection_method']:
            for i, m in enumerate(ini['inflection_method']):
                if m == 'gap':
                    X_raw[2 * i] = 1
                    X_raw[2 * i + 1] = None
    else:
        raise Exception('The inflection method in the config.ini file is not being recognized. Either use "pwl" for piece-wise linear trends or "ind" for independent trends. If none of these should be used, please delete the inflection method line or comment it out with "#".')

    X_1 = np.zeros((len(nanmask), len(X_1_string)), dtype=float)
    col = 0
    infl_count = 0
    for k, i in enumerate(X_raw):
        # Get an array of values (either the intercept values 1 or the ongoing trend values)
        # Depends on the inflection, trend and intercept method
        val = np.zeros(len(nanmask), dtype=float)  # Empty array to be filled with values depending on methods
        if i == None:   # If the column is a gap column, skip
            val = 0
            method = int(ini['trend_method'])
            infl_count += 1

        elif i == 1:  # Rules for intercept column
            seas_comp = int(ini.get('intercept_seasonal_component', ini.get('default_seasonal_component', 2)))
            method = int(ini['intercept_method'])
            if 'inflection_method' not in ini:
                val = 1
            elif 'pwl' in ini['inflection_method']:
                val = 1
            elif 'ind' in ini['inflection_method']:    # Intercept Inflection needs to account for multiple inflection points and gaps
                if infl_count == 0:
                    val[:data.inflection_index[infl_count]] = 1
                elif infl_count < len(data.inflection_index):
                    val[data.inflection_index[infl_count-1]:data.inflection_index[infl_count]] = 1
                else:
                    val[data.inflection_index[infl_count-1]:] = 1

        else:      # Rules for trend column
            seas_comp = int(ini.get('trend_seasonal_component', ini.get('default_seasonal_component', 2)))
            method = int(ini['trend_method'])
            if 'inflection_method' not in ini:
                val = np.arange(1, len(nanmask)+1)
            elif 'pwl' in ini['inflection_method']:
                if infl_count == 0:
                    val = np.arange(1, len(nanmask)+1)
                    infl_count += 1
                elif infl_count < len(data.inflection_index):
                    val[data.inflection_index[infl_count-1]:] = np.arange(1, len(nanmask)-data.inflection_index[infl_count-1]+1)
                    infl_count += 1
                else:
                    val[data.inflection_index[infl_count-1]:] = np.arange(1, len(nanmask)-data.inflection_index[infl_count-1]+1)
            elif 'ind' in ini['inflection_method']:
                if infl_count == 0:
                    val[:data.inflection_index[infl_count]] = np.arange(1, data.inflection_index[infl_count]+1)
                    infl_count += 1
                elif infl_count < len(data.inflection_index):
                    val[data.inflection_index[infl_count-1]:data.inflection_index[infl_count]] = np.arange(1, data.inflection_index[infl_count] - data.inflection_index[infl_count-1] + 1)
                    infl_count += 1
                else:
                    val[data.inflection_index[infl_count-1]:] = np.arange(1, len(nanmask)-data.inflection_index[infl_count-1]+1)

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
                # print(X_1[:, col])
                col += 1
                X_1[:, col] = val * np.cos(((kk + 1) * 2 * np.pi * np.arange(1, len(nanmask)+1))/12)
                # print(X_1[:, col])
                col += 1
        elif method == 3:
            month_array = np.array(pd.to_datetime(data.time[data.date_start:data.date_end]).month)
            for kk in range(12):
                X_1[:, col] = val
                X_1[np.where((month_array % 13) != kk + 1), col] = 0
                col += 1

    X_1[~nanmask, :] = np.nan
    return X_1


def get_X_2(proxies, nanmask, gap_mask, X_proxy_size, it, data):
    proxy_mask = nanmask | gap_mask
    mask_time = np.where(proxy_mask)[0]
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
                    tag = i.tag     # Proxy tag
                    tag_val = getattr(data, ii)[it.multi_index[kk]]
            if tag_val in getattr(i, tag):
                proxy_data = i.data[proxy_mask, np.where(getattr(i, tag) == tag_val)]
            else:
                closest_val = sorted([(val_close, abs(val_close - tag_val)) for val_close in getattr(i, tag)], key=lambda x: x[1:])[:2]
                val1, val2 = closest_val[0][0], closest_val[1][0]
                data1, data2 = i.data[proxy_mask, np.where(getattr(i, tag) == val1)[0][0]], i.data[proxy_mask, np.where(getattr(i, tag) == val2)[0][0]]
                temp_data = np.empty(len(data1))
                for kk, ii in enumerate(data1):
                    temp_data[kk] = np.interp(tag_val, [val1, val2], [data1[kk], data2[kk]])
                proxy_data = temp_data
        else:
            proxy_data = i.data[proxy_mask]

        if i.method == 0:
            continue
        elif i.method == 1:
            X_2[proxy_mask, col] = proxy_data
            col += 1
        elif i.method == 2:
            X_2[proxy_mask, col] = proxy_data
            col += 1
            for kk in range(int(i.seas_comp)):
                X_2[proxy_mask, col] = proxy_data * np.sin(((kk + 1) * 2 * np.pi * mask_time)/12)
                col += 1
                X_2[proxy_mask, col] = proxy_data * np.cos(((kk + 1) * 2 * np.pi * mask_time)/12)
                col += 1
        elif i.method == 3:
            month_array = np.array(pd.to_datetime(data.time[data.date_start:data.date_end]).month)
            for kk in range(12):
                X_2[proxy_mask, col] = proxy_data
                X_2[np.where((month_array % 13) != kk+1), col] = 0
                col += 1

    # Removing all columns with only NaNs (columns that got skipped because of limitations)
    X_2[~nanmask] = np.nan

    return X_2


def normalize(X_2):
    for k in range(X_2.shape[1]):
        current_proxy = X_2[:, k]
        X_2[:, k] = ((current_proxy - np.nanmin(current_proxy)) / (np.nanmax(current_proxy) - np.nanmin(current_proxy))) * 2 - 1
        # current_proxy = X_2[X_2[:, k] != 0, k]
        # X_2[X_2[:, k] != 0, k] = ((current_proxy - np.nanmin(current_proxy)) / (np.nanmax(current_proxy) - np.nanmin(current_proxy))) * 2 - 1
        # if k == range(X_2.shape[1])[1]:
        #     print(current_proxy)
        #     print(X_2[:, k])

    return X_2


def calc_trend(X_clean, data_arr, nanmask, ini, X_string, inflection_index):
    # Get the indices of the intercept and trend to get a mean value for the coefficient
    trend_string_index = [j for j, s in enumerate(X_string) if 'trend' in s]
    groups = get_string_groups(X_string)
    try:
        beta = np.linalg.inv(X_clean.T @ X_clean) @ X_clean.T @ data_arr[nanmask]
    except:
        print('Calculation failed: NaNs')
        return [np.nan] * len(trend_string_index), [np.nan] * len(trend_string_index), np.nan, np.nan, [np.nan] * len(trend_string_index)

    if len(trend_string_index) == 0:
        return (np.nan, np.nan, beta, beta, np.nan)

    # Carlo's autoregression
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
    if inflection_index:
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
            continue

    Xmask2ok = Xmask2[0:k, :]

    mult = 1
    if ini.get('anomaly', '') == 'True':
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
            covbetaa_z = [np.nan] * len(trend_string_index)
        else:
            trenda_z = []
            siga_z = []
            covbetaa_z = []

            count = 1
            for keys, indices in groups.items():
                if keys[0] == 'intercept' or keys[0] == 'proxy':
                    continue
                if keys[1] == 'month-of-the-year':
                    while keys[-1] > count:
                        trenda_z.append(np.nan)
                        siga_z.append(np.nan)
                        covbetaa_z.append(np.nan)
                        count += 1
                    trenda_z.append(np.nanmean(betaa[indices]) * mult)
                    # siga_z.append(np.abs(betaa[indices[0]] / np.sqrt(np.diag(covbetaa)[indices[0]])))
                    siga_z.append(np.abs(np.nanmean(betaa[indices]) / np.nanmean(np.sqrt(np.diag(covbetaa)[indices]))))
                    covbetaa_z.append(np.sqrt(np.nanmean(np.diag(covbetaa)[indices])) * mult)
                else:
                    while keys[-1] > count:
                        trenda_z.append(np.nan)
                        siga_z.append(np.nan)
                        count += 1
                    trenda_z.append(betaa[indices[0]] * mult)
                    siga_z.append(np.abs(betaa[indices[0]] / np.sqrt(np.diag(covbetaa)[indices[0]])))
                    covbetaa_z.append(np.sqrt(np.diag(covbetaa)[indices[0]]) * mult)
                count += 1
            # if ini.get('anomaly', '') == 'True' and ini.get('anomaly_method', 'rel') == 'rel':
            #     print('NOT YET FINISHED')
            #     print(chr(sum(range(ord(min(str(not ())))))))
            #     # idx = trend_string_index
            #     # beta_trend = betaa[idx]
            #     # cov_trend = covbetaa[np.ix_(idx, idx)]
            #     #
            #     # n = len(beta_trend)
            #     # mean_beta = np.nanmean(beta_trend)
            #     #
            #     # var_mean = np.nansum(cov_trend) / (n ** 2)
            #     # se_mean = np.sqrt(var_mean)
            #     #
            #     # scale = 120  # already percent
            #     #
            #     # trenda_z.append(mean_beta * scale)
            #     # covbetaa_z.append(se_mean * scale)
            #     # siga_z.append(np.abs(mean_beta / se_mean))
            #     # trenda_z.append(betaa[indices[0]] * mult)
            #     # siga_z.append(np.abs(betaa[indices[0]] / np.sqrt(np.diag(covbetaa)[indices[0]])))
            #     # covbetaa_z.append(np.sqrt(np.diag(covbetaa)[indices[0]]) * mult)
            # elif ini.get('anomaly', '') == 'True' and ini.get('anomaly_method', 'rel') == 'abs':
            #     print('NOT YET FINISHED')
            #     print(chr(sum(range(ord(min(str(not ())))))))
            # else:
            #     count = 1
            #     for keys, indices in groups.items():
            #         if keys[0] == 'intercept' or keys[0] == 'proxy':
            #             continue
            #         if keys[1] == 'month-of-the-year':
            #             while keys[-1] > count:
            #                 trenda_z.append(np.nan)
            #                 siga_z.append(np.nan)
            #                 covbetaa_z.append(np.nan)
            #                 count += 1
            #             trenda_z.append(np.nanmean(betaa[indices]) * mult)
            #             # siga_z.append(np.abs(betaa[indices[0]] / np.sqrt(np.diag(covbetaa)[indices[0]])))
            #             siga_z.append(np.abs(np.nanmean(betaa[indices]) / np.nanmean(np.sqrt(np.diag(covbetaa)[indices]))))
            #             covbetaa_z.append(np.sqrt(np.nanmean(np.diag(covbetaa)[indices])) * mult)
            #         else:
            #             while keys[-1] > count:
            #                 trenda_z.append(np.nan)
            #                 siga_z.append(np.nan)
            #                 count += 1
            #             trenda_z.append(betaa[indices[0]] * mult)
            #             siga_z.append(np.abs(betaa[indices[0]] / np.sqrt(np.diag(covbetaa)[indices[0]])))
            #             covbetaa_z.append(np.sqrt(np.diag(covbetaa)[indices[0]]) * mult)
            #         count += 1
                # siga_z = np.abs(betaa[trend_string_index] / np.sqrt(np.diag(covbetaa)[trend_string_index])) if len(trend_string_index) == 1 else [np.abs(betaa[i] / np.sqrt(np.diag(covbetaa)[i])) for i in trend_string_index]
                # trenda_z = betaa[trend_string_index] * mult if len(trend_string_index) == 1 else [betaa[i] * mult for i in trend_string_index]

    except:
        trenda_z = [np.nan] * len(trend_string_index)
        siga_z = [np.nan] * len(trend_string_index)
        covbetaa_z = [np.nan] * len(trend_string_index)
        print('Failed to calculate the trend and significants')
    if len(trenda_z) == 1:
        return trenda_z.pop(), siga_z.pop(), beta, betaa, covbetaa_z.pop()
    else:
        return np.array(trenda_z), np.array(siga_z), beta, betaa, np.array(covbetaa_z)


def iup_reg_model(data, proxies, ini):
    data, proxies = get_proxy_time_overlap(ini, proxies, data)
    data = set_data_limits(data, ini)

    # Get index of the inflection point
    data.inflection_index = get_inflection_index(ini, data)

    # Creating the empty arrays for the trends and the uncertainty
    if 'inflection_method' not in ini:
        trenda_z = np.empty(np.atleast_1d(data.o3[0, ...]).shape) * np.nan
        siga_z = np.empty(np.atleast_1d(data.o3[0, ...]).shape) * np.nan
        covbetaa_z = np.empty(np.atleast_1d(data.o3[0, ...]).shape) * np.nan
        X_string = ['intercept', 'trend']
    else:
        if isinstance(ini['inflection_method'], list) == True:
            infl_methods = ini['inflection_method']
        else:
            infl_methods = [part.strip() for part in ini['inflection_method'].split(',') if part.strip()]
        if len(infl_methods) < len(data.inflection_index) + 1:
            ini['inflection_method'] = infl_methods * (len(data.inflection_index) + 1)
        else:
            ini['inflection_method'] = infl_methods
        X_string = []
        if ('pwl' in infl_methods and 'ind' in infl_methods) or ('pwl' in infl_methods and 'gap' in infl_methods):
            raise ValueError('Piece-wise linear trends cannot be combined with gap and independent trends.')
        elif 'ind' in infl_methods:
            trenda_z = np.empty(np.atleast_1d((data.o3[0, ...] + (2,))).shape) * np.nan
            siga_z = np.empty(np.atleast_1d((data.o3[0, ...] + (2,))).shape) * np.nan
            covbetaa_z = np.empty(np.atleast_1d((data.o3[0, ...] + (2,))).shape) * np.nan
            X_string = []
            count = 1
            for method in ini['inflection_method']:
                if method == 'gap':
                    X_string.append('intercept gap')
                    X_string.append('gap')
                else:
                    X_string.append(f'intercept #{count}')
                    X_string.append(f'independent trend #{count}')
                    count += 1
        elif 'pwl' in ini['inflection_method']:
            trenda_z = np.empty(np.atleast_1d((data.o3[0, ...] + (2,))).shape) * np.nan
            siga_z = np.empty(np.atleast_1d((data.o3[0, ...] + (2,))).shape) * np.nan
            covbetaa_z = np.empty(np.atleast_1d((data.o3[0, ...] + (2,))).shape) * np.nan
            X_string = ['intercept', 'piece-wise linear trend #1']
            for k in range(2, len(ini['inflection_method']) + 1):
                X_string.append(f'piece-wise linear trend #{k}')

    # Expand dimension of trends and uncertainties, depending on number of inflection points
    if data.inflection_index:
        trenda_z = np.expand_dims(trenda_z, axis=-1)
        trenda_z = np.tile(trenda_z, (1,) * (trenda_z.ndim - 1) + ((len(ini['inflection_method']) - ini['inflection_method'].count('gap')),))
        siga_z = np.expand_dims(siga_z, axis=-1)
        siga_z = np.tile(siga_z, (1,) * (siga_z.ndim - 1) + ((len(ini['inflection_method']) - ini['inflection_method'].count('gap')),))
        covbetaa_z = np.expand_dims(covbetaa_z, axis=-1)
        covbetaa_z = np.tile(covbetaa_z, (1,) * (covbetaa_z.ndim - 1) + ((len(ini['inflection_method']) - ini['inflection_method'].count('gap')),))
    ini['trend_method'] = ini.get('trend_method', 1)
    ini['intercept_method'] = ini.get('intercept_method', 1)

    # check how the data should be averaged
    check = averaging_window_text_check(ini.get('averaging_window', ''))
    anom_check = ini.get('anomaly', 'False')
    time = pd.DatetimeIndex(data.time)
    time_log = np.unique(time.year, return_index=True)[1] if check != 0 else slice(None)

    # Creating new X_string depending on method used for trend and intercept
    X_1_string = calc_new_Xstring(X_string, ini)

    # Get size of the X matrices by either not using proxies or using proxies with different methods
    X_proxy_size, X_2_string = calc_proxy_size(proxies)

    X_string = X_1_string + X_2_string
    groups = get_string_groups(X_string)

    if check == 0:      # No averaging
        X_all = np.full((data.o3.shape + (len(X_string),)), np.nan, dtype='f4')
    elif check == 1:    # Yearly
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
        time_log = [x + 5 for x in time_log]    # Set the time index in the middle of the year
    elif check == 2:    # Monthly
        month_index = re.split(r',\s*', ini.get('averaging_window', ''))
        month_index = np.array([int(num) for num in month_index])
        X_all = np.full(((len(np.unique(time.year)),) + data.o3[0, ...].shape + (len(X_string),)), np.nan, dtype='f4')
        for i in proxies:
            for kk, ii in enumerate(np.unique(time.year)):
                time_index = np.arange((kk * 12), min((kk * 12) + 12, len(time)), 1)
                arr = i.data[time_index][np.in1d(time[time_index].month, month_index)]
                if arr.size == 0:
                    i.data[kk] = np.nan
                    continue
                elif np.count_nonzero((arr != 0) & ~np.isnan(arr)) / arr.size <= float(ini.get('skip_percentage', 0.75)):
                    i.data[kk] = np.nan
                    continue
                i.data[kk] = np.nanmean(i.data[time_index][np.in1d(time[time_index].month, month_index)], axis=0)
            i.data = i.data[:len(np.unique(time.year))]
        if getattr(data, 'inflection_index', None)[0]:
            for k, i in enumerate(data.inflection_index):
                data.inflection_index[k] = np.where(np.unique(time.year) == time[i].year)[0][0]  # Change inflection point to reflect the yearly data
        time_log = [x + int(np.nanmean(month_index) - 1) for x in time_log]  # Set the time index in the middle of the year

    beta_all = np.empty((data.o3[0, ...].shape + (len(X_string),)), dtype='f4') * np.nan
    betaa_all = np.empty((data.o3[0, ...].shape + (len(X_string),)), dtype='f4') * np.nan
    data_all = np.empty(X_all.shape[:-1])

    # Looping over every dimension but the first (time), to calculate the trends for every latitude, longitude and altitude
    it = np.nditer(data.o3[0, ...], flags=['multi_index'])
    while not it.finished:
        # print(str(it.multi_index) + ': calculating trend')
        dim_names = data.dim_array[1:]  # ohne time-Dimension
        coord_strings = []
        for dim_name, idx in zip(dim_names, it.multi_index):
            coord_values = getattr(data, dim_name)  # z.B. data.lat
            coord_val = coord_values[idx]
            if dim_name == 'lat':
                coord_strings.append(f'Latitude {coord_val:.1f}°')
            elif dim_name == 'lon':
                coord_strings.append(f'Longitude {coord_val:.1f}°')
            elif dim_name == 'alt':
                coord_strings.append(f'Altitude {coord_val:.1f}')
            else:
                coord_strings.append(f'{dim_name} {coord_val}')
        print(f"{it.multi_index}: calculating trend ({', '.join(coord_strings)})")

        data_arr = np.ma.masked_invalid(data.o3[(slice(None),) + it.multi_index])
        # data_arr = filter_time_series(data_arr, data, monthly=True, min_window_years=3, min_valid_fraction=0.5, check_yearly_validity=True)
        data_arr = filter_by_time_coverage(data_arr, data, min_fraction=ini.get('fill_fraction', 0.70), min_internal_fraction=ini.get('skip_percentage', 0.50))

        # if check == 0 and anom_check == 'True':
        #     for k in range(12):
        #         if ini.get('anomaly_method', 'rel') == 'abs':
        #             data_arr[time.month == k + 1] = data_arr[time.month == k + 1] - np.nanmean(data_arr[time.month == k + 1].filled(np.nan))
        #         else:
        #             data_arr[time.month == k + 1] = (data_arr[time.month == k + 1] - np.nanmean(data_arr[time.month == k + 1].filled(np.nan))) / np.nanmean(data_arr[time.month == k + 1].filled(np.nan))
        # elif check == 1:
        #     for k, i in enumerate(np.unique(time.year)):
        #         if len(np.nonzero(data_arr[np.where(time.year == i)])[0]) / len(np.where(time.year == i)[0]) <= float(ini.get('skip_percentage', 0.75)):
        #             data_arr[k] = np.nan
        #             continue
        #         data_arr[k] = np.nanmean(data_arr[np.where(time.year == i)])
        #     data_arr = data_arr[:len(np.unique(time.year))]
        #     if anom_check == 'True':
        #         if ini.get('anomaly_method', 'rel') == 'abs':
        #             data_arr = data_arr - np.nanmean(data_arr)
        #         else:
        #             data_arr = (data_arr - np.nanmean(data_arr)) / np.nanmean(data_arr)
        # elif check == 2:
        #     for k, i in enumerate(np.unique(time.year)):
        #         time_index = np.arange((k * 12), min((k * 12) + 12, len(time)), 1)
        #         if len(data_arr[time_index][np.in1d(time[time_index].month, month_index)].nonzero()[0]) / len(month_index) <= float(ini.get('skip_percentage', 0.75)):
        #             data_arr[k] = np.nan
        #             continue
        #         data_arr[k] = np.nanmean(data_arr[time_index][np.in1d(time[time_index].month, month_index)])
        #     data_arr = data_arr[:len(np.unique(time.year))]
        #     if anom_check == 'True':
        #         if ini.get('anomaly_method', 'rel') == 'abs':
        #             data_arr = data_arr - np.nanmean(data_arr)
        #         else:
        #             data_arr = (data_arr - np.nanmean(data_arr)) / np.nanmean(data_arr)

        nanmask = ~np.isnan(data_arr.filled(np.nan))
        gap_mask = np.zeros_like(nanmask, dtype=bool)
        if 'inflection_method' in ini and 'gap' in ini['inflection_method']:
            methods = ini['inflection_method']
            inf_idx = list(data.inflection_index)

            bounds = [0] + inf_idx + [len(nanmask)]

            for seg, method in enumerate(methods):
                if method == 'gap':
                    start, end = bounds[seg], bounds[seg + 1]
                    gap_mask[start:end] = True
        mask_time = np.where(nanmask == True)[0]

        # inf_idx = list(getattr(data, 'inflection_index', []) or [])  # Build segment boundaries from inflection indices
        # inf_idx = [int(i) for i in inf_idx]  # Guarantee integer indices and sorted order
        # inf_idx.sort()
        # bounds = [0] + inf_idx + [len(nanmask)]  # segment boundaries in index space of data_arr (0 .. len(nanmask))
        # segment_counts = [int(np.sum(nanmask[bounds[j]:bounds[j + 1]])) for j in range(len(bounds) - 1)]  # Count valid (non-nan) observations in each segment
        # min_count = int(ini.get('min_obs_per_segment', 12))
        # bad_segments = [j for j, c in enumerate(segment_counts) if c < min_count]
        # # Mask out those segments by setting data_arr (and optionally nanmask) to NaN
        # if bad_segments:
        #     for j in bad_segments:
        #         start, end = bounds[j], bounds[j + 1]
        #         data_arr[start:end] = np.nan
        #         nanmask[start:end] = False
        # Inquery if there are enough datapoints to even calculate a trend
        # if len(mask_time) / len(nanmask) < float(ini.get('skip_percentage', 0.75)):
        #     print('Not enough values to compute the trend! ' + f'{len(mask_time) / len(nanmask)*100:.2f}' + '% of data available.')
        #     it.iternext()
        #     continue
        X_1 = get_X_1(nanmask, ini, X_1_string, data)
        X_2 = get_X_2(proxies, nanmask, gap_mask, X_proxy_size, it, data)

        X = np.concatenate([X_1, X_2], axis=1)
        X[:, np.all(X[nanmask] == 0, axis=0)] = np.nan

        for keys, indices in groups.items():
            if keys[1] == 'month-of-the-year' and keys[0] == 'intercept':
                for i in indices:
                    if (np.sum((X[:, i] != 0) & ~np.isnan(X[:, i])) / (len(X[:, i])/12)) < float(ini.get('skip_percentage', 0.75)):  # Check to see if any month has less that the needed coverage
                        nanmask[(X[:, i] != 0) & ~np.isnan(X[:, i])] = False
                        X[(X[:, i] != 0) & ~np.isnan(X[:, i]), :] = np.nan
                        X[:, i::12] = np.nan

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

        # Calculation of the trends and uncertainties for each cell
        trenda_z[it.multi_index], siga_z[it.multi_index], beta, betaa, covbetaa_z[it.multi_index] = calc_trend(X_clean, data_arr, nanmask, ini, np.array(X_string)[~np.all(np.isnan(X), axis=0)], data.inflection_index)

        # Save X, beta and betaa
        X_all[(slice(None),) + it.multi_index + (slice(None),)][np.ix_(~row_mask, ~col_mask)] = X_clean

        beta_all[it.multi_index + (slice(None),)][~col_mask] = beta
        betaa_all[it.multi_index + (slice(None),)][~col_mask] = betaa
        data_all[(slice(None),) + it.multi_index] = data_arr.filled(np.nan)
        # Go to next iteration:
        it.iternext()
    diagnostic = [X_all, beta_all, betaa_all, data.dim_array, X_string, data.time[time_log], data_all, covbetaa_z]
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
    iup_ui(ui=True)
