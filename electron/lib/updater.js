const { autoUpdater } = require('electron-updater');
const { dialog } = require('electron');

function initAutoUpdater(mainWindow) {
  autoUpdater.logger = console;
  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;

  autoUpdater.on('checking-for-update', () => {
    console.log('[updater] Checking for update...');
  });

  autoUpdater.on('update-available', (info) => {
    console.log(`[updater] Update available: ${info.version}`);
  });

  autoUpdater.on('update-not-available', () => {
    console.log('[updater] App is up to date.');
  });

  autoUpdater.on('download-progress', (progress) => {
    console.log(`[updater] Download: ${Math.round(progress.percent)}%`);
  });

  autoUpdater.on('update-downloaded', (info) => {
    console.log(`[updater] Update downloaded: ${info.version}`);
    dialog
      .showMessageBox(mainWindow, {
        type: 'info',
        title: 'Update Ready',
        message: 'A new version of ArcLight has been downloaded.',
        detail: `Version ${info.version} is ready to install. Restart now to apply the update.`,
        buttons: ['Restart Now', 'Later'],
        defaultId: 0,
        cancelId: 1,
      })
      .then(({ response }) => {
        if (response === 0) {
          autoUpdater.quitAndInstall();
        }
      });
  });

  autoUpdater.on('error', (err) => {
    console.error('[updater] Error:', err.message);
  });

  autoUpdater.checkForUpdatesAndNotify();
}

module.exports = { initAutoUpdater };
