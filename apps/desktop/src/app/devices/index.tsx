import { useStore } from '@nanostores/react'
import { useCallback, useMemo, useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { SearchField } from '@/components/ui/search-field'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import {
  $deviceFilterOS,
  $deviceLoading,
  $devices,
  $deviceSearch,
  type DeviceInfo,
  type DeviceOS,
  renameDevice,
  revokeDevice,
  setDeviceFilterOS,
  setDeviceSearch,
} from '@/store/devices'
import { notify } from '@/store/notifications'

const OS_OPTIONS: { value: DeviceOS | 'all'; label: string; icon: string }[] = [
  { value: 'all', label: 'All OS', icon: 'symbol-misc' },
  { value: 'windows', label: 'Windows', icon: 'symbol-misc' },
  { value: 'macos', label: 'macOS', icon: 'symbol-misc' },
  { value: 'linux', label: 'Linux', icon: 'symbol-misc' },
  { value: 'ios', label: 'iOS', icon: 'symbol-misc' },
  { value: 'android', label: 'Android', icon: 'symbol-misc' },
  { value: 'web', label: 'Web', icon: 'symbol-misc' },
]

export function DevicesView() {
  // Local device registry (no device backend is connected): rename/revoke
  // manage real local entries; sync badges reflect local state only.
  const devices = useStore($devices)
  const loading = useStore($deviceLoading)
  const search = useStore($deviceSearch)
  const filterOS = useStore($deviceFilterOS)

  const [renameDialog, setRenameDialog] = useState<DeviceInfo | null>(null)
  const [renameName, setRenameName] = useState('')
  const [revokeConfirm, setRevokeConfirm] = useState<DeviceInfo | null>(null)

  const filteredDevices = useMemo(() => {
    const q = search.trim().toLowerCase()

    return devices.filter(d => {
      if (filterOS && d.os !== filterOS) {return false}

      if (q && !d.name.toLowerCase().includes(q) && !d.os.toLowerCase().includes(q)) {return false}

      return true
    })
  }, [devices, search, filterOS])

  const handleRename = useCallback((device: DeviceInfo) => {
    setRenameDialog(device)
    setRenameName(device.name)
  }, [])

  const handleRenameConfirm = useCallback(() => {
    if (!renameDialog || !renameName.trim()) {return}
    renameDevice(renameDialog.id, renameName.trim())
    setRenameDialog(null)
    notify({ kind: 'success', title: 'Device Renamed', message: `Device renamed to "${renameName.trim()}"` })
  }, [renameDialog, renameName])

  const handleRevoke = useCallback((device: DeviceInfo) => {
    setRevokeConfirm(device)
  }, [])

  const handleRevokeConfirm = useCallback(() => {
    if (!revokeConfirm) {return}
    revokeDevice(revokeConfirm.id)
    setRevokeConfirm(null)
    notify({ kind: 'success', title: 'Device Revoked', message: `${revokeConfirm.name} has been revoked` })
  }, [revokeConfirm])

  const handleRevokeCancel = useCallback(() => {
    setRevokeConfirm(null)
  }, [])

  const syncStatusColor = (status: DeviceInfo['syncStatus']) => {
    switch (status) {
      case 'synced': return 'text-emerald-500'

      case 'syncing': return 'text-primary'

      case 'pending': return 'text-amber-500'

      case 'error': return 'text-destructive'

      case 'offline': return 'text-muted-foreground'
    }
  }

  if (loading) {
    return (
      <PageShell header={<PageHeader><PageTitle>Devices</PageTitle></PageHeader>}>
        <div className="grid min-h-52 place-items-center">
          <Codicon className="animate-spin text-muted-foreground" name="sync" size="1.5rem" />
        </div>
      </PageShell>
    )
  }

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div className="flex items-center justify-between">
            <div>
              <PageTitle>Devices</PageTitle>
              <PageDescription>Local device registry — rename and revoke manage this machine&apos;s entries</PageDescription>
            </div>
            <div className="flex items-center gap-2">
              <Codicon className="text-muted-foreground" name="device-desktop" size="1rem" />
              <span className="text-xs text-muted-foreground">{devices.length} device{devices.length !== 1 ? 's' : ''}</span>
            </div>
          </div>
        </PageHeader>
      }
    >
      <div className="flex items-center gap-3">
        <SearchField
          containerClassName="flex-1 max-w-xs"
          onChange={v => setDeviceSearch(v)}
          placeholder="Search devices..."
          value={search}
        />
        <Select onValueChange={v => setDeviceFilterOS(v === 'all' ? null : v as DeviceOS)} value={filterOS ?? 'all'}>
          <SelectTrigger className="h-8 w-32 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {OS_OPTIONS.map(opt => (
              <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filteredDevices.map(device => (
          <div
            className={cn(
              'group relative flex flex-col rounded-xl border bg-(--ui-chat-surface-background) p-4 transition-all hover:shadow-sm',
              device.isCurrent
                ? 'border-primary/40 ring-1 ring-primary/20'
                : 'border-(--ui-stroke-tertiary) hover:border-(--ui-stroke-secondary)'
            )}
            key={device.id}
          >
            {device.isCurrent && (
              <Badge className="absolute right-2.5 top-2.5 text-[0.55rem]" variant="default">Current</Badge>
            )}

            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Codicon name="device-desktop" size="1.1rem" />
                </span>
                <div>
                  <p className="text-sm font-medium">{device.name}</p>
                  <p className="mt-0.5 flex items-center gap-1.5 text-[0.6rem] text-muted-foreground">
                    <span className="capitalize">{device.os}{device.osVersion ? ` ${device.osVersion}` : ''}</span>
                    {device.appVersion ? (
                      <>
                        <span>·</span>
                        <span>v{device.appVersion}</span>
                      </>
                    ) : null}
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-3 flex items-center gap-3 text-[0.65rem] text-muted-foreground">
              <span className={cn('flex items-center gap-1', device.online ? 'text-emerald-500' : 'text-muted-foreground')}>
                <Codicon name="circle-filled" size="0.5rem" />
                {device.online ? 'Online' : 'Offline'}
              </span>
              <span className={cn('flex items-center gap-1', syncStatusColor(device.syncStatus))}>
                <Codicon name="sync" size="0.65rem" />
                <span className="capitalize">{device.syncStatus}</span>
              </span>
            </div>

            <p className="mt-1.5 text-[0.6rem] text-muted-foreground">
              Last active: {new Date(device.lastActive).toLocaleString()}
            </p>

            {!device.isCurrent && (
              <div className="mt-3 flex items-center gap-2 border-t border-(--ui-stroke-tertiary) pt-3">
                <Button className="flex-1 text-xs" onClick={() => handleRename(device)} size="sm" variant="outline">Rename</Button>
                <Button className="flex-1 text-xs text-muted-foreground hover:text-destructive" onClick={() => handleRevoke(device)} size="sm" variant="ghost">Revoke</Button>
              </div>
            )}
          </div>
        ))}
      </div>

      {filteredDevices.length === 0 && (
        <div className="mt-8 grid min-h-40 place-items-center">
          <div className="text-center">
            <Codicon className="text-muted-foreground/40" name="search" size="2rem" />
            <p className="mt-2 text-sm text-muted-foreground">No devices found</p>
            <p className="text-xs text-muted-foreground/60">Try a different search or filter</p>
          </div>
        </div>
      )}

      <Dialog onOpenChange={v => { if (!v) {setRenameDialog(null)} }} open={renameDialog !== null}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename Device</DialogTitle>
            <DialogDescription>Enter a new name for this device</DialogDescription>
          </DialogHeader>
          <Input onChange={e => setRenameName(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') {handleRenameConfirm()} }} placeholder="Device name" value={renameName} />
          <DialogFooter>
            <Button onClick={() => setRenameDialog(null)} size="sm" variant="outline">Cancel</Button>
            <Button disabled={!renameName.trim()} onClick={handleRenameConfirm} size="sm">Rename</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog onOpenChange={v => { if (!v) {setRevokeConfirm(null)} }} open={revokeConfirm !== null}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revoke Device</DialogTitle>
            <DialogDescription>
              Are you sure you want to revoke <strong>{revokeConfirm?.name}</strong>? This will remove its access to your AetherOS instance.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={handleRevokeCancel} size="sm" variant="outline">Cancel</Button>
            <Button onClick={handleRevokeConfirm} size="sm" variant="destructive">Revoke</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageShell>
  )
}
