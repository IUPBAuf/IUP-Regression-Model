# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainSLHZqN.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(636, 818)
        self.actionLoad_text_file = QAction(MainWindow)
        self.actionLoad_text_file.setObjectName(u"actionLoad_text_file")
        self.actionLoad_Proxy_file = QAction(MainWindow)
        self.actionLoad_Proxy_file.setObjectName(u"actionLoad_Proxy_file")
        self.menu_load_data_netcdf = QAction(MainWindow)
        self.menu_load_data_netcdf.setObjectName(u"menu_load_data_netcdf")
        self.menu_load_data_ascii = QAction(MainWindow)
        self.menu_load_data_ascii.setObjectName(u"menu_load_data_ascii")
        self.menu_load_proxy_netcdf = QAction(MainWindow)
        self.menu_load_proxy_netcdf.setObjectName(u"menu_load_proxy_netcdf")
        self.menu_save = QAction(MainWindow)
        self.menu_save.setObjectName(u"menu_save")
        self.menu_help = QAction(MainWindow)
        self.menu_help.setObjectName(u"menu_help")
        self.menu_load_proxy_ascii = QAction(MainWindow)
        self.menu_load_proxy_ascii.setObjectName(u"menu_load_proxy_ascii")
        self.menu_load_data = QAction(MainWindow)
        self.menu_load_data.setObjectName(u"menu_load_data")
        self.menu_load_proxy = QAction(MainWindow)
        self.menu_load_proxy.setObjectName(u"menu_load_proxy")
        self.menu_load_settings = QAction(MainWindow)
        self.menu_load_settings.setObjectName(u"menu_load_settings")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_5 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.horizontalLayout_4 = QHBoxLayout(self.tab)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.widget_4 = QWidget(self.tab)
        self.widget_4.setObjectName(u"widget_4")
        sizePolicy = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_4.sizePolicy().hasHeightForWidth())
        self.widget_4.setSizePolicy(sizePolicy)
        self.verticalLayout = QVBoxLayout(self.widget_4)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.data_list = QListWidget(self.widget_4)
        self.data_list.setObjectName(u"data_list")

        self.verticalLayout.addWidget(self.data_list)


        self.horizontalLayout_4.addWidget(self.widget_4)

        self.widget_3 = QWidget(self.tab)
        self.widget_3.setObjectName(u"widget_3")
        self.verticalLayout_2 = QVBoxLayout(self.widget_3)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.frame_2 = QFrame(self.widget_3)
        self.frame_2.setObjectName(u"frame_2")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.frame_2.sizePolicy().hasHeightForWidth())
        self.frame_2.setSizePolicy(sizePolicy1)
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.widget = QWidget(self.frame_2)
        self.widget.setObjectName(u"widget")
        sizePolicy2 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy2)
        self.horizontalLayout_3 = QHBoxLayout(self.widget)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.infl_check = QCheckBox(self.widget)
        self.infl_check.setObjectName(u"infl_check")
        sizePolicy3 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.infl_check.sizePolicy().hasHeightForWidth())
        self.infl_check.setSizePolicy(sizePolicy3)

        self.horizontalLayout_3.addWidget(self.infl_check)

        self.inflection_point = QLineEdit(self.widget)
        self.inflection_point.setObjectName(u"inflection_point")
        self.inflection_point.setEnabled(False)
        self.inflection_point.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_3.addWidget(self.inflection_point)

        self.check_inflection = QCheckBox(self.widget)
        self.check_inflection.setObjectName(u"check_inflection")
        self.check_inflection.setEnabled(False)

        self.horizontalLayout_3.addWidget(self.check_inflection)


        self.verticalLayout_3.addWidget(self.widget)

        self.widget_5 = QWidget(self.frame_2)
        self.widget_5.setObjectName(u"widget_5")
        self.verticalLayout_4 = QVBoxLayout(self.widget_5)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.inflection_method = QComboBox(self.widget_5)
        self.inflection_method.addItem("")
        self.inflection_method.addItem("")
        self.inflection_method.setObjectName(u"inflection_method")
        self.inflection_method.setEnabled(False)

        self.verticalLayout_4.addWidget(self.inflection_method)


        self.verticalLayout_3.addWidget(self.widget_5)

        self.widget_2 = QWidget(self.frame_2)
        self.widget_2.setObjectName(u"widget_2")
        sizePolicy2.setHeightForWidth(self.widget_2.sizePolicy().hasHeightForWidth())
        self.widget_2.setSizePolicy(sizePolicy2)
        self.gridLayout = QGridLayout(self.widget_2)
        self.gridLayout.setObjectName(u"gridLayout")
        self.start_date = QLineEdit(self.widget_2)
        self.start_date.setObjectName(u"start_date")
        self.start_date.setAlignment(Qt.AlignCenter)

        self.gridLayout.addWidget(self.start_date, 0, 1, 1, 1)

        self.label_2 = QLabel(self.widget_2)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.end_date = QLineEdit(self.widget_2)
        self.end_date.setObjectName(u"end_date")
        self.end_date.setAlignment(Qt.AlignCenter)

        self.gridLayout.addWidget(self.end_date, 1, 1, 1, 1)

        self.label = QLabel(self.widget_2)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.check_start = QCheckBox(self.widget_2)
        self.check_start.setObjectName(u"check_start")
        self.check_start.setEnabled(False)

        self.gridLayout.addWidget(self.check_start, 0, 2, 1, 1)

        self.check_end = QCheckBox(self.widget_2)
        self.check_end.setObjectName(u"check_end")
        self.check_end.setEnabled(False)

        self.gridLayout.addWidget(self.check_end, 1, 2, 1, 1)


        self.verticalLayout_3.addWidget(self.widget_2)

        self.widget_31 = QWidget(self.frame_2)
        self.widget_31.setObjectName(u"widget_31")
        sizePolicy2.setHeightForWidth(self.widget_31.sizePolicy().hasHeightForWidth())
        self.widget_31.setSizePolicy(sizePolicy2)
        self.gridLayout_2 = QGridLayout(self.widget_31)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_3 = QLabel(self.widget_31)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_3, 0, 0, 1, 1)

        self.label_4 = QLabel(self.widget_31)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_4, 0, 1, 1, 1)

        self.label_5 = QLabel(self.widget_31)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_5, 0, 2, 1, 1)

        self.label_6 = QLabel(self.widget_31)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_6, 0, 3, 1, 1)

        self.label_7 = QLabel(self.widget_31)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_7, 1, 0, 1, 1)

        self.lim_alt_min = QLineEdit(self.widget_31)
        self.lim_alt_min.setObjectName(u"lim_alt_min")
        self.lim_alt_min.setEnabled(False)
        self.lim_alt_min.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.lim_alt_min, 1, 1, 1, 1)

        self.lim_alt_max = QLineEdit(self.widget_31)
        self.lim_alt_max.setObjectName(u"lim_alt_max")
        self.lim_alt_max.setEnabled(False)
        self.lim_alt_max.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.lim_alt_max, 1, 2, 1, 1)

        self.unit_alt = QLabel(self.widget_31)
        self.unit_alt.setObjectName(u"unit_alt")
        self.unit_alt.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.unit_alt, 1, 3, 1, 1)

        self.label_8 = QLabel(self.widget_31)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_8, 2, 0, 1, 1)

        self.lim_lat_min = QLineEdit(self.widget_31)
        self.lim_lat_min.setObjectName(u"lim_lat_min")
        self.lim_lat_min.setEnabled(False)
        self.lim_lat_min.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.lim_lat_min, 2, 1, 1, 1)

        self.lim_lat_max = QLineEdit(self.widget_31)
        self.lim_lat_max.setObjectName(u"lim_lat_max")
        self.lim_lat_max.setEnabled(False)
        self.lim_lat_max.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.lim_lat_max, 2, 2, 1, 1)

        self.unit_lat = QLabel(self.widget_31)
        self.unit_lat.setObjectName(u"unit_lat")
        self.unit_lat.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.unit_lat, 2, 3, 1, 1)

        self.label_9 = QLabel(self.widget_31)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_9, 3, 0, 1, 1)

        self.lim_lon_min = QLineEdit(self.widget_31)
        self.lim_lon_min.setObjectName(u"lim_lon_min")
        self.lim_lon_min.setEnabled(False)
        self.lim_lon_min.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.lim_lon_min, 3, 1, 1, 1)

        self.lim_lon_max = QLineEdit(self.widget_31)
        self.lim_lon_max.setObjectName(u"lim_lon_max")
        self.lim_lon_max.setEnabled(False)
        self.lim_lon_max.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.lim_lon_max, 3, 2, 1, 1)

        self.unit_lon = QLabel(self.widget_31)
        self.unit_lon.setObjectName(u"unit_lon")
        self.unit_lon.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.unit_lon, 3, 3, 1, 1)


        self.verticalLayout_3.addWidget(self.widget_31)


        self.verticalLayout_2.addWidget(self.frame_2)

        self.proxy_list = QTableWidget(self.widget_3)
        if (self.proxy_list.columnCount() < 2):
            self.proxy_list.setColumnCount(2)
        self.proxy_list.setObjectName(u"proxy_list")
        self.proxy_list.setColumnCount(2)
        self.proxy_list.verticalHeader().setVisible(False)

        self.verticalLayout_2.addWidget(self.proxy_list)

        self.frame = QFrame(self.widget_3)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout_7 = QVBoxLayout(self.frame)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.label_10 = QLabel(self.frame)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setAlignment(Qt.AlignCenter)

        self.verticalLayout_7.addWidget(self.label_10)

        self.all_proxy_method = QComboBox(self.frame)
        self.all_proxy_method.addItem("")
        self.all_proxy_method.addItem("")
        self.all_proxy_method.addItem("")
        self.all_proxy_method.addItem("")
        self.all_proxy_method.addItem("")
        self.all_proxy_method.setObjectName(u"all_proxy_method")

        self.verticalLayout_7.addWidget(self.all_proxy_method)


        self.verticalLayout_2.addWidget(self.frame)


        self.horizontalLayout_4.addWidget(self.widget_3)

        self.tabWidget.addTab(self.tab, "")
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        self.verticalLayout_8 = QVBoxLayout(self.tab_3)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.tabWidget_2 = QTabWidget(self.tab_3)
        self.tabWidget_2.setObjectName(u"tabWidget_2")
        self.widget_7 = QWidget()
        self.widget_7.setObjectName(u"widget_7")
        self.verticalLayout_9 = QVBoxLayout(self.widget_7)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.widget_8 = QWidget(self.widget_7)
        self.widget_8.setObjectName(u"widget_8")
        self.horizontalLayout_2 = QHBoxLayout(self.widget_8)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.widget_11 = QWidget(self.widget_8)
        self.widget_11.setObjectName(u"widget_11")
        self.verticalLayout_10 = QVBoxLayout(self.widget_11)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.dia_data_combo = QComboBox(self.widget_11)
        self.dia_data_combo.setObjectName(u"dia_data_combo")

        self.verticalLayout_10.addWidget(self.dia_data_combo)


        self.horizontalLayout_2.addWidget(self.widget_11)

        self.widget_10 = QWidget(self.widget_8)
        self.widget_10.setObjectName(u"widget_10")
        self.gridLayout_3 = QGridLayout(self.widget_10)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.label_11 = QLabel(self.widget_10)
        self.label_11.setObjectName(u"label_11")

        self.gridLayout_3.addWidget(self.label_11, 0, 0, 1, 1)

        self.dia_data_start = QLabel(self.widget_10)
        self.dia_data_start.setObjectName(u"dia_data_start")
        self.dia_data_start.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.dia_data_start, 0, 1, 1, 1)

        self.label_12 = QLabel(self.widget_10)
        self.label_12.setObjectName(u"label_12")

        self.gridLayout_3.addWidget(self.label_12, 1, 0, 1, 1)

        self.dia_data_end = QLabel(self.widget_10)
        self.dia_data_end.setObjectName(u"dia_data_end")
        self.dia_data_end.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.dia_data_end, 1, 1, 1, 1)

        self.label_15 = QLabel(self.widget_10)
        self.label_15.setObjectName(u"label_15")

        self.gridLayout_3.addWidget(self.label_15, 2, 0, 1, 1)

        self.dia_data_time = QLabel(self.widget_10)
        self.dia_data_time.setObjectName(u"dia_data_time")
        self.dia_data_time.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.dia_data_time, 2, 1, 1, 1)

        self.label_17 = QLabel(self.widget_10)
        self.label_17.setObjectName(u"label_17")

        self.gridLayout_3.addWidget(self.label_17, 3, 0, 1, 1)

        self.dia_data_lat = QLabel(self.widget_10)
        self.dia_data_lat.setObjectName(u"dia_data_lat")
        self.dia_data_lat.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.dia_data_lat, 3, 1, 1, 1)

        self.label_18 = QLabel(self.widget_10)
        self.label_18.setObjectName(u"label_18")

        self.gridLayout_3.addWidget(self.label_18, 4, 0, 1, 1)

        self.dia_data_lon = QLabel(self.widget_10)
        self.dia_data_lon.setObjectName(u"dia_data_lon")
        self.dia_data_lon.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.dia_data_lon, 4, 1, 1, 1)

        self.label_19 = QLabel(self.widget_10)
        self.label_19.setObjectName(u"label_19")

        self.gridLayout_3.addWidget(self.label_19, 6, 0, 1, 1)

        self.dia_data_alt = QLabel(self.widget_10)
        self.dia_data_alt.setObjectName(u"dia_data_alt")
        self.dia_data_alt.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.dia_data_alt, 6, 1, 1, 1)


        self.horizontalLayout_2.addWidget(self.widget_10)


        self.verticalLayout_9.addWidget(self.widget_8)

        self.widget_9 = QWidget(self.widget_7)
        self.widget_9.setObjectName(u"widget_9")
        self.verticalLayout_11 = QVBoxLayout(self.widget_9)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.dia_data_table = QTableWidget(self.widget_9)
        self.dia_data_table.setObjectName(u"dia_data_table")

        self.verticalLayout_11.addWidget(self.dia_data_table)

        self.widget_21 = QWidget(self.widget_9)
        self.widget_21.setObjectName(u"widget_21")
        self.horizontalLayout_8 = QHBoxLayout(self.widget_21)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.label_24 = QLabel(self.widget_21)
        self.label_24.setObjectName(u"label_24")

        self.horizontalLayout_8.addWidget(self.label_24)

        self.dia_data_combo_time = QComboBox(self.widget_21)
        self.dia_data_combo_time.setObjectName(u"dia_data_combo_time")

        self.horizontalLayout_8.addWidget(self.dia_data_combo_time)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_4)

        self.label_20 = QLabel(self.widget_21)
        self.label_20.setObjectName(u"label_20")

        self.horizontalLayout_8.addWidget(self.label_20)

        self.dia_data_combo_lat = QComboBox(self.widget_21)
        self.dia_data_combo_lat.setObjectName(u"dia_data_combo_lat")

        self.horizontalLayout_8.addWidget(self.dia_data_combo_lat)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_2)

        self.label_22 = QLabel(self.widget_21)
        self.label_22.setObjectName(u"label_22")

        self.horizontalLayout_8.addWidget(self.label_22)

        self.dia_data_combo_lon = QComboBox(self.widget_21)
        self.dia_data_combo_lon.setObjectName(u"dia_data_combo_lon")

        self.horizontalLayout_8.addWidget(self.dia_data_combo_lon)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_3)

        self.label_23 = QLabel(self.widget_21)
        self.label_23.setObjectName(u"label_23")

        self.horizontalLayout_8.addWidget(self.label_23)

        self.dia_data_combo_alt = QComboBox(self.widget_21)
        self.dia_data_combo_alt.setObjectName(u"dia_data_combo_alt")

        self.horizontalLayout_8.addWidget(self.dia_data_combo_alt)


        self.verticalLayout_11.addWidget(self.widget_21)


        self.verticalLayout_9.addWidget(self.widget_9)

        self.tabWidget_2.addTab(self.widget_7, "")
        self.tab_5 = QWidget()
        self.tab_5.setObjectName(u"tab_5")
        self.verticalLayout_14 = QVBoxLayout(self.tab_5)
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.widget_12 = QWidget(self.tab_5)
        self.widget_12.setObjectName(u"widget_12")
        self.horizontalLayout_5 = QHBoxLayout(self.widget_12)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.widget_13 = QWidget(self.widget_12)
        self.widget_13.setObjectName(u"widget_13")
        self.verticalLayout_12 = QVBoxLayout(self.widget_13)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.dia_proxy_combo = QComboBox(self.widget_13)
        self.dia_proxy_combo.setObjectName(u"dia_proxy_combo")

        self.verticalLayout_12.addWidget(self.dia_proxy_combo)


        self.horizontalLayout_5.addWidget(self.widget_13)

        self.widget_14 = QWidget(self.widget_12)
        self.widget_14.setObjectName(u"widget_14")
        self.gridLayout_4 = QGridLayout(self.widget_14)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.dia_proxy_end = QLabel(self.widget_14)
        self.dia_proxy_end.setObjectName(u"dia_proxy_end")
        self.dia_proxy_end.setAlignment(Qt.AlignCenter)

        self.gridLayout_4.addWidget(self.dia_proxy_end, 1, 1, 1, 1)

        self.dia_proxy_start = QLabel(self.widget_14)
        self.dia_proxy_start.setObjectName(u"dia_proxy_start")
        self.dia_proxy_start.setAlignment(Qt.AlignCenter)

        self.gridLayout_4.addWidget(self.dia_proxy_start, 0, 1, 1, 1)

        self.label_16 = QLabel(self.widget_14)
        self.label_16.setObjectName(u"label_16")

        self.gridLayout_4.addWidget(self.label_16, 2, 0, 1, 1)

        self.label_13 = QLabel(self.widget_14)
        self.label_13.setObjectName(u"label_13")

        self.gridLayout_4.addWidget(self.label_13, 0, 0, 1, 1)

        self.label_14 = QLabel(self.widget_14)
        self.label_14.setObjectName(u"label_14")

        self.gridLayout_4.addWidget(self.label_14, 1, 0, 1, 1)

        self.dia_proxy = QLabel(self.widget_14)
        self.dia_proxy.setObjectName(u"dia_proxy")
        self.dia_proxy.setAlignment(Qt.AlignCenter)

        self.gridLayout_4.addWidget(self.dia_proxy, 2, 1, 1, 1)


        self.horizontalLayout_5.addWidget(self.widget_14)


        self.verticalLayout_14.addWidget(self.widget_12)

        self.widget_15 = QWidget(self.tab_5)
        self.widget_15.setObjectName(u"widget_15")
        self.verticalLayout_13 = QVBoxLayout(self.widget_15)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.dia_proxy_table = QTableWidget(self.widget_15)
        self.dia_proxy_table.setObjectName(u"dia_proxy_table")

        self.verticalLayout_13.addWidget(self.dia_proxy_table)


        self.verticalLayout_14.addWidget(self.widget_15)

        self.tabWidget_2.addTab(self.tab_5, "")
        self.tab_4 = QWidget()
        self.tab_4.setObjectName(u"tab_4")
        self.verticalLayout_17 = QVBoxLayout(self.tab_4)
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.widget_17 = QWidget(self.tab_4)
        self.widget_17.setObjectName(u"widget_17")
        self.horizontalLayout_7 = QHBoxLayout(self.widget_17)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.widget_18 = QWidget(self.widget_17)
        self.widget_18.setObjectName(u"widget_18")
        self.verticalLayout_15 = QVBoxLayout(self.widget_18)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.dia_X_combo = QComboBox(self.widget_18)
        self.dia_X_combo.setObjectName(u"dia_X_combo")

        self.verticalLayout_15.addWidget(self.dia_X_combo)


        self.horizontalLayout_7.addWidget(self.widget_18)

        self.widget_19 = QWidget(self.widget_17)
        self.widget_19.setObjectName(u"widget_19")
        self.gridLayout_5 = QGridLayout(self.widget_19)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.dia_X_dim = QLabel(self.widget_19)
        self.dia_X_dim.setObjectName(u"dia_X_dim")
        self.dia_X_dim.setAlignment(Qt.AlignCenter)

        self.gridLayout_5.addWidget(self.dia_X_dim, 0, 1, 1, 1)

        self.label_21 = QLabel(self.widget_19)
        self.label_21.setObjectName(u"label_21")

        self.gridLayout_5.addWidget(self.label_21, 0, 0, 1, 1)


        self.horizontalLayout_7.addWidget(self.widget_19)


        self.verticalLayout_17.addWidget(self.widget_17)

        self.widget_20 = QWidget(self.tab_4)
        self.widget_20.setObjectName(u"widget_20")
        self.verticalLayout_16 = QVBoxLayout(self.widget_20)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.dia_X_table = QTableWidget(self.widget_20)
        self.dia_X_table.setObjectName(u"dia_X_table")

        self.verticalLayout_16.addWidget(self.dia_X_table)


        self.verticalLayout_17.addWidget(self.widget_20)

        self.tabWidget_2.addTab(self.tab_4, "")

        self.verticalLayout_8.addWidget(self.tabWidget_2)

        self.tabWidget.addTab(self.tab_3, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.verticalLayout_6 = QVBoxLayout(self.tab_2)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.figure_widget = QWidget(self.tab_2)
        self.figure_widget.setObjectName(u"figure_widget")

        self.verticalLayout_6.addWidget(self.figure_widget)

        self.widget_16 = QWidget(self.tab_2)
        self.widget_16.setObjectName(u"widget_16")
        sizePolicy4 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.widget_16.sizePolicy().hasHeightForWidth())
        self.widget_16.setSizePolicy(sizePolicy4)
        self.horizontalLayout_6 = QHBoxLayout(self.widget_16)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.plot_button = QPushButton(self.widget_16)
        self.plot_button.setObjectName(u"plot_button")
        self.plot_button.setEnabled(False)
        self.plot_button.setMaximumSize(QSize(100, 16777215))

        self.horizontalLayout_6.addWidget(self.plot_button)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer)

        self.dim_label = QLabel(self.widget_16)
        self.dim_label.setObjectName(u"dim_label")

        self.horizontalLayout_6.addWidget(self.dim_label)

        self.dim_combo = QComboBox(self.widget_16)
        self.dim_combo.setObjectName(u"dim_combo")

        self.horizontalLayout_6.addWidget(self.dim_combo)

        self.axis_label = QLabel(self.widget_16)
        self.axis_label.setObjectName(u"axis_label")

        self.horizontalLayout_6.addWidget(self.axis_label)

        self.axis_combo = QComboBox(self.widget_16)
        self.axis_combo.setObjectName(u"axis_combo")

        self.horizontalLayout_6.addWidget(self.axis_combo)


        self.verticalLayout_6.addWidget(self.widget_16)

        self.tabWidget.addTab(self.tab_2, "")

        self.verticalLayout_5.addWidget(self.tabWidget)

        self.widget_6 = QWidget(self.centralwidget)
        self.widget_6.setObjectName(u"widget_6")
        self.horizontalLayout = QHBoxLayout(self.widget_6)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.compute_button = QPushButton(self.widget_6)
        self.compute_button.setObjectName(u"compute_button")
        self.compute_button.setMaximumSize(QSize(100, 16777215))

        self.horizontalLayout.addWidget(self.compute_button)


        self.verticalLayout_5.addWidget(self.widget_6)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 636, 22))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        self.menu_settings = QMenu(self.menubar)
        self.menu_settings.setObjectName(u"menu_settings")
        self.menuHelp = QMenu(self.menubar)
        self.menuHelp.setObjectName(u"menuHelp")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menu_settings.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.menu_load_data)
        self.menuFile.addAction(self.menu_load_proxy)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.menu_save)
        self.menu_settings.addAction(self.menu_load_settings)
        self.menuHelp.addAction(self.menu_help)

        self.retranslateUi(MainWindow)

        self.tabWidget.setCurrentIndex(0)
        self.tabWidget_2.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionLoad_text_file.setText(QCoreApplication.translate("MainWindow", u"Load Text file", None))
        self.actionLoad_Proxy_file.setText(QCoreApplication.translate("MainWindow", u"Load Proxy file", None))
        self.menu_load_data_netcdf.setText(QCoreApplication.translate("MainWindow", u"NetCDF", None))
        self.menu_load_data_ascii.setText(QCoreApplication.translate("MainWindow", u"ASCII", None))
        self.menu_load_proxy_netcdf.setText(QCoreApplication.translate("MainWindow", u"NetCDF", None))
        self.menu_save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.menu_help.setText(QCoreApplication.translate("MainWindow", u"Contact", None))
        self.menu_load_proxy_ascii.setText(QCoreApplication.translate("MainWindow", u"ASCII", None))
        self.menu_load_data.setText(QCoreApplication.translate("MainWindow", u"Load Data File", None))
        self.menu_load_proxy.setText(QCoreApplication.translate("MainWindow", u"Load Proxy File", None))
        self.menu_load_settings.setText(QCoreApplication.translate("MainWindow", u"Load Settings", None))
