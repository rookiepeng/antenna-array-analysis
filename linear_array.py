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
from scipy.signal import chebwin, hamming, hann
from time import sleep
from taylor_win import taylor


class Linear_Array(QObject):
    patternReady = pyqtSignal(np.ndarray, np.ndarray, object)
    new_data = False

    def __init__(self):
        super(Linear_Array, self).__init__()
        self.window_dict = {
            0: self.square_win,
            1: self.cheb_win,
            2: self.taylor_win,
            3: self.hamming_win,
            4: self.hann_win
        }
        self.array_size = 64
        self.spacing = 0.5
        self.beam_loc = 0
        self.theta = np.linspace(-90, 90, num=1801, endpoint=True)
        self.window_type = 0
        self.window_sll = 60
        self.window_nbar = 20
        self.new_data = False
        self.plot = 'Cartesian'

    def updateData(self, linear_array_config, theta, plot):
        self.array_size = linear_array_config['array_size']
        self.spacing = linear_array_config['spacing']
        self.beam_loc = linear_array_config['beam_loc']
        self.theta = theta
        self.window_type = linear_array_config['window_type_idx']
        self.window_sll = linear_array_config['window_sll']
        self.window_nbar = linear_array_config['window_nbar']
        self.new_data = True
        self.plot = plot

    def square_win(self, array_size=1, sll=0, nbar=0):
        return 1

    def cheb_win(self, array_size, sll, nbar=0):
        return chebwin(array_size, at=sll)

    def taylor_win(self, array_size, sll, nbar):
        return taylor(array_size, nbar, -sll)

    def hamming_win(self, array_size, sll=0, nbar=0):
        return hamming(array_size)

    def hann_win(self, array_size, sll=0, nbar=0):
        return hann(array_size)

    @pyqtSlot()
    def calculatePattern(self):
        while 1:
            if self.new_data:
                self.new_data = False

                array_geometry = np.arange(0, self.spacing * self.array_size,
                                           self.spacing)

                weight = np.exp(-1j * 2 * np.pi * array_geometry * np.sin(
                    self.beam_loc / 180 * np.pi)) * self.window_dict[
                             self.window_type](self.array_size, self.window_sll,
                                               self.window_nbar)

                weight = weight / np.sum(np.abs(weight))

                theta_grid, array_geometry_grid = np.meshgrid(
                    self.theta, array_geometry)
                A = np.exp(1j * 2 * np.pi * array_geometry_grid * np.sin(
                    theta_grid / 180 * np.pi))

                AF = 20 * np.log10(np.abs(np.matmul(weight, A)) + 0.00001)

                self.patternReady.emit(self.theta, AF, self.plot)

            sleep(0.01)

'''
    Z. Peng

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

'''