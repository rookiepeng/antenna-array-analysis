/**
 * Renderer process - UI logic and Plotly visualization
 */

const { ipcRenderer, shell } = require('electron');

// Plotly types + runtime require
import type * as PlotlyType from 'plotly.js';
const Plotly: typeof PlotlyType = require('plotly.js-dist-min');

// ---- Types ----
interface PatternResult {
  arrayFactor: number[];
  arrayFactor2D?: number[][];
  x: number[];
  y: number[];
  weightRe: number[];
  weightIm: number[];
  azimuth: number[];
  elevation: number[];
  error?: string;
}

type WindowType = 'Square' | 'Chebyshev' | 'Taylor' | 'Hamming' | 'Hann';

const WINDOW_INDEX: Record<WindowType, number> = {
  'Square': 0,
  'Chebyshev': 1,
  'Taylor': 2,
  'Hamming': 3,
  'Hann': 4,
};

// ---- State ----
let fixAzimuth = false;
let currentResult: PatternResult | null = null;
let plotType: string = '3d';
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
let computing = false;
let pendingCompute = false;

// ---- DOM Elements ----
const $ = (id: string) => document.getElementById(id)!;

const sizexInput = $('sizex') as HTMLInputElement;
const sizeyInput = $('sizey') as HTMLInputElement;
const spacingxInput = $('spacingx') as HTMLInputElement;
const spacingyInput = $('spacingy') as HTMLInputElement;
const windowxSelect = $('windowx') as HTMLSelectElement;
const windowySelect = $('windowy') as HTMLSelectElement;
const sllxInput = $('sllx') as HTMLInputElement;
const sllxSlider = $('sllx-slider') as HTMLInputElement;
const sllyInput = $('slly') as HTMLInputElement;
const sllySlider = $('slly-slider') as HTMLInputElement;
const nbarxInput = $('nbarx') as HTMLInputElement;
const nbarxSlider = $('nbarx-slider') as HTMLInputElement;
const nbaryInput = $('nbary') as HTMLInputElement;
const nbarySlider = $('nbary-slider') as HTMLInputElement;
const beamAzInput = $('beam-az') as HTMLInputElement;
const beamAzSlider = $('beam-az-slider') as HTMLInputElement;
const beamElInput = $('beam-el') as HTMLInputElement;
const beamElSlider = $('beam-el-slider') as HTMLInputElement;
const plotTypeSelect = $('plot-type') as HTMLSelectElement;
const fixElevationRadio = $('fix-elevation') as HTMLInputElement;
const fixAzimuthRadio = $('fix-azimuth') as HTMLInputElement;
const plotElInput = $('plot-el') as HTMLInputElement;
const plotElSlider = $('plot-el-slider') as HTMLInputElement;
const plotAzInput = $('plot-az') as HTMLInputElement;
const plotAzSlider = $('plot-az-slider') as HTMLInputElement;
const polarMinInput = $('polar-min') as HTMLInputElement;
const polarMinSlider = $('polar-min-slider') as HTMLInputElement;
const plotContainer = $('plot-container');
const layoutContainer = $('layout-container');

// ---- Sync helpers ----
function syncSliderToInput(slider: HTMLInputElement, input: HTMLInputElement, scale: number = 1) {
  input.value = String(parseInt(slider.value) / scale);
  scheduleUpdate();
}

function syncInputToSlider(input: HTMLInputElement, slider: HTMLInputElement, scale: number = 1) {
  slider.value = String(Math.round(parseFloat(input.value) * scale));
  scheduleUpdate();
}

function syncPair(input: HTMLInputElement, slider: HTMLInputElement, scale: number = 1) {
  input.addEventListener('input', () => syncInputToSlider(input, slider, scale));
  slider.addEventListener('input', () => syncSliderToInput(slider, input, scale));
}

function syncPairDirect(input: HTMLInputElement, slider: HTMLInputElement) {
  input.addEventListener('input', () => { slider.value = input.value; scheduleUpdate(); });
  slider.addEventListener('input', () => { input.value = slider.value; scheduleUpdate(); });
}

