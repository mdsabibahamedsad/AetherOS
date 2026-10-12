import { useStore } from '@nanostores/react'

import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { $setupWizard, updateProfile } from '@/store/setup-wizard'

import { ACCENT_OPTIONS, COUNTRY_OPTIONS, LANGUAGE_OPTIONS, THEME_OPTIONS, TIMEZONE_OPTIONS } from './options'

export function ProfileStep() {
  const p = useStore($setupWizard).profile

  return (
    <div className="mx-auto max-w-xl space-y-8 py-8">
      <div>
        <h2 className="text-2xl font-semibold">User Profile</h2>
        <p className="mt-1 text-sm text-muted-foreground">Tell us about yourself</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2 space-y-2">
          <Label htmlFor="displayName">Display Name</Label>
          <Input id="displayName" onChange={e => updateProfile({ displayName: e.target.value })} placeholder="Your name" value={p.displayName} />
        </div>

        <div className="col-span-2 space-y-2">
          <Label htmlFor="workspaceName">Workspace Name</Label>
          <Input id="workspaceName" onChange={e => updateProfile({ workspaceName: e.target.value })} placeholder="My Workspace" value={p.workspaceName} />
        </div>

        <div className="space-y-2">
          <Label>Language</Label>
          <Select onValueChange={v => updateProfile({ language: v })} value={p.language}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {LANGUAGE_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>Country</Label>
          <Select onValueChange={v => updateProfile({ country: v })} value={p.country}>
            <SelectTrigger><SelectValue placeholder="Select country" /></SelectTrigger>
            <SelectContent>
              {COUNTRY_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        <div className="col-span-2 space-y-2">
          <Label>Timezone</Label>
          <Select onValueChange={v => updateProfile({ timezone: v })} value={p.timezone}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {TIMEZONE_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>Theme</Label>
          <Select onValueChange={v => updateProfile({ theme: v })} value={p.theme}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {THEME_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>Accent Color</Label>
          <Select onValueChange={v => updateProfile({ accentColor: v })} value={p.accentColor}>
            <SelectTrigger><SelectValue placeholder="Default" /></SelectTrigger>
            <SelectContent>
              {ACCENT_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        <div className="col-span-2 flex items-center justify-between rounded-lg border p-4">
          <div>
            <Label className="text-base">Developer Mode</Label>
            <p className="text-sm text-muted-foreground">Enable developer features and diagnostics</p>
          </div>
          <Switch checked={p.developerMode} onCheckedChange={v => updateProfile({ developerMode: v })} />
        </div>

        <div className="col-span-2 flex items-center justify-between rounded-lg border p-4">
          <div>
            <Label className="text-base">Accessibility Mode</Label>
            <p className="text-sm text-muted-foreground">Enhanced screen reader and keyboard navigation</p>
          </div>
          <Switch checked={p.accessibility} onCheckedChange={v => updateProfile({ accessibility: v })} />
        </div>
      </div>
    </div>
  )
}
