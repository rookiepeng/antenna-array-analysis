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

import numpy as np
from scipy import signal


class Linear_Array:
    def __init__(self, array_size, spacing, beam_loc):
        self.array_size = array_size
        self.spacing = spacing
        self.beam_loc = beam_loc

    def getPattern(self):
        theta = np.arange(-90, 90, 0.1)

        array_geometry = np.arange(0, self.spacing * self.array_size,
                                   self.spacing)
        weight = np.exp(-1j * 2 * np.pi * array_geometry * np.sin(
            self.beam_loc / 180 * np.pi))

        theta_grid, array_geometry_grid = np.meshgrid(theta, array_geometry)
        A = np.exp(1j * 2 * np.pi * array_geometry_grid * np.sin(
            theta_grid / 180 * np.pi))

        AF = 20 * np.log10(np.abs(np.matmul(weight, A)) + 0.00001)

        return {'angle': theta, 'pattern': AF - np.max(AF)}
