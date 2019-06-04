"""
    Antenna Array Analysis

    Copyright (C) 2019  Zhengyu Peng
    E-mail: zpeng.me@gmail.com
    Website: https://zpeng.me

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

    `                      `
    -:.                  -#:
    -//:.              -###:
    -////:.          -#####:
    -/:.://:.      -###++##:
    ..   `://:-  -###+. :##:
           `:/+####+.   :##:
    .::::::::/+###.     :##:
    .////-----+##:    `:###:
     `-//:.   :##:  `:###/.
       `-//:. :##:`:###/.
         `-//:+######/.
           `-/+####/.
             `+##+.
              :##:
              :##:
              :##:
              :##:
              :##:
               .+:

"""

import sys
import res_rc
from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtCore import QThread

import numpy as np
import matplotlib.cm as cm

from calpattern import CalPattern

import pyqtgraph as pg
import pyqtgraph.opengl as gl

# pg.setConfigOption('background', 'w')
# pg.setConfigOption('foreground', 'k')
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)


class AntArrayAnalysis(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        super(QtWidgets.QMainWindow, self).__init__()
        self.ui = uic.loadUi('ui_array_analysis.ui', self)
        self.canvas2d = pg.GraphicsLayoutWidget()
        self.canvas3d = gl.GLViewWidget()
        self.window_list = ['Square', 'Chebyshev', 'Taylor', 'Hamming', 'Hann']

        self.layout_figure.addWidget(self.canvas3d)
        # self.layout_figure.addWidget(self.canvas2d)

        self.cmap = cm.get_cmap('jet')
        self.minZ = -100
        self.maxZ = 0

        self.array_config = dict()

        self.az_nfft = 512
        self.el_nfft = 512
        self.azimuth = np.arcsin(np.linspace(-1, 1, num=self.az_nfft,
                                             endpoint=False))/np.pi*180
        self.elevation = np.arcsin(np.linspace(-1, 1, num=self.el_nfft,
                                               endpoint=False))/np.pi*180
        self.angle = np.linspace(-90, 90, num=1801, endpoint=True)
        self.pattern = np.zeros(np.shape(self.azimuth))

        self.plotType = 'Cartesian'  # 'Cartesian' or 'Polar'
        self.polarAmpOffset = 60

        self.holdAngle = np.linspace(-90, 90, num=1801, endpoint=True)
        self.holdPattern = np.zeros(np.shape(self.azimuth))
        self.holdEnabled = False

        self.cartesianView = pg.PlotItem()
        self.cartesianPlot = pg.PlotDataItem()
        self.cartesianPlotHold = pg.PlotDataItem()

        self.polarView = pg.PlotItem()
        self.polarPlot = pg.PlotDataItem()
        self.polarPlotHold = pg.PlotDataItem()
        self.circleList = []
        self.circleLabel = []

        self.surface_plot = gl.GLSurfacePlotItem(computeNormals=False)
        self.surface_plot.translate(0, 0, 100)

        self.axis = gl.GLAxisItem()
        self.canvas3d.addItem(self.axis)
        self.axis.setSize(x=150, y=150, z=150)

        self.xzgrid = gl.GLGridItem()
        self.yzgrid = gl.GLGridItem()
        self.xygrid = gl.GLGridItem()
        self.canvas3d.addItem(self.xzgrid)
        self.canvas3d.addItem(self.yzgrid)
        self.canvas3d.addItem(self.xygrid)
        self.xzgrid.setSize(x=180, y=100, z=0)
        self.xzgrid.setSpacing(x=10, y=10, z=10)
        self.yzgrid.setSize(x=100, y=180, z=0)
        self.yzgrid.setSpacing(x=10, y=10, z=10)
        self.xygrid.setSize(x=180, y=180, z=0)
        self.xygrid.setSpacing(x=10, y=10, z=10)

        # rotate x and y grids to face the correct direction
        self.xzgrid.rotate(90, 1, 0, 0)
        self.xzgrid.translate(0, -90, 50)
        self.yzgrid.rotate(90, 0, 1, 0)
        self.yzgrid.translate(-90, 0, 50)
        # self.xygrid.translate(0, 0, -50)

        self.canvas3d.addItem(self.surface_plot)
        self.canvas3d.setCameraPosition(distance=300)
        # self.surface_plot.scale(0.1, 0.1, 0.1)

        self.penActive = pg.mkPen(color=(244, 143, 177), width=1)
        self.penHold = pg.mkPen(color=(158, 158, 158), width=1)

        self.init_plot_view()
        self.init_ui()

        self.calpattern = CalPattern()
        self.calpattern_thread = QThread()
        self.calpattern.patternReady.connect(self.update_pattern)
        self.calpattern_thread.started.connect(
            self.calpattern.cal_pattern)
        self.calpattern.moveToThread(self.calpattern_thread)
        self.calpattern_thread.start()

        self.new_params()
        self.ui.show()

    def init_ui(self):
        self.windowx_config(0)
        self.windowy_config(0)

        self.ui.clearButton.setEnabled(False)

        self.ui.cb_windowx.addItems(self.window_list)
        self.ui.cb_windowy.addItems(self.window_list)

        self.ui.cb_plottype.addItems(
            ['3D (Az-El-Amp)', '2D Cartesian', '2D Polar', 'Array layout'])

        self.ui.sb_sizex.valueChanged.connect(self.new_params)
        self.ui.sb_sizey.valueChanged.connect(self.new_params)
        self.ui.dsb_spacingx.valueChanged.connect(self.new_params)
        self.ui.dsb_spacingy.valueChanged.connect(self.new_params)
        self.ui.sb_sidelobex.valueChanged.connect(self.new_params)
        self.ui.sb_sidelobey.valueChanged.connect(self.new_params)
        self.ui.sb_adjsidelobex.valueChanged.connect(self.new_params)
        self.ui.sb_adjsidelobey.valueChanged.connect(self.new_params)
        self.ui.dsb_angleaz.valueChanged.connect(self.azimuth_value_changed)
        self.ui.hs_angletheta.valueChanged.connect(self.azimuth_slider_moved)

        self.ui.dsb_angleel.valueChanged.connect(
            self.elevation_value_changed)
        self.ui.hs_anglephi.valueChanged.connect(
            self.elevation_slider_moved)

        self.ui.cb_windowx.currentIndexChanged.connect(self.windowx_config)
        self.ui.cb_windowx.currentIndexChanged.connect(self.new_params)

        self.ui.cb_windowy.currentIndexChanged.connect(self.windowy_config)
        self.ui.cb_windowy.currentIndexChanged.connect(self.new_params)

        self.ui.spinBox_polarMinAmp.valueChanged.connect(
            self.polar_min_amp_value_changed)
        self.ui.horizontalSlider_polarMinAmp.valueChanged.connect(
            self.polar_min_amp_slider_moved)

        self.ui.label_polarMinAmp.setVisible(False)
        self.ui.spinBox_polarMinAmp.setVisible(False)
        self.ui.horizontalSlider_polarMinAmp.setVisible(False)

        self.ui.holdButton.clicked.connect(self.hold_figure)
        self.ui.clearButton.clicked.connect(self.clear_figure)

        self.ui.rb_cartesian.toggled.connect(
            self.cartesian_plot_toggled)
        self.ui.rb_polar.toggled.connect(self.polar_plot_toggled)

        self.ui.actionQuit.triggered.connect(QtWidgets.qApp.quit)

    def init_plot_view(self):
        ############################################
        # Cartesian View
        self.cartesianPlot.setPen(self.penActive)
        self.cartesianPlotHold.setPen(self.penHold)
        self.cartesianView.addItem(self.cartesianPlot)

        self.cartesianView.setXRange(-90, 90)
        self.cartesianView.setYRange(-80, 0)
        self.cartesianView.setLabel(axis='bottom', text='Angle', units='°')
        self.cartesianView.setLabel(
            axis='left', text='Normalized amplitude', units='dB')
        self.cartesianView.showGrid(x=True, y=True, alpha=0.5)
        self.cartesianView.setLimits(
            xMin=-90, xMax=90, yMin=-110, yMax=1, minXRange=0.1, minYRange=0.1)

        ############################################
        # Polar View
        self.polarPlot.setPen(self.penActive)
        self.polarPlotHold.setPen(self.penHold)
        self.polarView.addItem(self.polarPlot)

        self.polarView.setAspectLocked()
        self.polarView.hideAxis('left')
        self.polarView.hideAxis('bottom')

        self.circleLabel.append(pg.TextItem('0 dB'))
        self.polarView.addItem(self.circleLabel[0])
        self.circleLabel[0].setPos(self.polarAmpOffset, 0)
        for circle_idx in range(0, 6):
            self.circleList.append(
                QtGui.QGraphicsEllipseItem(
                    -self.polarAmpOffset + self.polarAmpOffset / 6 *
                    circle_idx,
                    -self.polarAmpOffset + self.polarAmpOffset / 6 *
                    circle_idx,
                    (self.polarAmpOffset - self.polarAmpOffset / 6 *
                     circle_idx) * 2,
                    (self.polarAmpOffset - self.polarAmpOffset / 6 *
                     circle_idx) * 2))
            self.circleList[circle_idx].setStartAngle(2880)
            self.circleList[circle_idx].setSpanAngle(2880)
            self.circleList[circle_idx].setPen(pg.mkPen(0.2))
            self.polarView.addItem(self.circleList[circle_idx])

            self.circleLabel.append(
                pg.TextItem(str(-self.polarAmpOffset / 6 * (circle_idx + 1))))
            self.circleLabel[circle_idx + 1].setPos(
                self.polarAmpOffset - self.polarAmpOffset / 6 * (
                    circle_idx + 1), 0)
            self.polarView.addItem(self.circleLabel[circle_idx + 1])

        self.polarView.addLine(x=0, pen=0.6)
        self.polarView.addLine(y=0, pen=0.6)
        self.polarView.addLine(y=0, pen=0.3).setAngle(45)
        self.polarView.addLine(y=0, pen=0.3).setAngle(-45)
        self.polarView.setMouseEnabled(x=False, y=False)

        # self.canvas3d.addItem(self.surface_plot)

        ############################################
        self.cartesianView.sigXRangeChanged.connect(
            self.plotview_x_range_changed)
        # self.show_cartesian_plot()
        # self.show_3d_plot()

    def azimuth_value_changed(self, value):
        self.ui.hs_angletheta.setValue(value * 10)
        self.new_params()

    def elevation_value_changed(self, value):
        self.ui.hs_anglephi.setValue(value * 10)
        self.new_params()

    def azimuth_slider_moved(self, value):
        self.ui.dsb_angleaz.setValue(value / 10)
        self.new_params()

    def elevation_slider_moved(self, value):
        self.ui.dsb_angleel.setValue(value / 10)
        self.new_params()

    def windowx_combobox_changed(self, value):
        self.windowx_change_config[value]()
        self.new_params()

    def windowy_combobox_changed(self, value):
        self.windowy_change_config[value]()
        self.new_params()

    def polar_min_amp_value_changed(self, value):
        self.ui.horizontalSlider_polarMinAmp.setValue(value)
        self.polarAmpOffset = -value
        self.new_params()

    def polar_min_amp_slider_moved(self, value):
        self.ui.spinBox_polarMinAmp.setValue(value)
        self.polarAmpOffset = -value
        self.new_params()

    def new_params(self):
        self.array_config['sizex'] = self.ui.sb_sizex.value()
        self.array_config['sizey'] = self.ui.sb_sizey.value()
        self.array_config['spacingx'] = self.ui.dsb_spacingx.value()
        self.array_config['spacingy'] = self.ui.dsb_spacingy.value()
        self.array_config['beam_az'] = self.ui.dsb_angleaz.value()
        self.array_config['beam_el'] = self.ui.dsb_angleel.value()
        self.array_config['windowx'] = self.ui.cb_windowx.currentIndex()
        self.array_config['windowy'] = self.ui.cb_windowy.currentIndex()
        self.array_config['sllx'] = self.ui.sb_sidelobex.value()
        self.array_config['slly'] = self.ui.sb_sidelobey.value()
        self.array_config['nbarx'] = self.ui.sb_adjsidelobex.value()
        self.array_config['nbary'] = self.ui.sb_adjsidelobey.value()

        self.calpattern.update_config(
            self.array_config, self.azimuth, self.elevation, self.plotType)

    def update_pattern(self, angle, angle_phi, pattern, plot_type):
        # print(np.shape(pattern))
        rgba_img = self.cmap((pattern-self.minZ)/(self.maxZ - self.minZ))
        self.surface_plot.setData(
            x=self.azimuth, y=self.elevation, z=pattern, colors=rgba_img)
        if plot_type is 'Cartesian':
            # self.cartesianPlot.setData(angle, pattern)
            self.angle = angle
            self.pattern = pattern

        elif plot_type is 'Polar':
            self.angle = angle
            self.pattern = pattern
            pattern = pattern + self.polarAmpOffset
            pattern[np.where(pattern < 0)] = 0
            x = pattern * np.sin(angle / 180 * np.pi)
            y = pattern * np.cos(angle / 180 * np.pi)

            self.circleLabel[0].setPos(self.polarAmpOffset, 0)
            for circle_idx in range(0, 6):
                self.circleList[circle_idx].setRect(
                    -self.polarAmpOffset + self.polarAmpOffset / 6 *
                    circle_idx,
                    -self.polarAmpOffset + self.polarAmpOffset / 6 *
                    circle_idx,
                    (self.polarAmpOffset - self.polarAmpOffset / 6 *
                     circle_idx) * 2,
                    (self.polarAmpOffset - self.polarAmpOffset / 6 *
                     circle_idx) * 2)
                self.circleLabel[circle_idx + 1].setText(
                    str(round(-self.polarAmpOffset / 6 * (circle_idx + 1), 1)))
                self.circleLabel[circle_idx + 1].setPos(
                    self.polarAmpOffset - self.polarAmpOffset / 6 * (
                        circle_idx + 1), 0)
            self.polarPlot.setData(x, y)

            pattern = self.holdPattern + self.polarAmpOffset
            pattern[np.where(pattern < 0)] = 0
            x = pattern * np.sin(self.holdAngle / 180 * np.pi)
            y = pattern * np.cos(self.holdAngle / 180 * np.pi)
            self.polarPlotHold.setData(x, y)

        elif plot_type is 'Cartesian_Hold':
            self.holdAngle = angle
            self.holdPattern = pattern
            self.cartesianPlotHold.setData(angle, pattern)
            self.cartesianView.addItem(self.cartesianPlotHold)

        elif plot_type is 'Polar_Hold':
            self.holdAngle = angle
            self.holdPattern = pattern
            pattern = pattern + self.polarAmpOffset
            pattern[np.where(pattern < 0)] = 0
            x = pattern * np.sin(angle / 180 * np.pi)
            y = pattern * np.cos(angle / 180 * np.pi)
            self.polarPlotHold.setData(x, y)
            self.polarView.addItem(self.polarPlotHold)

    def hold_figure(self):
        self.azimuth = np.linspace(-90, 90, num=1801, endpoint=True)
        self.new_params()
        self.ui.clearButton.setEnabled(True)
        self.holdEnabled = True

    def clear_figure(self):
        if self.plotType is 'Cartesian':
            self.cartesianView.removeItem(self.cartesianPlotHold)
        elif self.plotType is 'Polar':
            self.polarView.removeItem(self.polarPlotHold)

        self.ui.clearButton.setEnabled(False)
        self.holdEnabled = False

    def windowx_config(self, window_idx):
        if self.window_list[window_idx] is 'Chebyshev':
            self.ui.sb_sidelobex.setVisible(True)
            self.ui.label_sidelobex.setVisible(True)
            self.ui.hs_sidelobex.setVisible(True)
            self.ui.sb_adjsidelobex.setVisible(False)
            self.ui.label_adjsidelobex.setVisible(False)
            self.ui.hs_adjsidelobex.setVisible(False)
        elif self.window_list[window_idx] is 'Taylor':
            self.ui.sb_sidelobex.setVisible(True)
            self.ui.label_sidelobex.setVisible(True)
            self.ui.hs_sidelobex.setVisible(True)
            self.ui.sb_adjsidelobex.setVisible(True)
            self.ui.label_adjsidelobex.setVisible(True)
            self.ui.hs_adjsidelobex.setVisible(True)
        else:
            self.ui.sb_sidelobex.setVisible(False)
            self.ui.label_sidelobex.setVisible(False)
            self.ui.hs_sidelobex.setVisible(False)
            self.ui.sb_adjsidelobex.setVisible(False)
            self.ui.label_adjsidelobex.setVisible(False)
            self.ui.hs_adjsidelobex.setVisible(False)

    def windowy_config(self, window_idx):
        if self.window_list[window_idx] is 'Chebyshev':
            self.ui.sb_sidelobey.setVisible(True)
            self.ui.label_sidelobey.setVisible(True)
            self.ui.hs_sidelobey.setVisible(True)
            self.ui.sb_adjsidelobey.setVisible(False)
            self.ui.label_adjsidelobey.setVisible(False)
            self.ui.hs_adjsidelobey.setVisible(False)
        elif self.window_list[window_idx] is 'Taylor':
            self.ui.sb_sidelobey.setVisible(True)
            self.ui.label_sidelobey.setVisible(True)
            self.ui.hs_sidelobey.setVisible(True)
            self.ui.sb_adjsidelobey.setVisible(True)
            self.ui.label_adjsidelobey.setVisible(True)
            self.ui.hs_adjsidelobey.setVisible(True)
        else:
            self.ui.sb_sidelobey.setVisible(False)
            self.ui.label_sidelobey.setVisible(False)
            self.ui.hs_sidelobey.setVisible(False)
            self.ui.sb_adjsidelobey.setVisible(False)
            self.ui.label_adjsidelobey.setVisible(False)
            self.ui.hs_adjsidelobey.setVisible(False)

    def plotview_x_range_changed(self, item):
        self.azimuth = np.linspace(
            item.viewRange()[0][0],
            item.viewRange()[0][1],
            num=1801,
            endpoint=True)
        self.new_params()

    def cartesian_plot_toggled(self, checked):
        if checked and self.plotType is not 'Cartesian':
            if self.holdEnabled:
                self.polarView.removeItem(self.polarPlotHold)
                self.holdEnabled = False
                self.ui.clearButton.setEnabled(False)

            self.canvas2d.removeItem(self.polarView)
            self.canvas2d.addItem(self.cartesianView)
            self.ui.label_polarMinAmp.setVisible(False)
            self.ui.spinBox_polarMinAmp.setVisible(False)
            self.ui.horizontalSlider_polarMinAmp.setVisible(False)

            self.azimuth = np.linspace(-90, 90, num=1801, endpoint=True)
            self.plotType = 'Cartesian'
            self.new_params()
            self.cartesianView.setXRange(-90, 90)
            self.cartesianView.setYRange(-80, 0)

    def polar_plot_toggled(self, checked):
        if checked and self.plotType is not 'Polar':
            if self.holdEnabled:
                self.cartesianView.removeItem(self.cartesianPlotHold)
                self.holdEnabled = False
                self.ui.clearButton.setEnabled(False)

            self.canvas2d.removeItem(self.cartesianView)
            self.canvas2d.addItem(self.polarView)
            self.ui.label_polarMinAmp.setVisible(True)
            self.ui.spinBox_polarMinAmp.setVisible(True)
            self.ui.horizontalSlider_polarMinAmp.setVisible(True)

            self.azimuth = np.linspace(-90, 90, num=1801, endpoint=True)
            self.plotType = 'Polar'
            self.new_params()

    def show_cartesian_plot(self):
        self.canvas2d.addItem(self.cartesianView)

    def show_polar_plot(self):
        self.canvas2d.addItem(self.polarView)

    # def show_3d_plot(self):
        # self.canvas2d.addItem(self.canvas3d)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = AntArrayAnalysis()
    window.show()
    sys.exit(app.exec_())