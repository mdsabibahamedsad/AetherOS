/**
 * Real Jarvis voice settings. Every control reads/writes the persisted voice
 * store; provider rows show live availability (disabled + reason when the
 * environment or backend cannot support them). The wake-word toggle is an
 * explicit opt-in, default OFF — the mic is never hot unless listening.
 */

import { useStore } from '@nanostores/react'
import { memo, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Codicon } from '@/components/ui/codicon'
import { applyJarvisHotkey, DEFAULT_JARVIS_HOTKEY, getJarvisHotkey, setJarvisHotkeySetting } from '@/lib/jarvis/os/hotkey'
import {
  STT_PROVIDERS,
  type SttProviderId,
  TTS_PROVIDERS,
  type TtsProviderId
} from '@/lib/jarvis/voice/speech'
import { $micPermission, $voiceSettings, updateVoiceSettings, type VoiceResponseMode } from '@/store/jarvis-voice'

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <div className="text-[12px] text-white/30">{label}</div>
      {children}
    </div>
  )
}

function ProviderSelect<T extends string>({ value, options, disabled, onChange }: {
  value: T
  options: Array<{ id: T; label: string; available: boolean; reason: string | null }>
  disabled?: (id: T) => boolean
  onChange: (id: T) => void
}) {
  return (
    <div className="space-y-1">
      {options.map(opt => (
        <button
          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-left text-[12px] transition-all disabled:opacity-40 ${
            value === opt.id
              ? 'bg-[#00d4ff]/15 text-[#00d4ff] border border-[#00d4ff]/30'
              : 'bg-white/[0.04] text-white/50 border border-transparent hover:text-white/70'
          }`}
          disabled={!opt.available || disabled?.(opt.id)}
          key={opt.id}
          onClick={() => onChange(opt.id)}
          title={opt.available ? opt.label : (opt.reason ?? 'Unavailable')}
        >
          <span>{opt.label}</span>
          {!opt.available && <span className="text-[10px] text-white/25">unavailable</span>}
        </button>
      ))}
    </div>
  )
}

function VoiceSettingsPanel() {
  const settings = useStore($voiceSettings)
  const micPermission = useStore($micPermission)
  const [sttAvail, setSttAvail] = useState<Record<string, { ok: boolean; reason: string | null }>>({})
  const [ttsAvail, setTtsAvail] = useState<Record<string, { ok: boolean; reason: string | null }>>({})

  useEffect(() => {
    let cancelled = false

    async function probe() {
      const stt: Record<string, { ok: boolean; reason: string | null }> = {}

      for (const p of STT_PROVIDERS) {
        try { stt[p.id] = await p.checkAvailable() }
        catch { stt[p.id] = { ok: false, reason: 'Probe failed.' } }
      }

      const tts: Record<string, { ok: boolean; reason: string | null }> = {}

      for (const p of TTS_PROVIDERS) {
        try { tts[p.id] = await p.checkAvailable() }
        catch { tts[p.id] = { ok: false, reason: 'Probe failed.' } }
      }

      if (!cancelled) {
        setSttAvail(stt)
        setTtsAvail(tts)
      }
    }

    void probe()

    return () => { cancelled = true }
  }, [])

  const responseModes: Array<{ value: VoiceResponseMode; label: string }> = [
    { value: 'always', label: 'Always speak' },
    { value: 'voice-only', label: 'Voice commands only' },
    { value: 'errors-only', label: 'Errors only' },
    { value: 'off', label: 'Off' }
  ]

  return (
    <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-4">
      <div className="flex items-center gap-2">
        <Codicon className="size-4 text-[#00d4ff]" name="mic" />
        <div className="text-[13px] font-medium text-white/70">Voice</div>
        <div className="ml-auto text-[10px] text-white/25">mic permission: {micPermission}</div>
      </div>

      <Row label="Speech-to-text provider (microphone input)">
        <ProviderSelect<SttProviderId>
          onChange={id => updateVoiceSettings({ sttProvider: id })}
          options={STT_PROVIDERS.map(p => ({
            id: p.id,
            label: p.label,
            available: sttAvail[p.id]?.ok ?? true,
            reason: sttAvail[p.id]?.reason ?? null
          }))}
          value={settings.sttProvider}
        />
      </Row>

      <Row label="Text-to-speech provider (Jarvis voice)">
        <ProviderSelect<TtsProviderId>
          onChange={id => updateVoiceSettings({ ttsProvider: id })}
          options={TTS_PROVIDERS.map(p => ({
            id: p.id,
            label: p.label,
            available: ttsAvail[p.id]?.ok ?? true,
            reason: ttsAvail[p.id]?.reason ?? null
          }))}
          value={settings.ttsProvider}
        />
      </Row>

      <Row label="Voice responses">
        <div className="grid grid-cols-2 gap-1">
          {responseModes.map(m => (
            <button
              className={`px-2 py-1.5 rounded-lg text-[11px] font-medium transition-all ${
                settings.responseMode === m.value
                  ? 'bg-[#00d4ff]/20 text-[#00d4ff] border border-[#00d4ff]/30'
                  : 'bg-white/[0.04] text-white/30 border border-transparent hover:text-white/50'
              }`}
              key={m.value}
              onClick={() => updateVoiceSettings({ responseMode: m.value })}
            >
              {m.label}
            </button>
          ))}
        </div>
      </Row>

      <Row label={`Voice speed (${settings.rate.toFixed(1)}×)`}>
        <input
          className="w-full accent-[#00d4ff]"
          max={2}
          min={0.5}
          onChange={e => updateVoiceSettings({ rate: Number(e.target.value) })}
          step={0.1}
          type="range"
          value={settings.rate}
        />
      </Row>

      <Row label={`Voice volume (${Math.round(settings.volume * 100)}%)`}>
        <input
          className="w-full accent-[#00d4ff]"
          max={1}
          min={0}
          onChange={e => updateVoiceSettings({ volume: Number(e.target.value) })}
          step={0.05}
          type="range"
          value={settings.volume}
        />
      </Row>

      <Row label="Language">
        <input
          className="w-full px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] text-[12px] text-white/60 outline-none"
          onChange={e => updateVoiceSettings({ language: e.target.value || 'en-US' })}
          placeholder="en-US"
          value={settings.language}
        />
      </Row>

      <div className="flex items-center justify-between rounded-lg bg-white/[0.03] border border-white/[0.06] px-3 py-2">
        <div>
          <div className="text-[12px] text-white/60">Wake word ("hey Jarvis")</div>
          <div className="text-[10px] text-white/25">Opt-in. Mic is never hot unless listening.</div>
        </div>
        <button
          aria-checked={settings.wakeWordEnabled}
          className={`relative w-10 h-5 rounded-full transition-all ${settings.wakeWordEnabled ? 'bg-[#00d4ff]' : 'bg-white/[0.1]'}`}
          onClick={() => updateVoiceSettings({ wakeWordEnabled: !settings.wakeWordEnabled })}
          role="switch"
        >
          <span className={`absolute top-0.5 size-4 rounded-full bg-white transition-all ${settings.wakeWordEnabled ? 'left-[22px]' : 'left-0.5'}`} />
        </button>
      </div>

      <div className="flex items-center justify-between rounded-lg bg-white/[0.03] border border-white/[0.06] px-3 py-2">
        <div>
          <div className="text-[12px] text-white/60">Interruptible speech</div>
          <div className="text-[10px] text-white/25">Esc / Stop halts voice + task.</div>
        </div>
        <button
          aria-checked={settings.interruptible}
          className={`relative w-10 h-5 rounded-full transition-all ${settings.interruptible ? 'bg-[#00d4ff]' : 'bg-white/[0.1]'}`}
          onClick={() => updateVoiceSettings({ interruptible: !settings.interruptible })}
          role="switch"
        >
          <span className={`absolute top-0.5 size-4 rounded-full bg-white transition-all ${settings.interruptible ? 'left-[22px]' : 'left-0.5'}`} />
        </button>
      </div>
    </div>
  )
}

function SettingsViewComponent() {
  const navigate = useNavigate()
  const [hotkey, setHotkey] = useState(getJarvisHotkey())
  const [hotkeyStatus, setHotkeyStatus] = useState<string | null>(null)

  const saveHotkey = async (value: string) => {
    const trimmed = value.trim() || DEFAULT_JARVIS_HOTKEY
    setJarvisHotkeySetting(trimmed)
    setHotkey(trimmed)
    const res = await applyJarvisHotkey(trimmed)
    setHotkeyStatus(res.ok ? `Registered ${trimmed}` : (res.error ?? 'Registration failed.'))
  }

  return (
    <div className="h-full flex flex-col p-6">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-white/90">Jarvis Mode Settings</h2>
        <p className="text-[12px] text-white/30 mt-0.5">Voice, permissions and session controls</p>
      </div>

      <div className="space-y-3 flex-1 overflow-y-auto scrollbar-dt">
        <VoiceSettingsPanel />

        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          <div className="text-[13px] font-medium text-white/70 mb-1">Global hotkey</div>
          <div className="text-[11px] text-white/30 mb-2">Focus Jarvis from anywhere. Example: CommandOrControl+Space.</div>
          <div className="flex items-center gap-2">
            <input
              className="flex-1 px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] text-[12px] text-white/60 outline-none font-mono"
              onChange={e => setHotkey(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') {void saveHotkey(hotkey)}
              }}
              value={hotkey}
            />
            <button
              className="rounded-lg bg-[#00d4ff]/15 px-3 py-1.5 text-[12px] text-[#00d4ff] border border-[#00d4ff]/30 hover:bg-[#00d4ff]/25"
              onClick={() => void saveHotkey(hotkey)}
            >
              Apply
            </button>
          </div>
          {hotkeyStatus && <div className="mt-1.5 text-[11px] text-white/40">{hotkeyStatus}</div>}
        </div>

        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          <div className="text-[13px] font-medium text-white/70 mb-1">Permissions</div>
          <div className="text-[11px] text-white/30 mb-3">
            Destructive and outbound-message actions always ask first. Gateway approvals appear in Security Center.
          </div>
          <button
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-white/[0.04] text-left transition-colors"
            onClick={() => navigate('/security')}
          >
            <span className="text-[12px] text-white/50">Open Security Center approvals</span>
            <Codicon className="size-3.5 text-white/20" name="shield" />
          </button>
        </div>

        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          <div className="text-[13px] font-medium text-white/70 mb-3">Session</div>
          <div className="space-y-2">
            <button
              className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-white/[0.04] text-left transition-colors"
              onClick={() => navigate('/')}
            >
              <span className="text-[12px] text-red-400/60">Exit Jarvis Mode</span>
              <Codicon className="size-3.5 text-red-400/60" name="sign-out" />
            </button>
          </div>
        </div>
      </div>

      <div className="mt-4 text-[10px] text-white/15 text-center">
        AetherOS Jarvis Mode — voice and agent execution share one pipeline
      </div>
    </div>
  )
}

export const SettingsView = memo(SettingsViewComponent)
