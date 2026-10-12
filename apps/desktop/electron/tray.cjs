'use strict'

/**
 * AetherOS tray host (Master 64.1 A3) — Electron wiring for tray-menu.cjs.
 *
 * STATUS: IMPLEMENTED — UNVERIFIED (no Electron binary in this workspace,
 * no packaged build run here). Requires `electron` + app 'ready'.
 * Design: menu template comes from buildTrayMenu(liveState); clicks
 * re-emit the typed channel to the main window's webContents (the same
 * command layer the UI uses). Shell-restart recovery: rebuild on
 * 'ready' and on taskbar-created signal where available.
 */

const { buildTrayMenu } = require('./tray-menu.cjs')

let tray = null

function setupTray(electron, getState, dispatch, iconPath) {
  const { app, Tray, Menu, nativeImage } = electron
  if (!app || !Tray || !Menu) {
    throw new Error('tray unavailable: Electron Tray/Menu APIs missing')
  }
  const image = iconPath && nativeImage ? nativeImage.createFromPath(iconPath) : undefined
  tray = new Tray(image)
  tray.setToolTip('AetherOS')
  tray.on('click', () => dispatch('aetheros:window-show', {}))

  const refresh = () => {
    let state = {}
    try {
      state = getState() || {}
    } catch {
      state = { backendUp: false }
    }
    const { tooltip, items } = buildTrayMenu(state)
    tray.setToolTip(tooltip)
    tray.setContextMenu(Menu.buildFromTemplate(items.map(i => ({
      id: i.id,
      label: i.label,
      enabled: i.enabled,
      click: () => dispatch(i.channel, { source: 'tray', confirm: Boolean(i.confirm) }),
    }))))
  }

  refresh()
  const timer = setInterval(refresh, 15000)
  if (timer.unref) timer.unref()
  return { refresh, destroy: () => { clearInterval(timer); tray?.destroy(); tray = null } }
}

module.exports = { setupTray }