// ---- Window visibility ----
function updateWindowControls(axis: 'x' | 'y', value: string) {
  const sllRow = $(`sll${axis}-row`);
  const nbarRow = $(`nbar${axis}-row`);

  if (value === 'Chebyshev') {
    sllRow.style.display = '';
    nbarRow.style.display = 'none';
  } else if (value === 'Taylor') {
    sllRow.style.display = '';
    nbarRow.style.display = '';
  } else {
    sllRow.style.display = 'none';
    nbarRow.style.display = 'none';
  }
}

// ---- Plot type changes ----
function updatePlotTypeUI() {
  const cutSection = $('cut-plane-section');
  const polarSection = $('polar-min-section');

  if (plotType === '3d') {
    cutSection.style.display = 'none';
    polarSection.style.display = 'none';
  } else if (plotType === 'cartesian') {
    cutSection.style.display = '';
    polarSection.style.display = 'none';
  } else if (plotType === 'polar') {
    cutSection.style.display = '';
    polarSection.style.display = '';
  }

  updateFixPlaneUI();
}

function updateFixPlaneUI() {
  const fixElRow = $('fix-el-row');
  const fixAzRow = $('fix-az-row');

  if (fixAzimuth) {
    fixAzRow.style.display = '';
    fixElRow.style.display = 'none';
    fixAzimuthRadio.checked = true;
    fixElevationRadio.checked = false;
  } else {
    fixAzRow.style.display = 'none';
    fixElRow.style.display = '';
    fixElevationRadio.checked = true;
    fixAzimuthRadio.checked = false;
  }
}

// ---- Build config ----
function getConfig() {
  let nfftAz: number, nfftEl: number;

  if (plotType === '3d') {
    nfftAz = 512;
    nfftEl = 512;
  } else {
    if (fixAzimuth) {
      nfftAz = 1;
      nfftEl = 4096;
    } else {
      nfftAz = 4096;
      nfftEl = 1;
    }
  }

  return {
    sizex: parseInt(sizexInput.value) || 64,
    sizey: parseInt(sizeyInput.value) || 32,
    spacingx: parseFloat(spacingxInput.value) || 0.5,
    spacingy: parseFloat(spacingyInput.value) || 0.5,
    beamAz: parseFloat(beamAzInput.value) || 0,
    beamEl: parseFloat(beamElInput.value) || 0,
    windowx: WINDOW_INDEX[windowxSelect.value as WindowType] ?? 0,
    windowy: WINDOW_INDEX[windowySelect.value as WindowType] ?? 0,
    sllx: parseInt(sllxInput.value) || 60,
    slly: parseInt(sllyInput.value) || 60,
    nbarx: parseInt(nbarxInput.value) || 4,
    nbary: parseInt(nbaryInput.value) || 4,
    nfftAz,
    nfftEl,
    plotAz: parseFloat(plotAzInput.value) || 0,
    plotEl: parseFloat(plotElInput.value) || 0,
  };
}

// ---- Compute & Plot ----
function scheduleUpdate() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(computeAndPlot, 50);
}

function computeAndPlot() {
  if (computing) {
    // A computation is in-flight; mark dirty so we re-run when it resolves
    pendingCompute = true;
    return;
  }

  computing = true;
  pendingCompute = false;
  const config = getConfig();

  ipcRenderer.invoke('compute-pattern', config)
    .then((result: PatternResult) => {
      computing = false;
      if (result.error) {
        console.error('Python compute error:', result.error);
      } else {
        currentResult = result;
        renderPlot();
      }
      if (pendingCompute) computeAndPlot();
    })
    .catch((err: Error) => {
      computing = false;
      console.error('IPC error:', err.message);
      if (pendingCompute) scheduleUpdate();
    });
}

function renderPlot() {
  if (!currentResult) return;

  switch (plotType) {
    case '3d':
      render3D(currentResult);
      break;
    case 'cartesian':
      renderCartesian(currentResult);
      break;
    case 'polar':
      renderPolar(currentResult);
      break;
  }

  renderArrayLayout(currentResult);
}