#if QT_CONFIG(tooltip)
        self.data_list.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>All correctly loaded data will be displayed here.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.infl_check.setText(QCoreApplication.translate("MainWindow", u"Inflection Point", None))
        self.inflection_point.setText(QCoreApplication.translate("MainWindow", u"Inflection Date", None))
#if QT_CONFIG(tooltip)
        self.check_inflection.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Check: The format was recognized and can be used for the trend analysis</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.check_inflection.setText("")
        self.inflection_method.setItemText(0, QCoreApplication.translate("MainWindow", u"Independent Trend", None))
        self.inflection_method.setItemText(1, QCoreApplication.translate("MainWindow", u"Piece-wise Linear Trend", None))

#if QT_CONFIG(tooltip)
        self.start_date.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Date from which the trend will be computed.</p><p>Date must be inbetween the timeline of the data.</p><p>Dates not in the correct format (see &quot;Settings&quot;) or any other input will be used as if there is no input.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.start_date.setText(QCoreApplication.translate("MainWindow", u"Start Date", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"End Date", None))
#if QT_CONFIG(tooltip)
        self.end_date.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Date to which the trend will be computed.</p><p>Date must be inbetween the timeline of the data.</p><p>Dates not in the correct format (see &quot;Settings&quot;) or any other input will be used as if there is no input.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.end_date.setText(QCoreApplication.translate("MainWindow", u"End Date", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Start Date", None))
#if QT_CONFIG(tooltip)
        self.check_start.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Check: The format was recognized and can be used for the trend analysis</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.check_start.setText("")
#if QT_CONFIG(tooltip)
        self.check_end.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Check: The format was recognized and can be used for the trend analysis</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.check_end.setText("")
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Limits", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Min", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Max", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Units", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"Alt", None))
        self.unit_alt.setText(QCoreApplication.translate("MainWindow", u"unit_alt", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"Lat", None))
        self.unit_lat.setText(QCoreApplication.translate("MainWindow", u"unit_lat", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"Lon", None))
        self.unit_lon.setText(QCoreApplication.translate("MainWindow", u"unit_lon", None))
