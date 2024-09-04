import sys
import numpy as np
import pandas as pd
import copy
import netCDF4 as nc
import datetime as dt

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


class comboMethod(QtWidgets.QComboBox):
    def __init__(self, parent):
        super().__init__(parent)
        self.addItems(['disable', 'single', 'harmonics', '12 months'])


# Empty "canvas" for plotting
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure()
        # self.axes =fig.add_subplot(111)
        super().__init__(fig)
        self.axes_list = []


# Popup window to set the variable names to load data
class SettingsWindow(QtWidgets.QDialog):
    ini_signal = pyqtSignal(dict)
    def __init__(self, settings_ini):
        super(SettingsWindow, self).__init__()
        uic.loadUi('settings.ui', self)

        self.ini = settings_ini

        self.load_settings()

        # connect buttons
        self.bttn_ok.clicked.connect(self.save_settings)
        self.bttn_cancel.clicked.connect(self.close)

    def load_settings(self):
        # Load all ini settings for loading data and proxy and writes it into the settings window
        if 'o3_var' in self.ini:
            self.data_o3_var.setText(self.ini['o3_var'])

        if 'time_var' in self.ini:
            self.data_time_var.setText(self.ini['time_var'])

        if 'lat_var' in self.ini:
            self.data_lat_var.setText(self.ini['lat_var'])

        if 'lon_var' in self.ini:
            self.data_lon_var.setText(self.ini['lon_var'])

        if 'lev_var' in self.ini:
            self.data_alt_var.setText(self.ini['lev_var'])

        if 'time_format' in self.ini:
            self.data_time_form.setText(self.ini['time_format'])
            self.proxy_time_form.setText(self.ini['time_format'])
        else:
            self.data_time_form.setText('%Y-%m-%d')
            self.proxy_time_form.setText('%Y-%m-%d')

        if 'comment_symbol' in self.ini:
            self.proxy_comm.setText(self.ini['comment_symbol'])
        else:
            self.proxy_comm.setText('#')

        if 'header_size' in self.ini:
            self.proxy_header.setText(self.ini['header_size'])
        else:
            self.proxy_header.setText(None)

    def save_settings(self):
        # Saves all settings and closes the settings window
        print(self.proxy_header.text() == '')

        # Change ini
        if self.proxy_header.text() != '':
            self.ini['header_size'] = self.proxy_header.text()
        if self.proxy_comm.text() != '':
            self.ini['comment_symbol'] = self.proxy_comm.text()
        if self.data_time_var.text() != '':
            self.ini['time_var'] = self.data_time_var.text()
        if self.data_lat_var.text() != '':
            self.ini['lat_var'] = self.data_lat_var.text()
        if self.data_lon_var.text() != '':
            self.ini['lon_var'] = self.data_lon_var.text()
        if self.data_alt_var.text() != '':
            self.ini['lev_var'] = self.data_alt_var.text()
        if self.data_time_form.text() != '':
            self.ini['time_format'] = self.data_time_form.text()
        if self.data_o3_var.text() != '':
            self.ini['o3_var'] = self.data_o3_var.text()

        self.ini_signal.emit(self.ini)
        self.accept()