function render3D(result: PatternResult) {
  if (!result.arrayFactor2D) return;

  const data: Plotly.Data[] = [
    {
      type: 'surface' as const,
      z: result.arrayFactor2D,
      x: result.elevation,
      y: result.azimuth,
      colorscale: 'Jet',
      zmin: -100,
      zmax: 0,
      showscale: true,
      colorbar: {
        title: { text: 'dB', side: 'right' },
      },
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    scene: {
      xaxis: { title: { text: 'Elevation (°)' } },
      yaxis: { title: { text: 'Azimuth (°)' } },
      zaxis: { title: { text: 'Amplitude (dB)' }, range: [-100, 0] },
    },
    margin: { l: 0, r: 0, t: 30, b: 0 },
    paper_bgcolor: '#1e1e2e',
    font: { color: '#e0e0f0' },
  };

  Plotly.react(plotContainer, data, layout, { responsive: true });
}

function renderCartesian(result: PatternResult) {
  const angles = fixAzimuth ? result.elevation : result.azimuth;
  const pattern = result.arrayFactor;

  const data: Plotly.Data[] = [
    {
      type: 'scatter' as const,
      x: angles,
      y: pattern,
      mode: 'lines' as const,
      line: { color: '#f48fb1', width: 2 },
      name: 'Pattern',
    },
  ];

  const xLabel = fixAzimuth ? 'Elevation (°)' : 'Azimuth (°)';

  const layout: Partial<Plotly.Layout> = {
    xaxis: { title: { text: xLabel }, range: [-90, 90], gridcolor: '#3a3a5c' },
    yaxis: {
      title: { text: 'Normalized Amplitude (dB)' },
      range: [-80, 0],
      gridcolor: '#3a3a5c',
    },
    plot_bgcolor: '#1e1e2e',
    paper_bgcolor: '#1e1e2e',
    font: { color: '#e0e0f0' },
    margin: { l: 60, r: 20, t: 30, b: 50 },
    showlegend: false,
  };

  Plotly.react(plotContainer, data, layout, { responsive: true });
}

function renderPolar(result: PatternResult) {
  const angles = fixAzimuth ? result.elevation : result.azimuth;
  const pattern = result.arrayFactor;
  const minAmp = parseFloat(polarMinInput.value) || -60;

  // Clamp pattern values
  const clamped = pattern.map((v) => Math.max(v, minAmp));
  // Shift to make minAmp -> 0
  const shifted = clamped.map((v) => v - minAmp);

  const data: Plotly.Data[] = [
    {
      type: 'scatterpolar' as const,
      r: shifted,
      theta: angles,
      mode: 'lines' as const,
      line: { color: '#f48fb1', width: 2 },
      name: 'Pattern',
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    polar: {
      bgcolor: '#1e1e2e',
      radialaxis: {
        visible: true,
        range: [0, -minAmp],
        gridcolor: '#3a3a5c',
        color: '#e0e0f0',
      },
      angularaxis: {
        gridcolor: '#3a3a5c',
        color: '#e0e0f0',
        direction: 'clockwise' as const,
        rotation: 90,
      },
    },
    paper_bgcolor: '#1e1e2e',
    font: { color: '#e0e0f0' },
    margin: { l: 40, r: 40, t: 30, b: 40 },
    showlegend: false,
  };

  Plotly.react(plotContainer, data, layout, { responsive: true });
}

function renderArrayLayout(result: PatternResult) {
  const weightAmp = result.weightRe.map((re, i) => Math.sqrt(re * re + result.weightIm[i] * result.weightIm[i]));
  const maxW = Math.max(...weightAmp) || 1;
  const normWeight = weightAmp.map((w) => w / maxW);

  const data: Plotly.Data[] = [
    {
      type: 'scatter' as const,
      x: result.x,
      y: result.y,
      mode: 'markers' as const,
      marker: {
        size: 6,
        color: normWeight,
        colorscale: [
          [0, '#3a3a5c'],
          [1, '#f48fb1'],
        ],
        showscale: true,
        colorbar: {
          title: { text: 'Weight', side: 'right' },
        },
      },
      name: 'Elements',
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    xaxis: {
      title: { text: 'Horizontal x (λ)' },
      scaleanchor: 'y',
      gridcolor: '#3a3a5c',
    },
    yaxis: { title: { text: 'Vertical y (λ)' }, gridcolor: '#3a3a5c' },
    plot_bgcolor: '#1e1e2e',
    paper_bgcolor: '#1e1e2e',
    font: { color: '#e0e0f0' },
    margin: { l: 60, r: 20, t: 30, b: 50 },
    showlegend: false,
  };

  Plotly.react(layoutContainer, data, layout, { responsive: true });
}

// ---- CSV Export ----
function downloadCSV(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function exportArrayConfig() {
  if (!currentResult) return;
  const lines = ['x (wavelength),y (wavelength),amplitude (linear),phase (degree)'];
  for (let i = 0; i < currentResult.x.length; i++) {
    const re = currentResult.weightRe[i];
    const im = currentResult.weightIm[i];
    const amp = Math.sqrt(re * re + im * im);
    const phase = (Math.atan2(im, re) / Math.PI) * 180;
    lines.push(
      `${currentResult.x[i].toExponential(8)},${currentResult.y[i].toExponential(8)},${amp.toExponential(8)},${phase.toExponential(8)}`
    );
  }
  downloadCSV('array_config.csv', lines.join('\n'));
}

function exportPattern() {
  if (!currentResult) return;
  const lines = ['azimuth (degree),elevation (degree),pattern (dB)'];
  const { azimuth, elevation, arrayFactor, arrayFactor2D } = currentResult;

  if (arrayFactor2D) {
    for (let ai = 0; ai < azimuth.length; ai++) {
      for (let ei = 0; ei < elevation.length; ei++) {
        lines.push(
          `${azimuth[ai].toExponential(8)},${elevation[ei].toExponential(8)},${arrayFactor2D[ai][ei].toExponential(8)}`
        );
      }
    }
  } else {
    for (let i = 0; i < arrayFactor.length; i++) {
      const az = azimuth.length > 1 ? azimuth[i] : azimuth[0];
      const el = elevation.length > 1 ? elevation[i] : elevation[0];
      lines.push(
        `${az.toExponential(8)},${el.toExponential(8)},${arrayFactor[i].toExponential(8)}`
      );
    }
  }
  downloadCSV('pattern.csv', lines.join('\n'));
}

// ---- Event wiring ----
function init() {
  // Array config
  [sizexInput, sizeyInput, spacingxInput, spacingyInput].forEach((el) =>
    el.addEventListener('input', scheduleUpdate)
  );

  // Window selects
  windowxSelect.addEventListener('change', () => {
    updateWindowControls('x', windowxSelect.value);
    scheduleUpdate();
  });
  windowySelect.addEventListener('change', () => {
    updateWindowControls('y', windowySelect.value);
    scheduleUpdate();
  });

  // Slider/input pairs
  syncPair(beamAzInput, beamAzSlider, 10);
  syncPair(beamElInput, beamElSlider, 10);
  syncPair(plotAzInput, plotAzSlider, 10);
  syncPair(plotElInput, plotElSlider, 10);
  syncPairDirect(sllxInput, sllxSlider);
  syncPairDirect(sllyInput, sllySlider);
  syncPairDirect(nbarxInput, nbarxSlider);
  syncPairDirect(nbaryInput, nbarySlider);
  syncPairDirect(polarMinInput, polarMinSlider);

  // Plot type
  plotTypeSelect.addEventListener('change', () => {
    plotType = plotTypeSelect.value;
    updatePlotTypeUI();
    scheduleUpdate();
  });

  // Fix plane radio
  fixElevationRadio.addEventListener('change', () => {
    fixAzimuth = false;
    updateFixPlaneUI();
    scheduleUpdate();
  });
  fixAzimuthRadio.addEventListener('change', () => {
    fixAzimuth = true;
    updateFixPlaneUI();
    scheduleUpdate();
  });

  // Export buttons
  $('btn-export-config').addEventListener('click', exportArrayConfig);
  $('btn-export-pattern').addEventListener('click', exportPattern);

  // Help link
  $('link-help').addEventListener('click', (e) => {
    e.preventDefault();
    shell.openExternal(
      'https://github.com/rookiepeng/antenna-array-analysis/issues'
    );
  });

  // Resize handling
  window.addEventListener('resize', () => {
    Plotly.Plots.resize(plotContainer);
    Plotly.Plots.resize(layoutContainer);
  });

  // Initial state
  updatePlotTypeUI();
  updateWindowControls('x', windowxSelect.value);
  updateWindowControls('y', windowySelect.value);

  // Initial compute
  computeAndPlot();
}

document.addEventListener('DOMContentLoaded', init);
