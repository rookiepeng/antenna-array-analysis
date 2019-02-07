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


def taylor(N, nbar=4, level=-30):
    """
    Return the Taylor window.
    The Taylor window allows for a selectable sidelobe suppression with a 
    minimum broadening. This window is commonly used in radar processing [1].
    Parameters
    ----------
    M : int
        Number of points in the output window. If zero or less, an
        empty array is returned.
    nbar : int
        Number of nearly constant level sidelobes adjacent to the mainlobe
    level : float
        Desired peak sidelobe level in decibels (db) relative to the mainlobe
    Returns
    -------
    out : array
        The window, with the center value normalized to one (the value
        one appears only if the number of samples is odd).
    See Also
    --------
    kaiser, bartlett, blackman, hamming, hanning
    References
    -----
    .. [1] W. Carrara, R. Goodman, and R. Majewski "Spotlight Synthetic 
               Aperture Radar: Signal Processing Algorithms" Pages 512-513,
               July 1995.
    """
    B = 10**(-level / 20)
    A = np.log(B + np.sqrt(B**2 - 1)) / np.pi
    s2 = nbar**2 / (A**2 + (nbar - 0.5)**2)
    ma = np.arange(1, nbar)

    def calc_Fm(m):
        numer = (-1)**(m + 1) * np.prod(1 - m**2 / s2 / (A**2 + (ma - 0.5)**2))
        denom = 2 * np.prod([1 - m**2 / j**2 for j in ma if j != m])
        return numer / denom

    calc_Fm_vec = np.vectorize(calc_Fm)
    Fm = calc_Fm_vec(ma)

    def W(n):
        return 2 * np.dot(Fm, np.cos(2 * np.pi * ma *
                                     (n - N / 2 + 1 / 2) / N)) + 1

    W_vec = np.vectorize(W)
    w = W_vec(range(N))

    # normalize (Note that this is not described in the original text [1])
    scale = 1.0 / W((N - 1) / 2)
    w *= scale
    return w