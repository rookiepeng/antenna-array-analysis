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
let arrayColorMode: string = 'amplitude';
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
let computing = false;
let pendingCompute = false;
let firstRenderDone = false;

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
const arrayColorSelect = $('array-color') as HTMLSelectElement;
const plotContainer = $('plot-container');
const insetContainer = $('plot-3d-inset');
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

  if (plotType === '3d' || plotType === '3d-polar') {
    cutSection.style.display = 'none';
    polarSection.style.display = 'none';
    insetContainer.style.display = 'none';
    $('inset-section').style.display = 'none';
  } else if (plotType === 'cartesian') {
    cutSection.style.display = '';
    polarSection.style.display = 'none';
    insetContainer.style.display = 'block';
    $('inset-section').style.display = 'none';
  } else if (plotType === 'polar') {
    cutSection.style.display = '';
    polarSection.style.display = '';
    insetContainer.style.display = 'block';
    $('inset-section').style.display = 'none';
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
  const nfftAz = 512;
  const nfftEl = 512;

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
      insetContainer.style.display = 'none';
      break;
    case '3d-polar':
      render3DPolar(currentResult);
      insetContainer.style.display = 'none';
      break;
    case 'cartesian':
      renderCartesian(currentResult);
      if (insetContainer.style.display !== 'none') {
        render3DInset(currentResult);
      }
      break;
    case 'polar':
      renderPolar(currentResult);
      if (insetContainer.style.display !== 'none') {
        render3DInset(currentResult);
      }
      break;
  }

  renderArrayLayout(currentResult);

  if (!firstRenderDone) {
    firstRenderDone = true;
    const overlay = document.getElementById('startup-overlay');
    if (overlay) {
      overlay.classList.add('hidden');
      overlay.addEventListener('transitionend', () => overlay.remove(), { once: true });
    }
  }
}

