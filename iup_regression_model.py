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
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt5 import QtWidgets, QtGui, uic
from PyQt5.QtGui import QPalette, QColor, QIcon
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QHeaderView, QFileDialog, QMessageBox
from regression_model_ui import Ui_MainWindow

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
        self.addItems(['disable', 'single', 'harmonics', '12 months'])


class ComboSeasonal(QtWidgets.QComboBox):
    def __init__(self, parent):
        super().__init__(parent)
        self.addItems(['annual', 'semi-annual', 'tri-annual', 'quarter-annual'])


# Empty "canvas" for plotting
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure()
        # self.axes =fig.add_subplot(111)
        super().__init__(fig)
        self.axes_list = []


# Popup window to set the variable names to load data
class VariableWindow(QtWidgets.QDialog):
    ini_signal = pyqtSignal(dict)
    def __init__(self, settings_ini, filename):
        super(VariableWindow, self).__init__()
        uic.loadUi('var_naming.ui', self)

        self.ini = settings_ini
        f = nc.Dataset(filename[0], 'r')
        keys = list(f.variables.keys())
        keys.insert(0, '-None-')
        f.close()

        self.load_variable_keys(keys)

        # connect buttons
        self.bttn_ok.clicked.connect(self.save_settings)
        self.bttn_cancel.clicked.connect(self.close)

    def load_variable_keys(self, keys):
        self.o3_var_combo.addItems(keys)
        self.time_var_combo.addItems(keys)
        self.lat_var_combo.addItems(keys)
        self.lon_var_combo.addItems(keys)
        self.alt_var_combo.addItems(keys)
        self.time_var_format.setText(self.ini['time_format'])

    def save_settings(self):
        # Saves all settings and closes the settings window
        # print(self.proxy_header.text() == '')

        # Change ini
        if self.o3_var_combo.currentIndex() != 0:
            self.ini['o3_var'] = self.o3_var_combo.currentText()
        else:
            self.ini['o3_var'] = None

        if self.lat_var_combo.currentIndex() != 0:
            self.ini['lat_var'] = self.lat_var_combo.currentText()
        else:
            self.ini['lat_var'] = None

        if self.lon_var_combo.currentIndex() != 0:
            self.ini['lon_var'] = self.lon_var_combo.currentText()
        else:
            self.ini['lon_var'] = None

        if self.alt_var_combo.currentIndex() != 0:
            self.ini['lev_var'] = self.alt_var_combo.currentText()
        else:
            self.ini['lev_var'] = None

        if self.time_var_combo.currentIndex() != 0:
            self.ini['time_var'] = self.time_var_combo.currentText()
        else:
            self.ini['time_var'] = None

        if self.time_var_format != '':
            self.ini['time_format'] = self.time_var_format.text()
        else:
            self.ini['time_format'] = None

        self.ini_signal.emit(self.ini)
        self.accept()


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

        self.load_presets()

        self.proxies = load_default_proxies(self.ini)
        self.proxies = load_additional_proxies(self.proxies, self.ini)
        self.infl_method_list = ['ind', 'pwl']

        # Create important variables
        self.X = None
        self.beta = None
        self.betaa = None
        self.time = None

        # Fill lists with proxies and data
        # Proxies
        self.update_proxy_table()

        self.define_palettes()

        # main UI functions
        self.infl_check.toggled.connect(self.inflection_enable)
        self.start_date.textChanged.connect(self.format_check)
        self.end_date.textChanged.connect(self.format_check)
        self.inflection_point.textChanged.connect(self.format_check)
        self.inflection_method.currentIndexChanged.connect(self.inflection_method_change)
        self.all_proxy_method.currentIndexChanged.connect(self.all_proxy_method_change)
        self.intercept_method_combo.currentIndexChanged.connect(self.update_intercept_method)
        self.trend_method_combo.currentIndexChanged.connect(self.update_trend_method)
        self.mean_line.textChanged.connect(self.text_check)
        self.trend_seas_combo.currentIndexChanged.connect(self.update_trend_seasonal)
        self.intercept_seas_combo.currentIndexChanged.connect(self.update_intercept_seasonal)
        self.anomaly_check.toggled.connect(self.anomaly_enable)
        self.radio_rel.toggled.connect(self.anomaly_method_toggle)
        self.radio_abs.toggled.connect(self.anomaly_method_toggle)
        self.preset_combo.currentIndexChanged.connect(self.change_preset)

        # Diagnostic UI functions
        self.dia_proxy_combo.currentIndexChanged.connect(self.proxy_diagnostic)
        self.data_list.currentRowChanged.connect(self.data_diagnostic)

        # Start trend analysis
        self.compute_button.clicked.connect(self.compute_trends)

        # Plotting
        # self.plot_check.toggled.connect(self.time_series_enable)
        self.dim_combo.currentTextChanged.connect(self.axis_options)
        self.axis_combo.activated.connect(self.update_plot_indices)
        self.plot_button.clicked.connect(self.plot_figure)

        # Layout for plotting
        self.layout = QVBoxLayout(self.figure_widget)
        self.canvas = MplCanvas(self.figure_widget)
        self.layout.addWidget(self.canvas)

        # Menu button connection
        self.menu_help.triggered.connect(self.print_ini)
        self.menu_load_data.triggered.connect(self.open_data_dialog)
        self.menu_load_proxy.triggered.connect(self.open_proxy_dialog)
        self.menu_save.triggered.connect(self.save_file)

        self.trend_seas_combo.setCurrentIndex(int(self.ini.get('trend_seasonal_component', self.ini.get('default_seasonal_component', 2))) - 1)
        self.intercept_seas_combo.setCurrentIndex(int(self.ini.get('intercept_seasonal_component', self.ini.get('default_seasonal_component', 2))) - 1)

        # Load ini settings and input the data into the UI
        self.load_ini_settings()

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

        if 'trend_method' in self.ini:
            self.trend_method_combo.setCurrentIndex(int(self.ini['trend_method']))
        else:
            self.trend_method_combo.setCurrentIndex(1)
        if int(self.intercept_method_combo.currentIndex()) == 2:
            self.intercept_seas_combo.setDisabled(False)
        else:
            self.intercept_seas_combo.setDisabled(True)

        if 'intercept_method' in self.ini:
            self.intercept_method_combo.setCurrentIndex(int(self.ini['intercept_method']))
        else:
            self.intercept_method_combo.setCurrentIndex(1)
        if int(self.intercept_method_combo.currentIndex()) == 2:
            self.intercept_seas_combo.setDisabled(False)
        else:
            self.intercept_seas_combo.setDisabled(True)

        self.mean_line.setText(self.ini.get('averaging_window', ''))

        if self.ini.get('anomaly', 'False') == 'True':
            self.anomaly_check.setChecked(True)
        else:
            self.anomaly_check.setChecked(False)

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

                max_length = max(len(s) for s in self.proxy_string)
                f.createDimension('proxy', len(self.proxy_string))
                f.createDimension('string_length', max_length)
                f.createDimension('time', len(self.time))
                f.createDimension('infl', 2)

                # Needs improvement so it works well with netCDF
                ind_var = f.createVariable('independent variable names', 'str', ('proxy',))
                ind_var[:] = np.array(self.proxy_string)
                proxy_var = f.createVariable('proxy', 'S1', ('proxy', 'string_length'))
                for k, s in enumerate(self.proxy_string):
                    proxy_var[k, :len(s)] = np.array(list(s), dtype='S1')

                time_var = f.createVariable('date', 'S10', 'time')

                dim_tuple = tuple(dim_name for dim_name in dims)
                X_var = f.createVariable('independent variable matrix', 'f4', dim_tuple + ('proxy',))
                X_var[:] = self.X
                beta_var = f.createVariable('beta', 'f4', dim_tuple[1:] + ('proxy',))
                beta_var[:] = self.betaa
                covb_var = f.createVariable('covbeta', 'f4', dim_tuple[1:] + ('proxy',))
                covb_var[:] = self.convbeta

                if len(self.trends.shape) == len(dim_tuple):
                    trend_var = f.createVariable('trend', 'f4', dim_tuple[1:] + ('infl',))
                    sig_var = f.createVariable('sig', 'f4', dim_tuple[1:] + ('infl',))
                else:
                    trend_var = f.createVariable('trend', 'f4', dim_tuple[1:])
                    sig_var = f.createVariable('sig', 'f4', dim_tuple[1:])
                trend_var[:] = self.trends
                sig_var[:] = self.signi

                frac_var = f.createVariable('fractional year', 'f4', ('time',))

                X_var.long_name = 'Independent Variable matrix'
                beta_var.long_name = 'Trend coefficient'

                frac_year = convert_datetime_to_fractional(self.time)

                time_int = np.array([str_time.strftime('%Y-%m-%d') for str_time in self.time])
                time_var[:] = time_int
                frac_var[:] = frac_year

    def data_diagnostic_changed_cell(self):
        data = self.list_of_data[self.data_list.currentRow()]

        lat_ind = self.dia_data_combo_lat.currentIndex()
        lon_ind = self.dia_data_combo_lon.currentIndex()
        alt_ind = self.dia_data_combo_alt.currentIndex()

        self.dia_data_table.setColumnCount(self.dia_data_combo_alt.count()-1)
        self.dia_data_table.setRowCount(self.dia_data_combo_lat.count()-1)

        # self.dia_proxy_table.setVerticalHeaderLabels(self.proxies[index].time.astype(str))

        self.dia_data_table.clear()
        for k in range(self.dia_data_combo_lat.count()-1):
            for kk in range(self.dia_data_combo_alt.count()-1):
                self.dia_data_table.setItem(k, kk, QTableWidgetItem(str(data.o3[:, kk, k])))

    def data_diagnostic(self):
        data = self.list_of_data[self.data_list.currentRow()]

        start_date = str(data.time[0])
        end_date = str(data.time[-1])
        self.dia_data_start.setText(start_date)
        self.dia_data_end.setText(end_date)
        if data.time is None:
            self.dia_data_time.setText('-')
        else:
            time_str = ' '.join(map(str, data.time.shape))
            self.dia_data_time.setText(time_str)
        self.dia_data_combo_lat.clear()
        if data.lat is None:
            self.dia_data_lat.setText('-')
        else:
            lat_str = ' '.join(map(str, data.lat.shape))
            self.dia_data_lat.setText(lat_str)
            self.dia_data_combo_lat.addItem('All')
            for k, i in enumerate(data.lat):
                self.dia_data_combo_lat.addItem(str(i))
        self.dia_data_combo_lon.clear()
        if data.lon is None:
            self.dia_data_lon.setText('-')
        else:
            self.dia_data_combo_lon.addItem('All')
            for k, i in enumerate(data.lon):
                self.dia_data_combo_lon.addItem(str(i))
            lon_str = ' '.join(map(str, data.lon.shape))
            self.dia_data_lon.setText(lon_str)
        self.dia_data_combo_alt.clear()
        if data.lev is None:
            self.dia_data_alt.setText('-')
        else:
            self.dia_data_combo_alt.addItem('All')
            for k, i in enumerate(data.lev):
                self.dia_data_combo_alt.addItem(str(i))
            alt_str = ' '.join(map(str, data.lev.shape))
            self.dia_data_alt.setText(alt_str)

        # self.data_diagnostic_changed_cell()

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
        else:
            sec_dim = 1
        self.dia_proxy_table.setColumnCount(sec_dim)
        self.dia_proxy_table.setRowCount(self.proxies[index].data.shape[0])

        self.dia_proxy_table.setVerticalHeaderLabels(self.proxies[index].time.astype(str))

        # Not really pretty, but works for now
        for k, i in enumerate(self.proxies[index].data):
            if sec_dim == 1:
                self.dia_proxy_table.setItem(k, 0, QTableWidgetItem(str(self.proxies[index].data[k])))
            else:
                for kk in range(sec_dim):
                    self.dia_proxy_table.setItem(k, kk, QTableWidgetItem(str(self.proxies[index].data[k, kk])))

    def update_proxy_table(self):
        # Update of the main proxy table
        self.proxy_list.setRowCount(len(self.proxies))
        # Add method combo boxes for each available proxy
        for k, i in enumerate(self.proxies):
            self.proxy_list.setItem(k, 0, QTableWidgetItem(i.name))
            methodBox = ComboMethod(self)
            self.proxy_list.setCellWidget(k, 1, methodBox)
            methodBox.currentIndexChanged.connect(lambda index, methodBox=methodBox, row=k: self.method_update(methodBox, row))
            methodBox.setCurrentIndex(i.method)

        # Add seasonal component combo boxes for each available proxy
        for k, i in enumerate(self.proxies):
            self.proxy_list.setItem(k, 0, QTableWidgetItem(i.name))
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

    def open_data_dialog(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilters(["NetCDF (*.nc)", "ASCII files (*.*)"])
        dialog.setViewMode(QFileDialog.Detail)

        if dialog.exec_():
            fileName = dialog.selectedFiles()
        else:
            return

        self.open_settings_dialog(fileName)

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
        print(fileName)

        for k, i in enumerate(fileName):
            new_proxy = load_proxy_file(i, self.ini)
            self.proxies.append(new_proxy)

        self.update_proxy_table()

    def open_settings_dialog(self, filename):
        settings = VariableWindow(self.ini, filename)
        settings.ini_signal.connect(self.update_ini_settings)
        settings.setWindowTitle('Variable Settings')
        settings.exec_()

    def update_ini_settings(self, ini):
        self.ini = ini

    def reload_data_list(self):
        self.data_list.clear()
        for i in self.list_of_data:
            self.data_list.addItem(i.name)

    def define_palettes(self):
        # Set palette
        self.palette_wrong = QPalette()
        self.palette_wrong.setColor(QPalette.Background, QColor(212, 19, 22))
        self.palette_wrong.setColor(QPalette.Base, QColor(212, 19, 22))

        self.palette_right = QPalette()
        self.palette_right.setColor(QPalette.ColorRole.WindowText, QColor(0, 170, 0))
        self.palette_right.setColor(QPalette.Text, QColor(0, 170, 0))
        self.palette_right.setColor(QPalette.Background, QColor(255, 255, 255, 0))

    def plot_options(self):
        data = self.list_of_data[self.data_list.currentRow()]
        self.dim_combo.clear()
        if self.infl_check.isChecked() == True:
            dim_num = len(self.trends.shape) - 1
        else:
            dim_num = len(self.trends.shape)

        for k in range(dim_num):
            self.dim_combo.addItem(data.dim_array[1:][k])

        self.plot_indices = self.plot_indices[:dim_num]

    def update_plot_indices(self):
        self.plot_indices[self.dim_combo.currentIndex()] = self.axis_combo.currentIndex()

    def axis_options(self):
        indices = copy.copy(self.plot_indices)
        self.axis_combo.clear()
        data = self.list_of_data[self.data_list.currentRow()]
        combo_int = self.dim_combo.currentIndex()
        dim = []
        if data.lat is not None:
            dim.append(data.lat)
        if data.lon is not None:
            dim.append(data.lon)
        if data.lev is not None:
            dim.append(data.lev)

        for k, i in enumerate(dim[combo_int]):
            self.axis_combo.addItem(str(i))
        self.axis_combo.setCurrentIndex(indices[combo_int])

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
                string = [months_str[i] for i in month_list]
                self.mean_line.setToolTip('<html><head/><body><p>Currently averaged months:</p>' + ', '.join(string) + '</p><p>Months must be written with their respective number, seperated by &quot;,&quot;. To get a yearly average, use either &quot;yearly&quot; or &quot;all&quot;.</p></body></html>')
            else:
                self.mean_line.setToolTip('<html><head/><body><p>Currently averaged months:</p>' + 'all' + '</p><p>Months must be written with their respective number, seperated by &quot;,&quot;. To get a yearly average, use either &quot;yearly&quot; or &quot;all&quot;.</p></body></html>')

    def method_update(self, methodBox, row):
        self.proxies[row].method = int(methodBox.currentIndex())
        if int(methodBox.currentIndex()) > int(self.intercept_method_combo.currentIndex()):
            self.intercept_method_combo.setCurrentIndex(int(methodBox.currentIndex()))

        if self.proxy_list.cellWidget(row, 2) is not None:
            if int(methodBox.currentIndex()) == 2:
                self.proxy_list.cellWidget(row, 2).setEnabled(True)
            else:
                self.proxy_list.cellWidget(row, 2).setEnabled(False)

    def seas_update(self, seasBox, row):
        self.proxies[row].seas_comp = seasBox.currentIndex() + 1

    def update_trend_method(self):
        self.ini['trend_method'] = int(self.trend_method_combo.currentIndex())
        if int(self.trend_method_combo.currentIndex()) == 2:
            self.trend_seas_combo.setDisabled(False)
        else:
            self.trend_seas_combo.setDisabled(True)

    def update_trend_seasonal(self):
        self.ini['trend_seasonal_component'] = int(self.trend_seas_combo.currentIndex()) + 1

    def update_intercept_seasonal(self):
        self.ini['intercept_seasonal_component'] = int(self.intercept_seas_combo.currentIndex()) + 1

    def update_intercept_method(self):
        self.ini['intercept_method'] = int(self.intercept_method_combo.currentIndex())
        if int(self.intercept_method_combo.currentIndex()) == 2:
            self.intercept_seas_combo.setDisabled(False)
        else:
            self.intercept_seas_combo.setDisabled(True)

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
        self.intercept_method_combo.setCurrentIndex(index)
        self.trend_method_combo.setCurrentIndex(index)

    def inflection_method_change(self):
        self.ini['inflection_method'] = self.infl_method_list[self.inflection_method.currentIndex()]

    def data_change(self):
        # Change the time format to the current dataset time format
        self.ini['time_format'] = self.list_of_data[self.data_list.currentRow()].time_format

    def compute_trends(self):
        self.setDisabled(True)
        self.trends, self.signi, self.diagnostic = iup_reg_model(self.list_of_data[self.data_list.currentRow()], self.proxies, self.ini)
        self.setDisabled(False)

        self.X = self.diagnostic[0]
        self.beta = self.diagnostic[1]
        self.betaa = self.diagnostic[2]
        self.convbeta = self.diagnostic[3]
        self.proxy_string = self.diagnostic[4]
        self.time = self.diagnostic[5]
        self.current_ini = copy.copy(self.ini)
        self.current_data = copy.copy(self.list_of_data[self.data_list.currentRow()])

        self.plot_button.setDisabled(False)

        # Get roughly the middle index of the variables, so it looks nicer
        self.plot_indices = np.zeros(len(self.trends.shape), dtype=int)
        for k, i in enumerate(self.plot_indices):
            self.plot_indices[k] = int(self.trends.shape[k]/2)
        self.plot_options()

    def plot_figure(self):
        # Clear the figure
        self.canvas.figure.clf()

        # Preparing Plot values
        data = self.current_data
        indices = tuple([slice(None)] + list(self.plot_indices))

        X = data.time
        Y = data.o3[indices]
        Y_trend = self.trends[tuple(self.plot_indices)]
        Y_signi = self.signi[tuple(self.plot_indices)]
        trend_string = ''

        valid_cols = ~np.isnan(self.X[indices]).all(axis=0)
        valid_rows = ~np.isnan(self.X[indices]).all(axis=1)
        Y_model = np.matmul(self.X[indices][valid_rows][:, valid_cols], self.betaa[tuple(self.plot_indices)][valid_cols])

        if 'inflection_method' in self.current_ini:
            # Loop over the amount of inflection points, to write string for the trend value textbox
            for k, i in enumerate(Y_trend):
                # trend_string += 'trend ' + str(k) + ': ' + str(round(i, 2)) + '+/-' + str(round(Y_signi[k], 2)) + '\n'
                trend_string += 'trend ' + str(k) + ': ' + str(round(i, 2)) + '%/decade' '\n'
            trend_string = trend_string[:-1]

            if self.current_ini['inflection_method'] == 'pwl':
                Y_slope = np.matmul(self.X[indices][valid_rows][:, valid_cols][:, :3], self.betaa[tuple(self.plot_indices)][valid_cols][:3])
            elif self.current_ini['inflection_method'] == 'ind':
                Y_slope = np.matmul(self.X[indices][valid_rows][:, valid_cols][:, :4], self.betaa[tuple(self.plot_indices)][valid_cols][:4])
                try:
                    Y_slope[np.where(self.time[valid_rows] == dt.datetime.strptime(self.current_ini['inflection_point'], self.current_ini['time_format']).date().replace(day=15))[0][0]] = np.nan
                except:
                    pass
        else:
            trend_string_index = [k for k, s in enumerate(np.array(self.proxy_string)[valid_cols]) if 'trend' in s]
            intercept_string_index = [k for k, s in enumerate(np.array(self.proxy_string)[valid_cols]) if 'intercept' in s]
            # X_trend_mean = np.nanmean(self.X[indices][valid_rows][:, valid_cols][:, trend_string_index], axis=1)
            # X_intercept_mean = np.nanmean(self.X[indices][valid_rows][:, valid_cols][:, intercept_string_index], axis=1)
            X_trend_mean = self.X[indices][valid_rows][:, valid_cols][:, trend_string_index[0]]
            X_intercept_mean = self.X[indices][valid_rows][:, valid_cols][:, intercept_string_index[0]]
            # beta_trend_mean = np.nanmean(self.betaa[tuple(self.plot_indices)][valid_cols][trend_string_index])
            # beta_intercept_mean = np.nanmean(self.betaa[tuple(self.plot_indices)][valid_cols][intercept_string_index])
            beta_trend_mean = self.betaa[tuple(self.plot_indices)][valid_cols][trend_string_index[0]]
            beta_intercept_mean = self.betaa[tuple(self.plot_indices)][valid_cols][intercept_string_index[0]]

            Y_slope = np.matmul(np.vstack((X_intercept_mean, X_trend_mean)).T, np.vstack((beta_intercept_mean, beta_trend_mean)))

            # Y_slope = np.matmul(self.X[indices][valid_rows][:, valid_cols][:, :2], self.betaa[tuple(self.plot_indices)][valid_cols][:2])
            # trend_string += 'trend: ' + str(round(Y_trend, 2)) + '+/-' + str(round(Y_signi, 2))
            trend_string += 'trend: ' + str(round(Y_trend, 2)) + '%/decade'

        plot_number = 1

        self.canvas.axes_list = [self.canvas.figure.add_subplot(plot_number, 1, i + 1) for i in range(plot_number)]

        bounds = [-7, -5, -3, -1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1, 3, 5, 7]
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list("", plt.get_cmap('RdBu_r')(np.arange(10, 245, 3).astype(int)))
        cmap.set_under(plt.get_cmap('RdBu_r')(0))
        cmap.set_over(plt.get_cmap('RdBu_r')(255))
        norm = mpl.colors.BoundaryNorm(bounds, cmap.N)

        for k, ax in enumerate(self.canvas.axes_list):
            ax.plot(X, Y, label='Time Series', linewidth=1.8)

            ax.plot(self.time[valid_rows], Y_model, label='Model', linewidth=1.8)
            ax.plot(self.time[valid_rows], Y_slope, path_effects=[pe.Stroke(linewidth=5, foreground='black'), pe.Normal()], label='Trend', linewidth=1.3)
            # ax.plot(self.time)
            y_label_cor = 0.025
            self.canvas.figure.text(0.45, y_label_cor, 'Time [yr]', ha='center', va='center', rotation='horizontal', fontsize=12)
            x_label_cor = 0.02
            self.canvas.figure.text(x_label_cor, 0.5, 'Number Density [molec/cm³]', ha='center', va='center', rotation='vertical', fontsize=12)
            ax.legend(loc='upper right')

            props = dict(boxstyle='round', facecolor='white', alpha=1)
            ax.text(0.05, 0.95, trend_string, transform=ax.transAxes, fontsize=10, verticalalignment='top', horizontalalignment='left', bbox=props)
        toolbar = NavigationToolbar(self.canvas, self)

        self.canvas.draw()

    def print_ini(self):
        for i in self.ini:
            print(i, self.ini[i])
        print('\n\n')


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

        # Creating empty lists for the additional proxy data
        ini['additional_proxy_path'] = np.empty(add_proxy_count, dtype='object')
        ini['additional_proxy_time_col'] = np.zeros(add_proxy_count, dtype='object')
        ini['additional_proxy_data_col'] = np.ones(add_proxy_count, dtype=int)
        ini['additional_proxy_method'] = np.ones(add_proxy_count, dtype=int)
        ini['additional_proxy_comment_symbol'] = np.empty(add_proxy_count, dtype='object')
        ini['additional_proxy_header_size'] = np.empty(add_proxy_count, dtype=int)
        ini['additional_proxy_time_format'] = np.empty(add_proxy_count, dtype='object')

    with open(ini_path, 'r') as f:
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

    return ini


def proxies_to_class(proxy_raw):
    # Convert each proxy in the list to the proxy class
    proxy_list = []
    proxy_array = np.array(proxy_raw)

    for count, proxy in enumerate(proxy_raw):
        proxy_list.append(Proxy(proxy))
        proxy_list[count].time = pd.to_datetime(pd.Series(proxy_raw.index)).dt.date.map(lambda t: t.replace(day=15))
        # proxy_list[count].time = proxy_list[count].time.to_pydatetime()
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
            date_end = np.array(i.time)[np.max(np.where(np.in1d(np.array(i.time), new_data.time))[0])]

    new_data.date_start = np.where(new_data.time == date_start)[0][0]
    new_data.date_end = np.where(new_data.time == date_end)[0][0] + 1

    for k, i in enumerate(new_proxies):
        if 'Nino' in i.name or 'ENSO' in i.name:
            # Shift the data of ENSO to incorporate the lag of the enso impact for the ozone
            enso_lag = -2
            enso = get_enso_lag(i, enso_lag, date_start, date_end)
            new_proxies[k].data = enso.data
        else:
            new_proxies[k].data = i.data[(i.time >= date_start.replace(day=15)) & (i.time <= date_end.replace(day=15))]

    return new_data, new_proxies


def convert_to_datetime(time, ini=None):
    # Converting every possible time to datetime
    # STILL NEEDS MORE OPTIONS
    if ini is not None:
        format = ini['time_format']
    else:
        format = '%Y-%m-%d'
    if isinstance(time, np.ndarray):
        if np.issubdtype(time.dtype, 'O') or np.issubdtype(time.dtype, str):
            time = np.array([dt.datetime.strptime(str(x), format).date() for x in time])
        elif (time.astype(int) == time).all():
            time = np.array([dt.datetime.strptime(str(int(x)), format).date() for x in time])
        elif np.issubdtype(time.dtype, np.datetime64):
            time = pd.to_datetime(time)

    return time


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


def parse_time(value):
    # Convert value to string
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

    if 'default_proxy_limit' in ini:
        if int(ini['default_proxy_limit']) == 1:
            proxy_list = default_boundary_settings(proxy_list)

    for i in proxy_list:
        i.method = int(ini.get('default_proxy_method', 2))
        i.seas_comp = int(ini.get('default_seasonal_component', 3))

    return proxy_list


def load_proxy_file(fileName, ini, proxy_col=None):
    proxy_raw = pd.read_csv(fileName, comment=ini['comment_symbol'], delim_whitespace=True, header=None, index_col=0)
    proxy_raw.dropna(axis=1, how='all', inplace=True)

    try:
        proxy_raw.index = pd.to_datetime(proxy_raw.index, format=ini['time_format']).date
    except:
        raise Exception('The time format is not correct. Please follow the datetime format: hhttps://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior\nFor exammple "%Y-%M-%d" for the date format "2012-01-17"')

    # Trying to get the proxy name by using the file name
    name = fileName.split('/')[-1].split('.')[0]
    proxy = Proxy(name)

    proxy.time = pd.Series(proxy_raw.index).apply(lambda dt: dt.replace(day=15))
    if proxy_col is not None:
        proxy.data = np.array(proxy_raw)[:, proxy_col]
    else:
        proxy.data = np.array(proxy_raw)[:, 0]

    return proxy


def load_additional_proxies(proxies, ini):
    if 'additional_proxy_path' not in ini:
        return proxies
    add_proxies = []
    # Loop over every path in the ini file
    for k, i in enumerate(ini['additional_proxy_path']):
        if ',' in str(ini['additional_proxy_time_col'][k]):
            time_index_list = np.array(ini['additional_proxy_time_col'][k].split(','), dtype=int)
            proxy_data = pd.read_csv(i, sep='\s+', index_col=time_index_list[0])
        else:
            proxy_data = pd.read_csv(i, sep='\s+', index_col=int(ini['additional_proxy_time_col'][k]))
        add_proxies.append(Proxy(proxy_data.columns.values[int(ini['additional_proxy_data_col'][k])-1]))
        proxy_data.dropna(axis=1, how='all', inplace=True)
        proxy_data.index = pd.to_datetime(proxy_data.index, format=ini['additional_proxy_time_format'][k]).date

        add_proxies[k].data = np.array(proxy_data)[:, int(ini['additional_proxy_data_col'][k])-1]
        if ',' in ini['additional_proxy_time_col']:
            date = np.empty(len(proxy_data.index), dtype='object')
            for kk, ii in enumerate(date):
                date[kk] = dt.datetime(np.array(proxy_data.index)[kk], np.array(proxy_data)[time_index_list[1]+1, kk], 15).date()
            add_proxies[k].time = pd.Series(date)
        else:
            add_proxies[k].time = pd.Series(proxy_data.index).apply(lambda dt: dt.replace(day=15))
        add_proxies[k].method = ini['additional_proxy_method'][k]

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

        var_list = ['o3_var', 'time_var', 'lat_var', 'lon_var', 'lev_var']
        group_name = ini.get('group_name')
        group = dataset[group_name] if group_name else dataset

        # Create a dataset class
        try:
            data = Dataset(filename.split('/')[-1].split('.')[0])
        except:
            data = Dataset('New Dataset')

        # Loop over each key in the dictionary and look for the variable names
        for var_name, var_key in ini.items():
            if var_name not in var_list:
                # If the dictionary key is not one of the variable names, skip to the next loop
                continue
            try:
                setattr(data, var_name.split('_')[0], group.variables[var_key][:])
            except:
                continue
                # raise Exception('f"Variable "var_key" not found in the netCDF file.')

        # Transposing the ozone data
        dependencies = group.variables[ini['o3_var']].dimensions
        var_names = {'time': [ini.get('time_var'), 'date', 'time'], 'lat': [ini.get('lat_var'), 'latitude', 'lat'], 'lon': [ini.get('lon_var'), 'longitude', 'lon'], 'alt': [ini.get('lev_var'), 'altitude', 'alt', 'level', 'lev']}
        order = ['time', 'lat', 'lon', 'alt']
        permutation = []
        dim_array = []

        for dim_name in order:
            found = False
            for possible_name in var_names[dim_name]:
                if possible_name in dependencies:
                    permutation.append(dependencies.index(possible_name))
                    dim_array.append(dim_name)
                    found = True
                    break
            if not found:
                permutation.append(None)

        data.o3 = np.transpose(data.o3, [index for index in permutation if index is not None])
        data.o3 = np.ma.masked_invalid(data.o3)
        data.dim_array = dim_array
        data.time = convert_to_datetime(data.time, ini)
        data.time_format = ini['time_format']

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
                f.createDimension('proxy', len(diagnostic[3]))
                f.createDimension('string_length', max_length)
                f.createDimension('time', len(diagnostic[4]))
                f.createDimension('infl', 2)

                # Needs improvement so it works well with netCDF
                proxy_var = f.createVariable('proxy', 'S1', ('proxy', 'string_length'))
                for k, s in enumerate(diagnostic[3]):
                    proxy_var[k, :len(s)] = np.array(list(s), dtype='S1')

                time_var = f.createVariable('date', 'S10', 'time')

                dim_tuple = tuple(dim_name for dim_name in dims)
                X_var = f.createVariable('independent variable matrix', 'f4', dim_tuple + ('proxy',))
                X_var[:] = diagnostic[0]
                beta_var = f.createVariable('beta', 'f4', dim_tuple[1:] + ('proxy',))
                beta_var[:] = diagnostic[2]
                covb_var = f.createVariable('covbeta', 'f4', dim_tuple[1:] + ('proxy',))
                covb_var[:] = diagnostic[3]

                if len(trends.shape) == len(dim_tuple):
                    trend_var = f.createVariable('trend', 'f4', dim_tuple[1:] + ('infl',))
                    sig_var = f.createVariable('sig', 'f4', dim_tuple[1:] + ('infl',))
                else:
                    trend_var = f.createVariable('trend', 'f4', dim_tuple[1:])
                    sig_var = f.createVariable('sig', 'f4', dim_tuple[1:])
                trend_var[:] = trends
                sig_var[:] = signi

                frac_var = f.createVariable('fractional year', 'f4', ('time',))

                X_var.long_name = 'Independent Variable matrix'
                beta_var.long_name = 'Trend coefficient'

                frac_year = convert_datetime_to_fractional(diagnostic[4])

                time_int = np.array([str_time.strftime('%Y-%m-%d') for str_time in diagnostic[4]])
                time_var[:] = time_int
                frac_var[:] = frac_year


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
    intercept_ind = np.where(np.array(X_string) == 'intercept')[0]

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


def get_X_1(inflection_index, nanmask, ini, X_1_string, data):
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
                    val[:inflection_index] = 1
                else:
                    val[inflection_index:] = 1

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
                    val[inflection_index:] = np.arange(1, len(nanmask)-inflection_index+1)
            elif ini['inflection_method'] == 'ind':
                if first_part == True:  # UGLY, needs fixing
                    val[:inflection_index] = np.arange(1, inflection_index+1)
                    first_part = False
                else:
                    val[inflection_index:] = np.arange(1, len(nanmask)-inflection_index+1)

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

            # X_1[:, col] = val * np.sin((2 * np.pi * np.arange(1, len(nanmask)+1)) / 12)
            # col += 1
            # X_1[:, col] = val * np.cos((2 * np.pi * np.arange(1, len(nanmask)+1)) / 12)
            # col += 1
            # X_1[:, col] = val * np.sin((4 * np.pi * np.arange(1, len(nanmask)+1)) / 12)
            # col += 1
            # X_1[:, col] = val * np.cos((4 * np.pi * np.arange(1, len(nanmask)+1)) / 12)
            # col += 1
        elif method == 3:
            month_array = np.array(pd.to_datetime(data.time[data.date_start:data.date_end]).month)
            for kk in range(12):
                X_1[:, col] = val
                X_1[np.where((month_array % 13) != kk + 1), col] = 0
                col += 1

    X_1[~nanmask, :] = np.nan

    return X_1


def get_X_2(proxies, nanmask, X_proxy_size, ini, it, data):
    mask_time = np.where(nanmask == True)[0]    # Array which has every index of actual values of the original data
    X_2 = np.zeros((len(nanmask), X_proxy_size), dtype=float)  # Size of the proxy part of the X matrices depends on which method to use for each proxy as well as the seasonal cycle
    X_2[:] = np.nan

    # Get the latitude, longitude and altitude of the dataset for AOD and limits
    ind = 0
    lat = None
    lon = None
    alt = None

    for k, i in enumerate(data.dim_array):
        if i == 'lat' and data.lat is not None:
            try:
                lat = data.lat[it.multi_index[ind]]
            except:
                lat = data.lat[it.multi_index]
            ind += 1
        elif i == 'lon' and data.lon is not None:
            try:
                lon = data.lon[it.multi_index[ind]]
            except:
                lon = data.lon[it.multi_index]
            ind += 1
        elif i == 'alt' and data.lev is not None:
            try:
                alt = data.lev[it.multi_index[ind]]
            except:
                alt = data.lev[it.multi_index]
            ind += 1

    col = 0

    # Setting columns as NaNs if they don't fall inbetween the min and max lat and alt specifications of the proxy
    for i in proxies:
        if i.method == 0:
            continue
        if not is_between(lat, i.lat_min, i.lat_max) or not is_between(alt, i.alt_min, i.alt_max):
            if i.method == 1:
                X_2[:, col] = np.nan
                col += 1
            elif i.method == 2:
                for kk in range(i.seas_comp*2 + 1):
                    X_2[:, col] = np.nan
                    col += 1
            elif i.method == 3:
                for kk in range(12):
                    X_2[:, col] = np.nan
                    col += 1
            continue

        # NOT A GOOD SOLUTION, NEEDS IMPROVEMENT
        # Get the correct proxy data depending on latitude
        if len(i.data.shape) > 1:
            if lat in i.lat:
                proxy_data = i.data[nanmask, np.where(i.lat == lat)]
            else:
                closest_lat = sorted([(lat_close, abs(lat_close - lat)) for lat_close in i.lat], key=lambda x: x[1:])[:2]
                lat1, lat2 = closest_lat[0][0], closest_lat[1][0]
                data1, data2 = i.data[nanmask, np.where(i.lat == lat1)[0][0]], i.data[nanmask, np.where(i.lat == lat2)[0][0]]
                temp_data = np.empty(len(data1))
                for kk, ii in enumerate(data1):
                    temp_data[kk] = np.interp(lat, [lat1, lat2], [data1[kk], data2[kk]])
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
    # X_2 = X_2[:, ~np.all(np.isnan(X_2), axis=0)]
    X_2[~nanmask] = np.nan

    return X_2


def normalize(X_2):

    for k in range(X_2.shape[1]):
        current_proxy = X_2[X_2[:, k] != 0, k]
        X_2[X_2[:, k] != 0, k] = ((current_proxy - np.nanmin(current_proxy)) / (np.nanmax(current_proxy) - np.nanmin(current_proxy)))*2 - 1

    return X_2


def calc_trend(X, data_arr, ini, X_string):
    nanmask = ~np.isnan(data_arr.filled(np.nan))

    # Get the indices of the intercept and trend to get a mean value for the coefficient
    trend_string_index = [j for j, s in enumerate(X_string) if 'trend' in s]
    trend_index = trend_string_index[0]     # To get the first trend index so that the autoregression works

    try:
        beta = np.matmul(np.matmul(np.linalg.inv(np.matmul(np.transpose(X), X)), np.transpose(X)), data_arr[nanmask])
    except:
        print('Calculation failed: NaNs')
        return np.nan, np.nan, np.nan, np.nan, np.nan

    # Carlos autoregression program, not yet completely reworked

    fity = np.matmul(X, beta)
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
    for i in range(len(X))[1:]:  # I am starting from the second line
        for g in range(len(X)):
            if i == g:
                if X[i, 1] - X[i - 1, 1] > 1:
                    P[i, g] = np.sqrt(1 - phi ** 2)
                    epsilon[i] = N[i] * np.sqrt(1 - phi ** 2)
                else:
                    P[i, g] = 1
                    epsilon[i] = N[i] - phi * N[i - 1]
            elif i == g + 1:
                if X[i, 1] - X[i - 1, 1] > 1:
                    P[i, g] = 0
                else:
                    P[i, g] = -phi
    P[0, 0] = np.sqrt(1 - phi ** 2)  # this is the first line
    epsilon[0] = N[0] * np.sqrt(1 - phi ** 2)

    Xstar = np.matmul(P, X)
    Ystar = np.matmul(P, data_arr[nanmask])
    try:
        betaa = np.matmul(np.matmul(np.linalg.inv(np.matmul(np.transpose(Xstar), Xstar)), np.transpose(Xstar)), Ystar)
        covbetaa = np.var(epsilon) * (np.linalg.inv(np.matmul(np.transpose(Xstar), Xstar)))
    except:
        print('Two or more proxies are dependent to each other. A linear regression is not possible. Please either turn of linear regression or turn off one of the proxies.')
        return np.nan, np.nan, np.nan, np.nan, np.nan

    Xmask2, Ymask2 = np.zeros((len(X), X.shape[1])), np.zeros((len(X)))
    k = 0
    timok = list()
    for i in range(len(X)):
        if i == 0:
            Xmask2[k, 0:len(Xstar[i, :])] = Xstar[i, :]
            Ymask2[k] = Ystar[i]
            k = k + 1
            timok.append(i)
            continue
        if X[i, trend_index] - X[i - 1, trend_index] == 1:
            Xmask2[k, 0:len(Xstar[i, :])] = Xstar[i, :]
            Ymask2[k] = Ystar[i]
            k = k + 1
            timok.append(i)
        elif len(trend_string_index) >= 6:
            if np.nansum(X[:, trend_string_index], axis=1)[i] - np.nansum(X[:, trend_string_index][i - 1]) == 1:
                Xmask2[k, 0:len(Xstar[i, :])] = Xstar[i, :]
                Ymask2[k] = Ystar[i]
                k = k + 1
                timok.append(i)
            else:
                continue
        else:
            # print('gap in X1, ',i,k)
            continue
    Xmask2ok = Xmask2[0:k, :]

    # Calculate the trend coefficients
    try:
        if len(beta) == 1 or len(Xmask2ok) < 10:
            trenda_z = np.nan
            siga_z = np.nan
        else:
            if ini.get('anomaly', '') == 'True' and ini.get('anomaly_method', 'rel') == 'rel':
                trenda_z = np.nanmean(betaa[trend_string_index]) * 120 * 100
                siga_z = np.abs(np.nanmean(betaa[trend_string_index]) / np.sqrt(np.nanmean(np.diag(covbetaa)[trend_string_index])))
            elif ini.get('anomaly', '') == 'True' and ini.get('anomaly_method', 'abs') == 'rel':
                print('NOT YET FINISHED')
            else:
                siga_z = np.abs(np.nanmean(betaa[trend_string_index]) / np.sqrt(np.nanmean(np.diag(covbetaa)[trend_string_index])))
                if ini.get('o3_var_unit').split('_')[0] == 'anom':
                    trenda_z = np.nanmean(betaa[trend_string_index]) * 120
                else:
                    trenda_z = np.nanmean(betaa[trend_string_index]) * 120 * 100 / np.nanmean(data_arr)

    except:
        trenda_z = np.nan
        siga_z = np.nan
        print('Failed to calculate the trend and significants')

    return trenda_z, siga_z, beta, betaa, np.diag(covbetaa)


# Main program to run
def iup_reg_model(data, proxies, ini):
    data, proxies = get_proxy_time_overlap(ini, proxies, data)

    # Get index of the inflection point
    inflection_index = get_inflection_index(ini, data)

    # Creating the empty arrays for the trends and the uncertainty
    if 'inflection_method' not in ini:
        trenda_z = np.empty(np.atleast_1d(data.o3[0, ...]).shape) * np.nan
        siga_z = np.empty(np.atleast_1d(data.o3[0, ...]).shape) * np.nan
        X_string = ['intercept', 'trend']
    elif ini['inflection_method'] == 'pwl':
        trenda_z = np.empty(np.atleast_1d((data.o3[0, ...] + (2,))).shape) * np.nan
        siga_z = np.empty(np.atleast_1d((data.o3[0, ...] + (2,))).shape) * np.nan
        X_string = ['intercept', 'trend', 'piece-wise-linear-trend']
    elif ini['inflection_method'] == 'ind':
        trenda_z = np.empty(np.atleast_1d((data.o3[0, ...] + (2,))).shape) * np.nan
        siga_z = np.empty(np.atleast_1d((data.o3[0, ...] + (2,))).shape) * np.nan
        X_string = ['intercept', 'independent trend first part', 'intercept', 'independent trend second part']

    if 'trend_method' not in ini:
        ini['trend_method'] = 1
    if 'intercept_method' not in ini:
        ini['intercept_method'] = 1

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

    if check == 0:
        X_all = np.empty((data.o3[data.date_start:data.date_end, ...].shape + (len(X_string),)), dtype='f4') * np.nan

    elif check == 1:
        X_all = np.empty(((len(np.unique(time.year)),) + data.o3[0, ...].shape + (len(X_string),)), dtype='f4') * np.nan
        for i in proxies:
            for kk, ii in enumerate(np.unique(time.year)):
                if len(np.nonzero(i.data[np.where(time.year == ii)])[0]) / len(np.where(time.year == ii)[0]) <= float(ini.get('skip_percentage', 0.75)):
                    i.data[kk] = np.nan
                    continue
                i.data[kk] = np.nanmean(i.data[np.where(time.year == ii)])
            i.data = i.data[:len(np.unique(time.year))]
    elif check == 2:
        month_index = re.split(r',\s*', ini.get('averaging_window', ''))
        month_index = np.array([int(num) for num in month_index])
        X_all = np.empty(((len(np.unique(time.year)),) + data.o3[0, ...].shape + (len(X_string),)), dtype='f4') * np.nan
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
    beta_all = np.empty((data.o3[0, ...].shape + (len(X_string),)), dtype='f4') * np.nan
    betaa_all = np.empty((data.o3[0, ...].shape + (len(X_string),)), dtype='f4') * np.nan

    # Looping over every dimension but the first (time), to calculate the trends for every latitude, longitude and altitude
    it = np.nditer(data.o3[0, ...], flags=['multi_index'])

    while not it.finished:
        print(it.multi_index)

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
                # if len(data_arr[np.where(time.year == i)][np.in1d(time[time.year == i].month, month_index)].nonzero()[0])/len(month_index) <= float(ini.get('skip_percentage', 0.75)):
                #     data_arr[k] = np.nan
                #     continue
                # data_arr[k] = np.nanmean(data_arr[np.where(time.year == i)][np.in1d(time[time.year == i].month, month_index)])
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
            print('Not long enough')
            it.iternext()
            continue

        X_1 = get_X_1(inflection_index, nanmask, ini, X_1_string, data)
        X_2 = get_X_2(proxies, nanmask, X_proxy_size, ini, it, data)

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
        trenda_z[it.multi_index], siga_z[it.multi_index], beta, betaa, covbetaa = calc_trend(X_clean, data_arr, ini, np.array(X_string)[~np.all(np.isnan(X), axis=0)])

        # Save X, beta and betaa
        X_all[(slice(None),) + it.multi_index + (slice(None),)][np.ix_(~row_mask, ~col_mask)] = X_clean
        beta_all[it.multi_index + (slice(None),)][~col_mask] = beta
        betaa_all[it.multi_index + (slice(None),)][~col_mask] = betaa

        # Go to next iteration:
        it.iternext()
    diagnostic = [X_all, beta_all, betaa_all, np.nan, X_string, data.time[data.date_start:data.date_end][time_log]]

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

def iup_ui(ui=False):

    parser = argparse.ArgumentParser(description="The IUP Regression Model can compute trends from different .netCDF ozone files with a range of default proxies aswell as the option to include additional proxies.")
    parser.add_argument('-u', '--ui', action='store_true', help='The IUP Regression Model will run with its user interface.')
    args = parser.parse_args()
    if args.ui:
        ui = True

    if not ui:
        ini = load_config_ini('config folder/config.ini')
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
