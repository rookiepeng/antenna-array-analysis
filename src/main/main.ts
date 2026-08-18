/**
 * Electron main process
 */

import { app, BrowserWindow, ipcMain } from 'electron';
import { spawn } from 'child_process';
import * as path from 'path';
import { PythonBridge, ComputeConfig } from './pythonBridge';

// ---------------------------------------------------------------------------
// Squirrel.Windows event handling
// ---------------------------------------------------------------------------
// Squirrel re-launches the app executable with special command-line flags
// (--squirrel-install, --squirrel-updated, --squirrel-uninstall,
// --squirrel-obsolete) during lifecycle events.  We must handle them as early
// as possible and quit immediately so the app does not fully start up (e.g.
// open a window or launch the Python bridge) while it is being installed,
// updated, or removed.
// ---------------------------------------------------------------------------

function handleSquirrelEvent(): boolean {
  if (process.platform !== 'win32') return false;

  const squirrelArg = process.argv[1];
  if (!squirrelArg) return false;

  const appFolder = path.resolve(process.execPath, '..');
  const rootFolder = path.resolve(appFolder, '..');
  const updateExe = path.join(rootFolder, 'Update.exe');
  const exeName = path.basename(process.execPath);

  const spawnUpdate = (args: string[]): void => {
    spawn(updateExe, args, { detached: true }).unref();
  };

  switch (squirrelArg) {
    case '--squirrel-install':
    case '--squirrel-updated':
      // Create desktop & Start Menu shortcuts
      spawnUpdate(['--createShortcut', exeName]);
      return true;

    case '--squirrel-uninstall':
      // Remove shortcuts
      spawnUpdate(['--removeShortcut', exeName]);
      return true;

    case '--squirrel-obsolete':
      // Old version being replaced — just quit
      return true;

    default:
      return false;
  }
}

if (handleSquirrelEvent()) {
  // Give Update.exe a moment to finish, then exit.
  setTimeout(() => app.quit(), 1000);
}

const pythonBridge = new PythonBridge();

function createWindow(): void {
  const mainWindow = new BrowserWindow({
    width: 1400,
    height: 850,
    minWidth: 900,
    minHeight: 600,
    title: 'BeamScope',
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
