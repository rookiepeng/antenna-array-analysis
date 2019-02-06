# -*- coding: utf-8 -*-
"""
    Antenna Array Analysis
    Copyright (C) 2019  Zhengyu Peng

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
"""

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import numpy as np
from scipy import signal
import time
from taylor_win import taylor


class Linear_Array(QObject):
    patternReady = pyqtSignal(np.ndarray, np.ndarray)
    new_data = False

    def updateData(self, array_size, spacing, beam_loc, plot_step, window_type,
                   window_sll, window_nbar):
        self.array_size = array_size
        self.spacing = spacing
        self.beam_loc = beam_loc
        self.plot_step = plot_step
        self.window_type = window_type
        self.window_sll = window_sll
        self.window_nbar = window_nbar
        self.new_data = True

    @pyqtSlot()
    def calculatePattern(self):
        while 1:
            if self.new_data:
                self.new_data = False

                theta = np.arange(-90, 90, self.plot_step)

                array_geometry = np.arange(0, self.spacing * self.array_size,
                                           self.spacing)

                if self.window_type == 0:
                    weight = np.exp(-1j * 2 * np.pi * array_geometry * np.sin(
                        self.beam_loc / 180 * np.pi))
                elif self.window_type == 1:
                    weight = np.exp(-1j * 2 * np.pi * array_geometry * np.sin(
                        self.beam_loc / 180 * np.pi)) * signal.chebwin(
                            self.array_size, at=self.window_sll)
                elif self.window_type == 2:
                    weight = np.exp(-1j * 2 * np.pi * array_geometry * np.sin(
                        self.beam_loc / 180 * np.pi)) * taylor(
                            self.array_size, self.window_nbar, -self.window_sll)
                elif self.window_type == 3:
                    weight = np.exp(-1j * 2 * np.pi * array_geometry * np.sin(
                        self.beam_loc / 180 * np.pi)) * signal.hamming(self.array_size)
                elif self.window_type == 4:
                    weight = np.exp(-1j * 2 * np.pi * array_geometry * np.sin(
                        self.beam_loc / 180 * np.pi)) * signal.hann(self.array_size)
                        

                theta_grid, array_geometry_grid = np.meshgrid(
                    theta, array_geometry)
                A = np.exp(1j * 2 * np.pi * array_geometry_grid * np.sin(
                    theta_grid / 180 * np.pi))

                AF = 20 * np.log10(np.abs(np.matmul(weight, A)) + 0.00001)

                self.patternReady.emit(theta, AF - np.max(AF))

            time.sleep(0.01)