# The UI and its functions
class AppWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('main.ui', self)
        self.setWindowTitle("IUP Regression Model")
        self.setWindowIcon(QIcon('iupLogo.png'))

        # Loading default data and proxies
        self.ini = load_config_ini('config.ini')
        self.list_of_data = []
        if 'data_path' in self.ini:
            try:
                data = load_netCDF(self.ini['data_path'], self.ini)
            except:
                print('Error in loading the data file.')
        self.list_of_data.append(data)
        self.data_list.addItem(data.name)

        self.proxies = load_default_proxies(self.ini)
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
        # self.menu_load_settings.triggered.connect(self.open_settings_dialog)
        self.menu_save.triggered.connect(self.save_file)

        # Load ini settings and input the data into the UI
        self.load_ini_settings()

    def load_ini_settings(self):

        if 'inflection_point' in self.ini:
            self.inflection_point.setText(dt.datetime.strftime(dt.datetime.strptime(self.ini['inflection_point'], self.ini['time_format']).date(), '%Y-%m'))
        else:
            self.inflection_point.setText('YYYY-MM')

        if 'inflection_point' in self.ini and 'inflection_method' in self.ini:
            if self.ini['inflection_method'] == 'ind':
                self.inflection_method.setCurrentIndex(0)
            elif self.ini['inflection_method'] == 'pwl':
                self.inflection_method.setCurrentIndex(1)
            self.infl_check.setChecked(True)

        if 'start_date' in self.ini:
            self.start_date.setText(dt.datetime.strftime(dt.datetime.strptime(self.ini['start_date'], self.ini['time_format']).date(), '%Y-%m'))
        else:
            self.start_date.setText('YYYY-MM')

        if 'end_date' in self.ini:
            self.end_date.setText(dt.datetime.strftime(dt.datetime.strptime(self.ini['end_date'], self.ini['time_format']).date(), '%Y-%m'))
        else:
            self.end_date.setText('YYYY-MM')

        self.ini['time_format'] = '%Y-%m'
        self.trend_method_combo.setCurrentIndex(int(self.ini['trend_method']))
        self.intercept_method_combo.setCurrentIndex(int(self.ini['intercept_method']))

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
        for k, i in enumerate(self.proxies):
            self.proxy_list.setItem(k, 0, QTableWidgetItem(i.name))
            methodBox = comboMethod(self)
            self.proxy_list.setCellWidget(k, 1, methodBox)
            methodBox.currentIndexChanged.connect(lambda index, methodBox=methodBox, row=k: self.method_update(methodBox, row))
            methodBox.setCurrentIndex(i.method)
        self.proxy_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.proxy_list.setHorizontalHeaderLabels(["Proxy", "Method"])

        # Update of the combo box for diagnostic
        self.dia_proxy_combo.clear()
        for k, i in enumerate(self.proxies):
            self.dia_proxy_combo.addItem(i.name)
        self.proxy_diagnostic(0)

    def open_data_dialog(self):

        self.open_settings_dialog()

        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilters(["NetCDF (*.nc)", "ASCII files (*.*)"])
        dialog.setViewMode(QFileDialog.Detail)

        if dialog.exec_():
            fileName = dialog.selectedFiles()
        else:
            return

        for i in fileName:
            data = load_netCDF(i, self.ini)
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

    def open_settings_dialog(self):
        settings = SettingsWindow(self.ini)
        settings.ini_signal.connect(self.update_ini_settings)
        settings.setWindowTitle('Load Settings')
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
            self.ini[self.sender().objectName()] = dt.datetime.strftime(dt.datetime.strptime(str(self.sender().text()), '%Y-%m'), self.ini['time_format'])
        except:
            checkbox.setChecked(False)
            checkbox.setPalette(self.palette_wrong)
            self.ini.pop(self.sender().objectName(), None)

    def method_update(self, methodBox, row):
        self.proxies[row].method = int(methodBox.currentIndex())
        if int(methodBox.currentIndex()) > int(self.intercept_method_combo.currentIndex()):
            self.intercept_method_combo.setCurrentIndex(int(methodBox.currentIndex()))

    def all_proxy_method_change(self):
        index = int(self.all_proxy_method.currentIndex()) - 1
        if index < 0:       # Doesn't do anything if ComboBox changes to "mixed"
            return

        for row in range(self.proxy_list.rowCount()):
            combo_box = self.proxy_list.cellWidget(row, 1)
            combo_box.setCurrentIndex(index)
        self.intercept_method_combo.setCurrentIndex(index)

    def inflection_method_change(self):
        self.ini['inflection_method'] = self.infl_method_list[self.inflection_method.currentIndex()]

    def data_change(self):
        print(self.sender().currentRow())

    def compute_trends(self):
        self.setDisabled(True)
        self.trends, self.signi, self.diagnostic = iup_reg_model(self.list_of_data[self.data_list.currentRow()], self.proxies, self.ini)
        self.setDisabled(False)

        self.X = self.diagnostic[0]
        self.beta = self.diagnostic[1]
        self.betaa = self.diagnostic[2]
        self.proxy_string = self.diagnostic[3]
        self.time = self.diagnostic[4]
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
            Y_slope = np.matmul(self.X[indices][valid_rows][:, valid_cols][:, :2], self.betaa[tuple(self.plot_indices)][valid_cols][:2])
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

    if 'default_proxy_method' in ini:
        ini['additional_proxy_method'] = ini['additional_proxy_method'] * int(ini['default_proxy_method'])

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
        date_start = dt.datetime.strptime(ini['start_date'], ini['time_format']).date().replace(day=15)
        if date_start < new_data.time[0]:
            date_start = new_data.time[0]
    else:
        date_start = new_data.time[0]
    if date_start < np.array(new_proxies[0].time)[0]:
        date_start = np.array(new_proxies[0].time)[0]

    if 'end_date' in ini:
        date_end = dt.datetime.strptime(ini['end_date'], ini['time_format']).date().replace(day=15)
        if date_end > new_data.time[-1]:
            date_end = new_data.time[-1]
            # raise Exception('The input for the end date of the trend calculation is later than the last date of the time series.')
    else:
        date_end = new_data.time[-1]
    if date_end > np.array(new_proxies[0].time)[-1]:
        date_end = np.array(new_proxies[0].time)[-1]

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


