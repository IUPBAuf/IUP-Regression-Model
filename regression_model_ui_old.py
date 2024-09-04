# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainPdKWIW.ui'
##
## Created by: Qt User Interface Compiler version 6.4.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMenu,
    QMenuBar, QSizePolicy, QStatusBar, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(585, 775)
        self.actionLoad_text_file = QAction(MainWindow)
        self.actionLoad_text_file.setObjectName(u"actionLoad_text_file")
        self.actionLoad_Proxy_file = QAction(MainWindow)
        self.actionLoad_Proxy_file.setObjectName(u"actionLoad_Proxy_file")
        self.actionNetCDF = QAction(MainWindow)
        self.actionNetCDF.setObjectName(u"actionNetCDF")
        self.actionASCII = QAction(MainWindow)
        self.actionASCII.setObjectName(u"actionASCII")
        self.actionASCII_2 = QAction(MainWindow)
        self.actionASCII_2.setObjectName(u"actionASCII_2")
        self.actionSave = QAction(MainWindow)
        self.actionSave.setObjectName(u"actionSave")
        self.actionContact = QAction(MainWindow)
        self.actionContact.setObjectName(u"actionContact")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout_2 = QHBoxLayout(self.centralwidget)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
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

        self.infl_date = QLineEdit(self.widget)
        self.infl_date.setObjectName(u"infl_date")
        self.infl_date.setEnabled(False)
        self.infl_date.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_3.addWidget(self.infl_date)


        self.verticalLayout_3.addWidget(self.widget)

        self.widget_2 = QWidget(self.frame_2)
        self.widget_2.setObjectName(u"widget_2")
        sizePolicy2.setHeightForWidth(self.widget_2.sizePolicy().hasHeightForWidth())
        self.widget_2.setSizePolicy(sizePolicy2)
        self.gridLayout = QGridLayout(self.widget_2)
        self.gridLayout.setObjectName(u"gridLayout")
        self.date_start = QLineEdit(self.widget_2)
        self.date_start.setObjectName(u"date_start")
        self.date_start.setAlignment(Qt.AlignCenter)

        self.gridLayout.addWidget(self.date_start, 0, 1, 1, 1)

        self.label_2 = QLabel(self.widget_2)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.date_end = QLineEdit(self.widget_2)
        self.date_end.setObjectName(u"date_end")
        self.date_end.setAlignment(Qt.AlignCenter)

        self.gridLayout.addWidget(self.date_end, 1, 1, 1, 1)

        self.label = QLabel(self.widget_2)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.check_start = QCheckBox(self.widget_2)
        self.check_start.setObjectName(u"check_start")
        self.check_start.setCheckable(False)

        self.gridLayout.addWidget(self.check_start, 0, 2, 1, 1)

        self.check_end = QCheckBox(self.widget_2)
        self.check_end.setObjectName(u"check_end")
        self.check_end.setCheckable(False)

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
        self.lim_alt_min.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.lim_alt_min, 1, 1, 1, 1)

        self.lim_alt_max = QLineEdit(self.widget_31)
        self.lim_alt_max.setObjectName(u"lim_alt_max")
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
        self.lim_lat_min.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.lim_lat_min, 2, 1, 1, 1)

        self.lim_lat_max = QLineEdit(self.widget_31)
        self.lim_lat_max.setObjectName(u"lim_lat_max")
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
        self.lim_lon_min.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.lim_lon_min, 3, 1, 1, 1)

        self.lim_lon_max = QLineEdit(self.widget_31)
        self.lim_lon_max.setObjectName(u"lim_lon_max")
        self.lim_lon_max.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.lim_lon_max, 3, 2, 1, 1)

        self.unit_lon = QLabel(self.widget_31)
        self.unit_lon.setObjectName(u"unit_lon")
        self.unit_lon.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.unit_lon, 3, 3, 1, 1)


        self.verticalLayout_3.addWidget(self.widget_31)


        self.verticalLayout_2.addWidget(self.frame_2)

        self.proxy_list = QTableWidget(self.widget_3)
        self.proxy_list.setObjectName(u"proxy_list")

        self.verticalLayout_2.addWidget(self.proxy_list)


        self.horizontalLayout_4.addWidget(self.widget_3)

        self.tabWidget.addTab(self.tab, "")
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        self.tabWidget.addTab(self.tab_3, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.tabWidget.addTab(self.tab_2, "")

        self.horizontalLayout_2.addWidget(self.tabWidget)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 585, 22))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuLoad_Data_File = QMenu(self.menuFile)
        self.menuLoad_Data_File.setObjectName(u"menuLoad_Data_File")
        self.menuLoad_Proxy_File = QMenu(self.menuFile)
        self.menuLoad_Proxy_File.setObjectName(u"menuLoad_Proxy_File")
        self.menuSettings = QMenu(self.menubar)
        self.menuSettings.setObjectName(u"menuSettings")
        self.menuHelp = QMenu(self.menubar)
        self.menuHelp.setObjectName(u"menuHelp")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.menuLoad_Data_File.menuAction())
        self.menuFile.addAction(self.menuLoad_Proxy_File.menuAction())
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionSave)
        self.menuLoad_Data_File.addAction(self.actionNetCDF)
        self.menuLoad_Data_File.addAction(self.actionASCII)
        self.menuLoad_Proxy_File.addAction(self.actionASCII_2)
        self.menuHelp.addAction(self.actionContact)

        self.retranslateUi(MainWindow)

        self.tabWidget.setCurrentIndex(2)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionLoad_text_file.setText(QCoreApplication.translate("MainWindow", u"Load Text file", None))
        self.actionLoad_Proxy_file.setText(QCoreApplication.translate("MainWindow", u"Load Proxy file", None))
        self.actionNetCDF.setText(QCoreApplication.translate("MainWindow", u"NetCDF", None))
        self.actionASCII.setText(QCoreApplication.translate("MainWindow", u"ASCII", None))
        self.actionASCII_2.setText(QCoreApplication.translate("MainWindow", u"ASCII", None))
        self.actionSave.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.actionContact.setText(QCoreApplication.translate("MainWindow", u"Contact", None))
        self.infl_check.setText(QCoreApplication.translate("MainWindow", u"Inflection Point", None))
        self.infl_date.setText(QCoreApplication.translate("MainWindow", u"Inflection Date", None))
#if QT_CONFIG(tooltip)
        self.date_start.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Date from which the trend will be computed.</p><p>Date must be inbetween the timeline of the data.</p><p>Dates not in the correct format (see &quot;Settings&quot;) or any other input will be used as if there is no input.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.date_start.setText(QCoreApplication.translate("MainWindow", u"Start Date", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"End Date", None))
#if QT_CONFIG(tooltip)
        self.date_end.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Date to which the trend will be computed.</p><p>Date must be inbetween the timeline of the data.</p><p>Dates not in the correct format (see &quot;Settings&quot;) or any other input will be used as if there is no input.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.date_end.setText(QCoreApplication.translate("MainWindow", u"End Date", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Start Date", None))
        self.check_start.setText("")
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
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("MainWindow", u"Options", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), QCoreApplication.translate("MainWindow", u"Data", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("MainWindow", u"Plotting", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuLoad_Data_File.setTitle(QCoreApplication.translate("MainWindow", u"Load Data File", None))
        self.menuLoad_Proxy_File.setTitle(QCoreApplication.translate("MainWindow", u"Load Proxy File", None))
        self.menuSettings.setTitle(QCoreApplication.translate("MainWindow", u"Settings", None))
        self.menuHelp.setTitle(QCoreApplication.translate("MainWindow", u"Help", None))
    # retranslateUi

