const os = require('node:os')

let lastCpuInfo = os.cpus()

function getCpuUsage() {
  const current = os.cpus()
  let idle = 0
  let total = 0

  for (let i = 0; i < current.length; i++) {
    const curr = current[i].times
    const prev = lastCpuInfo[i]?.times
    if (!prev) continue
    const currTotal = curr.user + curr.nice + curr.sys + curr.idle + curr.irq
    const prevTotal = prev.user + prev.nice + prev.sys + prev.idle + prev.irq
    const delta = currTotal - prevTotal
    const deltaIdle = curr.idle - prev.idle
    if (delta > 0) {
      idle += deltaIdle / delta
      total += 1
    }
  }

  lastCpuInfo = current
  return total > 0 ? Math.round((1 - idle / total) * 100) : 0
}

function getMemoryInfo() {
  const total = os.totalmem()
  const free = os.freemem()
  const used = total - free
  return {
    used: Math.round(used / 1024 / 1024),
    total: Math.round(total / 1024 / 1024),
    percent: Math.round((used / total) * 100)
  }
}

function getGpuInfo() {
  try {
    const { execFileSync } = require('node:child_process')
    const platform = process.platform
    if (platform === 'win32') {
      const result = execFileSync('wmic', ['path', 'win32_VideoController', 'get', 'name'], {
        encoding: 'utf8',
        timeout: 2000
      })
      const lines = result.trim().split('\n').filter(Boolean)
      const name = lines.length > 1 ? lines[1].trim() : 'Unknown GPU'
      return { name, percent: 0, used: 0, total: 0 }
    }
    if (platform === 'darwin') {
      return { name: 'Apple Silicon / Metal GPU', percent: 0, used: 0, total: 0 }
    }
    if (platform === 'linux') {
      try {
        const result = execFileSync('nvidia-smi', [
          '--query-gpu=name,memory.used,memory.total,utilization.gpu',
          '--format=csv,noheader,nounits'
        ], { encoding: 'utf8', timeout: 2000 })
        const parts = result.trim().split(', ')
        if (parts.length >= 4) {
          return {
            name: parts[0],
            used: parseInt(parts[1], 10) || 0,
            total: parseInt(parts[2], 10) || 0,
            percent: parseInt(parts[3], 10) || 0
          }
        }
      } catch {
        return null
      }
    }
  } catch {
    // GPU info not available
  }
  return null
}

function getSystemStats() {
  return {
    cpu: getCpuUsage(),
    memory: getMemoryInfo(),
    gpu: getGpuInfo(),
    platform: process.platform,
    hostname: os.hostname(),
    uptime: Math.floor(os.uptime())
  }
}

function startPolling(intervalMs = 5000) {
  return setInterval(() => {
    lastCpuInfo = os.cpus()
  }, intervalMs)
}

module.exports = { getSystemStats, startPolling }