#if QT_CONFIG(tooltip)
        self.proxy_list.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Successfully loaded proxies and the methods how they will be used in the trend analysis.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"Method for all proxies", None))
        self.all_proxy_method.setItemText(0, QCoreApplication.translate("MainWindow", u"mixed", None))
        self.all_proxy_method.setItemText(1, QCoreApplication.translate("MainWindow", u"disable", None))
        self.all_proxy_method.setItemText(2, QCoreApplication.translate("MainWindow", u"single", None))
        self.all_proxy_method.setItemText(3, QCoreApplication.translate("MainWindow", u"harmonics", None))
        self.all_proxy_method.setItemText(4, QCoreApplication.translate("MainWindow", u"12 months", None))

#if QT_CONFIG(tooltip)
        self.all_proxy_method.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>This changes the method for all loaded proxies at the same time.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("MainWindow", u"Options", None))
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"start date:", None))
        self.dia_data_start.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_12.setText(QCoreApplication.translate("MainWindow", u"end date:", None))
        self.dia_data_end.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_15.setText(QCoreApplication.translate("MainWindow", u"time dimension:", None))
        self.dia_data_time.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_17.setText(QCoreApplication.translate("MainWindow", u"latitude dimension:", None))
        self.dia_data_lat.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_18.setText(QCoreApplication.translate("MainWindow", u"longitude dimension:", None))
        self.dia_data_lon.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_19.setText(QCoreApplication.translate("MainWindow", u"altitude dimension:", None))
        self.dia_data_alt.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_24.setText(QCoreApplication.translate("MainWindow", u"Time:", None))
        self.label_20.setText(QCoreApplication.translate("MainWindow", u"Latitude:", None))
        self.label_22.setText(QCoreApplication.translate("MainWindow", u"Longitude:", None))
        self.label_23.setText(QCoreApplication.translate("MainWindow", u"Altitude:", None))
        self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.widget_7), QCoreApplication.translate("MainWindow", u"Data", None))
        self.dia_proxy_end.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.dia_proxy_start.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_16.setText(QCoreApplication.translate("MainWindow", u"proxy dimension:", None))
        self.label_13.setText(QCoreApplication.translate("MainWindow", u"start date:", None))
        self.label_14.setText(QCoreApplication.translate("MainWindow", u"end date:", None))
        self.dia_proxy.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.tab_5), QCoreApplication.translate("MainWindow", u"Proxies", None))
        self.dia_X_dim.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_21.setText(QCoreApplication.translate("MainWindow", u"dimension:", None))
        self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.tab_4), QCoreApplication.translate("MainWindow", u"X", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), QCoreApplication.translate("MainWindow", u"Diagnostic", None))
        self.plot_button.setText(QCoreApplication.translate("MainWindow", u"Plot", None))
        self.dim_label.setText(QCoreApplication.translate("MainWindow", u"Plot", None))
        self.axis_label.setText(QCoreApplication.translate("MainWindow", u"Axis:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("MainWindow", u"Plotting", None))
        self.compute_button.setText(QCoreApplication.translate("MainWindow", u"Compute", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menu_settings.setTitle(QCoreApplication.translate("MainWindow", u"Settings", None))
        self.menuHelp.setTitle(QCoreApplication.translate("MainWindow", u"Help", None))
    # retranslateUi

