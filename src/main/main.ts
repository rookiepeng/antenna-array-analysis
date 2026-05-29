/**
 * Electron main process
 */

import { app, BrowserWindow, ipcMain } from 'electron';
import * as path from 'path';
import { PythonBridge, ComputeConfig } from './pythonBridge';

const pythonBridge = new PythonBridge();

function createWindow(): void {
  const mainWindow = new BrowserWindow({
    width: 1400,
    height: 850,
    minWidth: 900,
    minHeight: 600,
    title: 'Antenna Array Analysis',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
    backgroundColor: '#1e1e2e',
  });

  mainWindow.loadFile(path.join(__dirname, '..', '..', 'src', 'renderer', 'index.html'));

  mainWindow.setMenuBarVisibility(false);
}

// IPC handler for pattern computation
ipcMain.handle('compute-pattern', async (_event, config: ComputeConfig) => {
  try {
    return await pythonBridge.compute(config);
  } catch (err: unknown) {
    // 'superseded' is a normal cancellation signal, not an error worth logging.
    if (err instanceof Error && err.message === 'superseded') {
      return { superseded: true };
    }
    throw err;
  }
});

app.whenReady().then(() => {
  pythonBridge.start();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    pythonBridge.stop();
    app.quit();
  }
});

app.on('before-quit', () => {
  pythonBridge.stop();
});
