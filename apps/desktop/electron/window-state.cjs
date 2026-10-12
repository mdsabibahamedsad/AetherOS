const fs = require('node:fs')
const path = require('node:path')
const { app, screen } = require('electron')

const STATE_FILE = 'window-state.json'

function getStatePath() {
  return path.join(app.getPath('userData'), STATE_FILE)
}

function loadState() {
  try {
    const raw = fs.readFileSync(getStatePath(), 'utf8')
    return JSON.parse(raw)
  } catch {
    return null
  }
}

function saveState(state) {
  try {
    const dir = path.dirname(getStatePath())
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true })
    }
    fs.writeFileSync(getStatePath(), JSON.stringify(state, null, 2))
  } catch {
    // Non-fatal
  }
}

function safeDisplayBounds() {
  try {
    const display = screen.getPrimaryDisplay()
    if (display && display.workArea && typeof display.workArea.width === 'number' && typeof display.workArea.height === 'number') {
      return display.workArea
    }
  } catch {
    // screen API may return undefined in headless/restricted sessions
  }
  return { x: 0, y: 0, width: 1280, height: 800 }
}

function getValidatedBounds(saved, defaults = { width: 1280, height: 800 }) {
  if (!saved || saved.x === undefined || saved.y === undefined) {
    const bounds = safeDisplayBounds()
    return {
      x: Math.round((bounds.width - defaults.width) / 2 + bounds.x),
      y: Math.round((bounds.height - defaults.height) / 2 + bounds.y),
      width: defaults.width,
      height: defaults.height
    }
  }

  const displays = screen.getAllDisplays()
  const onDisplay = displays.some(d => {
    if (!d || !d.workArea) return false
    const { x, y, width, height } = d.workArea
    return (
      saved.x >= x && saved.x < x + width && saved.y >= y && saved.y < y + height
    )
  })

  if (!onDisplay) {
    const bounds = safeDisplayBounds()
    return {
      x: Math.round((bounds.width - saved.width) / 2 + bounds.x),
      y: Math.round((bounds.height - saved.height) / 2 + bounds.y),
      width: saved.width,
      height: saved.height
    }
  }

  return saved
}

function createWindowMenuTemplate(appWin) {
  return [
    {
      label: 'AetherOS',
      submenu: [
        { role: 'about', label: 'About AetherOS' },
        { type: 'separator' },
        {
          label: 'Settings',
          accelerator: 'CmdOrCtrl+,',
          click: () => appWin.webContents.send('aetheros:open-settings')
        },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    },
    {
      label: 'File',
      submenu: [
        {
          label: 'New Chat',
          accelerator: 'CmdOrCtrl+N',
          click: () => appWin.webContents.send('aetheros:new-chat')
        },
        {
          label: 'New Project',
          accelerator: 'CmdOrCtrl+Shift+N',
          click: () => appWin.webContents.send('aetheros:new-project')
        },
        { type: 'separator' },
        {
          label: 'Open File...',
          accelerator: 'CmdOrCtrl+O',
          click: () => appWin.webContents.send('aetheros:open-file')
        },
        {
          label: 'Open Folder...',
          accelerator: 'CmdOrCtrl+Shift+O',
          click: () => appWin.webContents.send('aetheros:open-folder')
        }
      ]
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'selectAll' }
      ]
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    },
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        { type: 'separator' },
        { role: 'front' },
        { type: 'separator' },
        { role: 'window' }
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'AetherOS Documentation',
          click: () => require('electron').shell.openExternal('https://aetheros.ai/docs')
        },
        {
          label: 'Report Issue',
          click: () => require('electron').shell.openExternal('https://github.com/aetheros/aetheros/issues')
        }
      ]
    }
  ]
}

module.exports = { loadState, saveState, getValidatedBounds, createWindowMenuTemplate }
