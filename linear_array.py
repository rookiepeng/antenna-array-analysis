# -*- coding: utf-8 -*-
"""
Created on Sat Feb  2 18:42:52 2019

@author: Zach
"""

import numpy as np
from scipy import signal


class Linear_Array:
    def __init__(self, array_size, spacing, beam_loc):
        self.array_size = array_size
        self.spacing = spacing
        self.beam_loc = beam_loc

    def getPattern(self):
        theta = np.arange(-90, 90, 0.02)

        array_geometry = np.arange(0, self.spacing * self.array_size,
                                   self.spacing)
        weight = np.exp(-1j * 2 * np.pi * array_geometry * np.sin(
            self.beam_loc / 180 * np.pi))

        theta_grid, array_geometry_grid = np.meshgrid(theta, array_geometry)
        A = np.exp(1j * 2 * np.pi * array_geometry_grid * np.sin(
            theta_grid / 180 * np.pi))

        AF = 20 * np.log10(np.abs(np.matmul(weight, A)) + 0.00001)

        return {'angle': theta, 'pattern': AF - np.max(AF)}