def load_default_proxies(ini):
    path = ini['proxy_path']
    # NEEDS TO BE MORE FLEXIBLE
    format = '%Y%m'

    proxy_raw = pd.read_fwf(path, index_col=0)
    proxy_raw.dropna(axis=1, how='all', inplace=True)
    try:
        proxy_raw.index = pd.to_datetime(proxy_raw.index, format=format).date
    except:
        raise Exception('The time format is not correct. Please follow the datetime format: hhttps://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior\nFor exammple "%Y-%M-%d" for the date format "2012-01-17"')

    # Convert raw data to the proxy class
    proxy_list = proxies_to_class(proxy_raw)

    # Load AOD data
    path = ini['aod_path']
    aod = Proxy('AOD')

    aod_data = np.genfromtxt(path, skip_header=1)
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

    proxy_list = default_boundary_settings(proxy_list)

    if 'default_proxy_method' in ini:
        for k, i in enumerate(proxy_list):
            proxy_list[k].method = int(ini['default_proxy_method'])

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
            proxy_data = pd.read_csv(i, delim_whitespace=True, index_col=time_index_list[0])
        else:
            proxy_data = pd.read_csv(i, delim_whitespace=True, index_col=ini['additional_proxy_time_col'][k])
        add_proxies.append(Proxy(proxy_data.columns.values[ini['additional_proxy_data_col'][k]-1]))
        proxy_data.dropna(axis=1, how='all', inplace=True)
        proxy_data.index = pd.to_datetime(proxy_data.index, format=ini['additional_proxy_time_format'][k]).date

        add_proxies[k].data = np.array(proxy_data)[:, ini['additional_proxy_data_col'][k]-1]
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
        var_names = {'time': ['date', 'time'], 'lat': ['latitude', 'lat'], 'lon': ['longitude', 'lon'], 'alt': ['altitude', 'alt', 'level', 'lev']}
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
    if 'inflection_point' in ini:
        inflection_date = dt.datetime.strptime(ini['inflection_point'], ini['time_format']).date()
    else:
        return inflection_index

    for k, i in enumerate(data.time.astype(dt.datetime)):
        if i.year == inflection_date.year and i.month == inflection_date.month:
            inflection_index = k
    inflection_index = inflection_index - data.date_start

    return inflection_index