function render3DPolar(result: PatternResult) {
  if (!result.arrayFactor2D) return;

  const nAz = result.azimuth.length;
  const nEl = result.elevation.length;

  // Downsample for WebGL performance
  const stride = 3;
  const meshX: number[][] = [];
  const meshY: number[][] = [];
  const meshZ: number[][] = [];
  const surfColor: number[][] = [];

  for (let i = 0; i < nAz; i += stride) {
    const rowX: number[] = [];
    const rowY: number[] = [];
    const rowZ: number[] = [];
    const rowC: number[] = [];
    const azRad = result.azimuth[i] * Math.PI / 180;
    for (let j = 0; j < nEl; j += stride) {
      const elRad = result.elevation[j] * Math.PI / 180;
      const ampDb = result.arrayFactor2D[i][j];
      // Shift dB range to [0, 1]: 0 dB → 1.0, -60 dB → 0.0
      const r = Math.max(ampDb + 60, 0) / 60;
      // x = boresight, y = horizontal (left-right), z = vertical (up-down)
      rowX.push(r * Math.cos(elRad) * Math.cos(azRad));
      rowY.push(r * Math.cos(elRad) * Math.sin(azRad));
      rowZ.push(r * Math.sin(elRad));
      rowC.push(ampDb);
    }
    meshX.push(rowX);
    meshY.push(rowY);
    meshZ.push(rowZ);
    surfColor.push(rowC);
  }

  // Axis reference lines: x=boresight, y=horizontal, z=vertical
  function axisLine(x1: number, y1: number, z1: number, label: string, color: string): Plotly.Data {
    return {
      type: 'scatter3d' as const,
      x: [0, x1],
      y: [0, y1],
      z: [0, z1],
      mode: 'lines+text' as const,
      line: { color, width: 5 },
      text: ['', label],
      textposition: 'top center' as const,
      textfont: { size: 12, color },
      showlegend: false,
      hoverinfo: 'skip' as const,
    } as unknown as Plotly.Data;
  }

  // YZ aperture plane grid (x = 0)
  const planeSize = 1.05;
  const planeSteps = 5;
  const yzPlaneTraces: Plotly.Data[] = [];
  // horizontal lines (sweep y, fixed z)
  for (let s = 0; s <= planeSteps; s++) {
    const zv = -planeSize + s * (2 * planeSize / planeSteps);
    yzPlaneTraces.push({
      type: 'scatter3d' as const,
      x: [0, 0],
      y: [-planeSize, planeSize],
      z: [zv, zv],
      mode: 'lines' as const,
      line: { color: '#3a3a6c', width: 1 },
      showlegend: false,
      hoverinfo: 'skip' as const,
    } as unknown as Plotly.Data);
  }
  // vertical lines (sweep z, fixed y)
  for (let s = 0; s <= planeSteps; s++) {
    const yv = -planeSize + s * (2 * planeSize / planeSteps);
    yzPlaneTraces.push({
      type: 'scatter3d' as const,
      x: [0, 0],
      y: [yv, yv],
      z: [-planeSize, planeSize],
      mode: 'lines' as const,
      line: { color: '#3a3a6c', width: 1 },
      showlegend: false,
      hoverinfo: 'skip' as const,
    } as unknown as Plotly.Data);
  }

  const data: Plotly.Data[] = [
    ...yzPlaneTraces,
    {
      type: 'surface' as const,
      x: meshX as any,
      y: meshY as any,
      z: meshZ as any,
      surfacecolor: surfColor as any,
      colorscale: 'Jet',
      cmin: -60,
      cmax: 0,
      showscale: true,
      colorbar: { title: { text: 'dB', side: 'right' } },
      contours: {
        x: { highlight: false } as any,
        y: { highlight: false } as any,
        z: { highlight: false } as any,
      },
    } as Plotly.Data,
    axisLine(1.35, 0, 0, 'x (boresight)', '#80c0ff'),
    axisLine(0, 1.35, 0, 'y (horizontal)', '#80ffb0'),
    axisLine(0, 0, 1.35, 'z (vertical)', '#ffb080'),
  ];

  const layout: Partial<Plotly.Layout> = {
    scene: {
      xaxis: {
        title: { text: 'x (boresight)' },
        showgrid: false,
        zeroline: false,
        showticklabels: false,
        range: [-1.1, 1.1] as any,
      },
      yaxis: {
        title: { text: 'y (horizontal)' },
        showgrid: false,
        zeroline: false,
        showticklabels: false,
        range: [-1.1, 1.1] as any,
      },
      zaxis: {
        title: { text: 'z (vertical)' },
        showgrid: false,
        zeroline: false,
        showticklabels: false,
        range: [-1.1, 1.1] as any,
      },
      aspectmode: 'cube' as const,
      bgcolor: '#1e1e2e',
      camera: {
        eye: { x: 1.6, y: 1.2, z: 0.8 },
      } as any,
    },
    margin: { l: 0, r: 0, t: 30, b: 0 },
    paper_bgcolor: '#1e1e2e',
    font: { color: '#e0e0f0' },
  };

  Plotly.react(plotContainer, data, layout, { responsive: true });
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

function extractCut(result: PatternResult): { angles: number[]; pattern: number[] } {
  if (!result.arrayFactor2D) {
    return { angles: result.azimuth, pattern: result.arrayFactor };
  }

  if (fixAzimuth) {
    // Fix azimuth → sweep elevation
    const targetAz = parseFloat(plotAzInput.value) || 0;
    let azIdx = 0;
    let minDist = Math.abs(result.azimuth[0] - targetAz);
    for (let i = 1; i < result.azimuth.length; i++) {
      const d = Math.abs(result.azimuth[i] - targetAz);
      if (d < minDist) { minDist = d; azIdx = i; }
    }
    return { angles: result.elevation, pattern: result.arrayFactor2D[azIdx] };
  } else {
    // Fix elevation → sweep azimuth
    const targetEl = parseFloat(plotElInput.value) || 0;
    let elIdx = 0;
    let minDist = Math.abs(result.elevation[0] - targetEl);
    for (let i = 1; i < result.elevation.length; i++) {
      const d = Math.abs(result.elevation[i] - targetEl);
      if (d < minDist) { minDist = d; elIdx = i; }
    }
    const pattern = result.arrayFactor2D.map((row) => row[elIdx]);
    return { angles: result.azimuth, pattern };
  }
}

function renderCartesian(result: PatternResult) {
  const { angles, pattern } = extractCut(result);

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
  const { angles, pattern } = extractCut(result);
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
      sector: [0, 180],
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

function render3DInset(result: PatternResult) {
  if (!result.arrayFactor2D) return;

  const traces: Plotly.Data[] = [
    {
      type: 'heatmap' as const,
      z: result.arrayFactor2D,
      x: result.elevation,
      y: result.azimuth,
      colorscale: 'Jet',
      zmin: -60,
      zmax: 0,
      showscale: false,
      hoverinfo: 'skip' as const,
    },
  ];

  // Add cut-plane line
  if (fixAzimuth) {
    const targetAz = parseFloat(plotAzInput.value) || 0;
    let azIdx = 0;
    let minDist = Math.abs(result.azimuth[0] - targetAz);
    for (let i = 1; i < result.azimuth.length; i++) {
      const d = Math.abs(result.azimuth[i] - targetAz);
      if (d < minDist) { minDist = d; azIdx = i; }
    }
    const cutAz = result.azimuth[azIdx];
    traces.push({
      type: 'scatter' as const,
      x: [result.elevation[0], result.elevation[result.elevation.length - 1]],
      y: [cutAz, cutAz],
      mode: 'lines' as const,
      line: { color: '#f48fb1', width: 2, dash: 'dash' },
      showlegend: false,
      hoverinfo: 'skip' as const,
    });
  } else {
    const targetEl = parseFloat(plotElInput.value) || 0;
    let elIdx = 0;
    let minDist = Math.abs(result.elevation[0] - targetEl);
    for (let i = 1; i < result.elevation.length; i++) {
      const d = Math.abs(result.elevation[i] - targetEl);
      if (d < minDist) { minDist = d; elIdx = i; }
    }
    const cutEl = result.elevation[elIdx];
    traces.push({
      type: 'scatter' as const,
      x: [cutEl, cutEl],
      y: [result.azimuth[0], result.azimuth[result.azimuth.length - 1]],
      mode: 'lines' as const,
      line: { color: '#f48fb1', width: 2, dash: 'dash' },
      showlegend: false,
      hoverinfo: 'skip' as const,
    });
  }

  const layout: Partial<Plotly.Layout> = {
    xaxis: {
      title: { text: 'El (°)', standoff: 2 },
      gridcolor: '#3a3a5c',
      tickfont: { size: 9 },
    },
    yaxis: {
      title: { text: 'Az (°)', standoff: 2 },
      gridcolor: '#3a3a5c',
      tickfont: { size: 9 },
    },
    margin: { l: 36, r: 4, t: 20, b: 30 },
    plot_bgcolor: '#1e1e2e',
    paper_bgcolor: '#1e1e2e',
    font: { color: '#e0e0f0', size: 9 },
  };

  Plotly.react(insetContainer, traces, layout, { responsive: true, displayModeBar: false });
}

function renderArrayLayout(result: PatternResult) {
  const weightAmp = result.weightRe.map((re, i) => Math.sqrt(re * re + result.weightIm[i] * result.weightIm[i]));
  const maxW = Math.max(...weightAmp) || 1;

  let colorValues: number[];
  let colorscale: [number, string][];
  let colorbarTitle: string;
  let cmin: number;
  let cmax: number;

  if (arrayColorMode === 'phase') {
    colorValues = result.weightRe.map((re, i) => (Math.atan2(result.weightIm[i], re) / Math.PI) * 180);
    colorscale = [
      [0, '#3a3a8c'],
      [0.25, '#80c0ff'],
      [0.5, '#f0f0f0'],
      [0.75, '#f48fb1'],
      [1, '#8c1a40'],
    ];
    colorbarTitle = 'Phase (°)';
    cmin = -180;
    cmax = 180;
  } else {
    colorValues = weightAmp.map((w) => w / maxW);
    colorscale = [
      [0, '#3a3a5c'],
      [1, '#f48fb1'],
    ];
    colorbarTitle = 'Amplitude';
    cmin = 0;
    cmax = 1;
  }

  const data: Plotly.Data[] = [
    {
      type: 'scatter' as const,
      x: result.x,
      y: result.y,
      mode: 'markers' as const,
      marker: {
        size: 6,
        color: colorValues,
        colorscale: colorscale as any,
        cmin,
        cmax,
        showscale: true,
        colorbar: {
          title: { text: colorbarTitle, side: 'right' },
        },
      },
      name: 'Elements',
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    xaxis: {
      title: { text: 'Horizontal y (\u03bb)' },
      scaleanchor: 'y',
      gridcolor: '#3a3a5c',
    },
    yaxis: { title: { text: 'Vertical z (\u03bb)' }, gridcolor: '#3a3a5c' },
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

  // Export dropdown
  const exportBtn = $('btn-export');
  const exportMenu = $('export-menu');
  exportBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    exportMenu.style.display = exportMenu.style.display === 'none' ? '' : 'none';
  });
  document.addEventListener('click', () => { exportMenu.style.display = 'none'; });
  $('btn-export-config').addEventListener('click', () => { exportMenu.style.display = 'none'; exportArrayConfig(); });
  $('btn-export-pattern').addEventListener('click', () => { exportMenu.style.display = 'none'; exportPattern(); });

  // Array color mode
  arrayColorSelect.addEventListener('change', () => {
    arrayColorMode = arrayColorSelect.value;
    if (currentResult) renderArrayLayout(currentResult);
  });

  // Help link
  $('link-help').addEventListener('click', (e) => {
    e.preventDefault();
    shell.openExternal(
      'https://github.com/rookiepeng/antenna-array-analysis/issues'
    );
  });

  // Inset close / show
  $('inset-close').addEventListener('click', (e: Event) => {
    e.stopPropagation();
    insetContainer.style.display = 'none';
    $('inset-section').style.display = '';
  });

  $('btn-show-inset').addEventListener('click', () => {
    insetContainer.style.display = 'block';
    $('inset-section').style.display = 'none';
    if (currentResult) render3DInset(currentResult);
  });

  // Inset drag
  const dragHandle = $('inset-drag-handle');
  let dragging = false;
  let dragStartX = 0, dragStartY = 0;
  let dragStartLeft = 0, dragStartTop = 0;

  dragHandle.addEventListener('mousedown', (e: MouseEvent) => {
    dragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragStartLeft = insetContainer.offsetLeft;
    dragStartTop = insetContainer.offsetTop;
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e: MouseEvent) => {
    if (!dragging) return;
    const parent = insetContainer.parentElement!;
    const maxLeft = parent.clientWidth - insetContainer.offsetWidth;
    const maxTop = parent.clientHeight - insetContainer.offsetHeight;
    insetContainer.style.left = Math.max(0, Math.min(dragStartLeft + e.clientX - dragStartX, maxLeft)) + 'px';
    insetContainer.style.top  = Math.max(0, Math.min(dragStartTop  + e.clientY - dragStartY, maxTop))  + 'px';
  });

  document.addEventListener('mouseup', () => { dragging = false; });

  // Resize handling
  window.addEventListener('resize', () => {
    Plotly.Plots.resize(plotContainer);
    if (insetContainer.style.display !== 'none') {
      Plotly.Plots.resize(insetContainer);
    }
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
