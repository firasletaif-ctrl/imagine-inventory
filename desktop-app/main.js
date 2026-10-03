const { app, BrowserWindow, Menu } = require('electron');
const path = require('path');

const APP_URL = 'https://imagine-inventory.onrender.com';

// Une seule instance de l'app
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  let win;
  function createWindow() {
    win = new BrowserWindow({
      width: 1366,
      height: 850,
      minWidth: 1000,
      minHeight: 640,
      icon: path.join(__dirname, 'icon.png'),
      backgroundColor: '#0B1D3A',
      title: 'Imagine Events — Gestion du dépôt',
      webPreferences: {
        spellcheck: false,
        zoomFactor: 1.0
      }
    });
    win.loadURL(APP_URL);
    win.on('closed', () => { win = null; });
  }
  app.on('second-instance', () => {
    if (win) { if (win.isMinimized()) win.restore(); win.focus(); }
  });
  app.whenReady().then(createWindow);
  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
  });
}