def calc_proxy_size(proxies):
    X_proxy_size = 0
    X_2_string = []
    size_array = [0, 1, 5, 12]
    method_name = ['disabled', 'singular', 'harmonically', 'month-of-the-year']
    for i in proxies:
        X_proxy_size = X_proxy_size + size_array[i.method]
        for k in range(size_array[i.method]):
            X_2_string.append(i.name + ' - ' + method_name[i.method] + ' - ' + str(k + 1))

    return X_proxy_size, X_2_string


def default_boundary_settings(proxy_list):
    proxy_list[0].alt_max = 25000   # Only use ENSO under 25 km; NEEDS A CHANGE TO INCLUDE DIFFERENT ALT UNITS
    proxy_list[8].alt_max = 25000   # Only use AOD under 25 km; NEEDS A CHANGE TO INCLUDE DIFFERENT ALT UNITS
    proxy_list[4].lat_min = 0       # Only use EHF NH over 0°
    proxy_list[5].lat_max = 0       # Only use EHF SH under 0°
    proxy_list[6].lat_min = 0       # Only use AO over 0°
    proxy_list[7].lat_max = 0       # Only use AAO under 0°

    return proxy_list


def get_X_1(inflection_index, nanmask, ini):
    if 'inflection_method' not in ini:
        X_1 = np.zeros((len(nanmask), 2), dtype=float)
        X_1[:, 0] = 1
        X_1[:, 1] = np.arange(1, len(nanmask)+1)
    elif ini['inflection_method'] == 'pwl':
        X_1 = np.zeros((len(nanmask), 3), dtype=float)
        X_1[:, 0] = 1
        X_1[:, 1] = np.arange(1, len(nanmask)+1)
        X_1[inflection_index:, 2] = np.arange(1, len(nanmask)-inflection_index+1)
    elif ini['inflection_method'] == 'ind':
        X_1 = np.zeros((len(nanmask), 4), dtype=float)
        X_1[:inflection_index, 0] = 1
        X_1[:inflection_index, 1] = np.arange(1, inflection_index+1)
        X_1[inflection_index:, 2] = 1
        X_1[inflection_index:, 3] = np.arange(1, len(nanmask)-inflection_index+1)
    else:
        raise Exception('The inflection method in the config.ini file is not being recognized. Either use "pwl" for piece-wise linear trends or "ind" for independent trends. If none of these should be used, please delete the inflection method line or comment it out with "#".')

    X_1[~nanmask, :] = np.nan

    return X_1


def get_X_2(proxies, nanmask, X_proxy_size, ini, it, data):
    mask_time = np.where(nanmask == True)[0]    # Array which has every index of actual values of the original data
    X_2 = np.zeros((len(nanmask), X_proxy_size + int(ini['number_of_seasonal_terms'])*2), dtype=float)  # Size of the proxy part of the X matrices depends on which method to use for each proxy as well as the seasonal cycle
    X_2[:] = np.nan

    # Get the latitude, longitude and altitude of the dataset for AOD and limits
    ind = 0
    lat = None
    lon = None
    alt = None

    for k, i in enumerate(data.dim_array):
        if i == 'lat' and data.lat is not None:
            lat = data.lat[it.multi_index[ind]]
            ind += 1
        elif i == 'lon' and data.lon is not None:
            lon = data.lon[it.multi_index[ind]]
            ind += 1
        elif i == 'alt' and data.lev is not None:
            alt = data.lev[it.multi_index[ind]]
            ind += 1

    col = 0
    # Loop for all seasonal terms; SHOULD BE OPTIONAL
    for k in range(int(ini['number_of_seasonal_terms'])):
        X_2[nanmask, col] = np.sin((k+1)*2 * np.pi * mask_time / 12)
        col += 1
        X_2[nanmask, col] = np.cos((k+1)*2 * np.pi * mask_time / 12)
        col += 1

    # Setting columns as NaNs if they don't fall inbetween the min and max lat and alt specifications of the proxy
    for i in proxies:
        if not is_between(lat, i.lat_min, i.lat_max) or not is_between(alt, i.alt_min, i.alt_max):
            if i.method == 1:
                X_2[:, col] = np.nan
                col += 1
            elif i.method == 2:
                for kk in range(5):
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
            X_2[nanmask, col] = proxy_data * np.sin((2 * np.pi * mask_time)/12)
            col += 1
            X_2[nanmask, col] = proxy_data * np.cos((2 * np.pi * mask_time)/12)
            col += 1
            X_2[nanmask, col] = proxy_data * np.sin((4 * np.pi * mask_time)/12)
            col += 1
            X_2[nanmask, col] = proxy_data * np.cos((4 * np.pi * mask_time)/12)
            col += 1
        elif i.method == 3:
            month_array = np.array(pd.to_datetime(data.time[data.date_start:data.date_end]).month)
            for kk in range(12):
                X_2[nanmask, col] = proxy_data
                X_2[np.where((month_array % 12) != kk+1), col] = 0
                # X_2[np.where((mask_time % 12) != kk), col] = 0
                col += 1

    # Removing all columns with only NaNs (columns that got skipped because of limitations)
    # X_2 = X_2[:, ~np.all(np.isnan(X_2), axis=0)]
    X_2[~nanmask] = np.nan

    return X_2


def normalize(X_2):

    for k in range(X_2.shape[1]):
        current_proxy = X_2[X_2[:, k] != 0, k]
        # logic = X_2[X_2[:, k] != 0, k]
        X_2[X_2[:, k] != 0, k] = (current_proxy - np.nanmin(current_proxy)) / (np.nanmax(current_proxy) - np.nanmin(current_proxy))

    return X_2


def calc_trend(X, data_arr, ini):
    nanmask = ~data_arr.mask

    try:
        beta = np.matmul(np.matmul(np.linalg.inv(np.matmul(np.transpose(X), X)), np.transpose(X)), data_arr[nanmask])
    except:
        print('Calculation failed: NaNs')
        return np.nan, np.nan, np.nan, np.nan

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
        return np.nan, np.nan, np.nan, np.nan

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
        if X[i, 1] - X[i - 1, 1] == 1:
            Xmask2[k, 0:len(Xstar[i, :])] = Xstar[i, :]
            Ymask2[k] = Ystar[i]
            k = k + 1
            timok.append(i)
        else:
            # print('gap in X1, ',i,k)
            continue
    Xmask2ok = Xmask2[0:k, :]

    if len(beta) == 1 or len(Xmask2ok) < 10:
        trenda_z = np.nan
        siga_z = np.nan
    else:
        trenda_z = betaa[1] * 120 * 100 / np.nanmean(data_arr)
        siga_z = np.abs(betaa[1] / np.sqrt(covbetaa[1, 1]))

    if 'inflection_method' in ini:
        if ini['inflection_method'] == 'pwl':
            trenda_z = np.append(trenda_z, (betaa[2] + betaa[1]) * 120 * 100 / np.nanmean(data_arr))
            siga_z = np.append(siga_z, np.abs(betaa[2] / np.sqrt(covbetaa[2, 2])))
        elif ini['inflection_method'] == 'ind':
            trenda_z = np.append(trenda_z, betaa[3] * 120 * 100 / np.nanmean(data_arr))
            siga_z = np.append(siga_z, np.abs(betaa[3] / np.sqrt(covbetaa[3, 3])))

    return trenda_z, siga_z, beta, betaa


# Main program to run
def iup_reg_model(data, proxies, ini):
    data, proxies = get_proxy_time_overlap(ini, proxies, data)

    # Get index of the inflection point
    inflection_index = get_inflection_index(ini, data)

    # Creating the empty arrays for the trends and the uncertainty
    if 'inflection_method' not in ini:
        trenda_z = np.empty(data.o3[0, ...].shape) * np.nan
        siga_z = np.empty(data.o3[0, ...].shape) * np.nan
        X_string = ['1', 'time']
    elif ini['inflection_method'] == 'pwl':
        trenda_z = np.empty((data.o3[0, ...].shape + (2,))) * np.nan
        siga_z = np.empty((data.o3[0, ...].shape + (2,))) * np.nan
        X_string = ['1', 'time', 'piece-wise-linear-time']
    elif ini['inflection_method'] == 'ind':
        trenda_z = np.empty((data.o3[0, ...].shape + (2,))) * np.nan
        siga_z = np.empty((data.o3[0, ...].shape + (2,))) * np.nan
        X_string = ['1', 'independent time first part', '1', 'independent time second part']

    if 'trend_method' not in ini:
        ini['trend_method'] = 1
    if 'intercept_method' not in ini:
        ini['intercept_method'] = 1

    # Add strings for seasonal terms to the string list
    for k in range(int(ini['number_of_seasonal_terms'])):
        X_string.append('Seasonal term - sin of k=' + str(k+1))
        X_string.append('Seasonal term - cos of k=' + str(k + 1))

    # Get size of the X matrices by either not using proxies or using proxies with different methods
    X_proxy_size, X_2_string = calc_proxy_size(proxies)

    X_string = X_string + X_2_string

    X_all = np.empty((data.o3[data.date_start:data.date_end, ...].shape + (len(X_string),)), dtype='f4')
    X_all[:] = np.nan
    beta_all = np.empty((data.o3[0, ...].shape + (len(X_string),)), dtype='f4')
    beta_all[:] = np.nan
    betaa_all = np.empty((data.o3[0, ...].shape + (len(X_string),)), dtype='f4')
    betaa_all[:] = np.nan

    # Looping over every dimension but the first (time), to calculate the trends for every latitude, longitude and altitude
    it = np.nditer(data.o3[0, ...], flags=['multi_index'])

    while not it.finished:
        print(it.multi_index)
        data_arr = data.o3[(slice(None),) + it.multi_index]
        data_arr = data_arr[data.date_start:data.date_end]
        nanmask = ~data_arr.mask
        mask_time = np.where(nanmask == True)[0]

        # Inquery if there are enough datapoints to even calculate a trend
        # if len(mask_time) < 10 or mask_time[-1] < 125 or mask_time[0] >= 120:  # no trend is computed if the timeseries doesn't cover the entire series
        if len(mask_time) < 10:
            print('Not long enough')
            it.iternext()
            continue

        X_1 = get_X_1(inflection_index, nanmask, ini)
        X_2 = get_X_2(proxies, nanmask, X_proxy_size, ini, it, data)

        # X_2 = normalize(X_2) # Normalize at the start, not after forming the X matrices

        X = np.concatenate([X_1, X_2], axis=1)

        # Only use the X matrix without empty rows and columns
        X[:, np.all(X[nanmask] == 0, axis=0)] = np.nan  # This changes the rows with only 0 and NaNs to only NaN rows
        X_clean = X[~np.all(np.isnan(X), axis=1)][:, ~np.all(np.isnan(X), axis=0)]
        # Bandaid fix
        X_clean[np.isnan(X_clean)] = 0

        # Calculation of the trends and uncertainties for each cell
        trenda_z[it.multi_index], siga_z[it.multi_index], beta, betaa = calc_trend(X_clean, data_arr, ini)

        # Save X, beta and betaa
        X_all[(slice(None),) + it.multi_index + (slice(None),)] = X
        beta_all[it.multi_index + (slice(None),)][~np.all(np.isnan(X), axis=0)] = beta
        betaa_all[it.multi_index + (slice(None),)][~np.all(np.isnan(X), axis=0)] = betaa

        # Go to next iteration:
        it.iternext()
    diagnostic = [X_all, beta_all, betaa_all, X_string, data.time[data.date_start:data.date_end]]

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
    if ui == False:
        ini = load_config_ini('config.ini')
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


iup_ui(ui=True)
