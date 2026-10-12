import { useStore } from '@nanostores/react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  $ocr,
  setAutoDetectLanguage,
  setConfidenceThreshold,
  setDeskewImage,
  setEnhanceImage,
  setOCRLanguage,
  setOCRProvider,
  setPsmMode
} from '@/store/ocr-store'
import type { OCRProviderType } from '@/store/ocr-store'

const PROVIDER_NOTES: Record<OCRProviderType, string> = {
  tesseract: 'Best for offline OCR with common languages. No API key needed.',
  windows_ocr: 'Native Windows OCR engine. Works offline, good for system integration.',
  azure: 'Microsoft Azure Computer Vision. Best for printed text and handwritten notes.',
  google_cloud: 'Google Cloud Vision API. Excellent for diverse document types and layouts.',
  aws_textract: 'Amazon Textract. Optimized for forms, tables, and structured documents.',
  vision_llm: 'Uses a vision-capable LLM for OCR. Best for complex layouts and contextual extraction.'
}

const PSM_OPTIONS = [
  { value: 0, label: 'OSD Only' },
  { value: 1, label: 'Auto Page Segmentation' },
  { value: 3, label: 'Fully Automatic (Default)' },
  { value: 4, label: 'Single Column of Text' },
  { value: 6, label: 'Uniform Block of Text' },
  { value: 7, label: 'Single Line' },
  { value: 8, label: 'Single Word' },
  { value: 10, label: 'Single Character' },
  { value: 12, label: 'Sparse Text' },
  { value: 13, label: 'Raw Line' }
]

const AVAILABLE_LANGUAGES = [
  'eng', 'fra', 'deu', 'spa', 'ita', 'por', 'nld', 'rus',
  'jpn', 'chi_sim', 'chi_tra', 'kor', 'ara', 'hin', 'tha',
  'vie', 'tur', 'pol', 'ukr', 'ell', 'heb', 'swe', 'nor',
  'dan', 'fin', 'ces', 'hun', 'ron', 'cat', 'ind', 'msa'
]

const LANGUAGE_LABELS: Record<string, string> = {
  eng: 'English', fra: 'French', deu: 'German', spa: 'Spanish',
  ita: 'Italian', por: 'Portuguese', nld: 'Dutch', rus: 'Russian',
  jpn: 'Japanese', chi_sim: 'Chinese (Simplified)', chi_tra: 'Chinese (Traditional)',
  kor: 'Korean', ara: 'Arabic', hin: 'Hindi', tha: 'Thai',
  vie: 'Vietnamese', tur: 'Turkish', pol: 'Polish', ukr: 'Ukrainian',
  ell: 'Greek', heb: 'Hebrew', swe: 'Swedish', nor: 'Norwegian',
  dan: 'Danish', fin: 'Finnish', ces: 'Czech', hun: 'Hungarian',
  ron: 'Romanian', cat: 'Catalan', ind: 'Indonesian', msa: 'Malay'
}

function RangeSlider({ value, min, max, step, onChange, label }: {
  value: number
  min: number
  max: number
  step: number
  onChange: (v: number) => void
  label: string
}) {
  return (
    <div className="flex items-center gap-3">
      <input
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-(--ui-bg-tertiary) accent-[#00D4FF]"
        max={max}
        min={min}
        onChange={e => onChange(Number(e.target.value))}
        step={step}
        type="range"
        value={value}
      />
      <span className="min-w-12 text-right text-xs text-(--ui-text-secondary)">{value}{label}</span>
    </div>
  )
}

export function OCRSettings() {
  const state = useStore($ocr)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold">OCR Settings</h2>
        <p className="text-sm text-(--ui-text-tertiary)">
          Configure optical character recognition providers and options
        </p>
      </div>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Provider</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">OCR Provider</div>
            <div className="text-xs text-(--ui-text-tertiary)">Engine used for text recognition</div>
          </div>
          <Select onValueChange={v => setOCRProvider(v as OCRProviderType)} value={state.provider}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="tesseract">Tesseract</SelectItem>
              <SelectItem value="windows_ocr">Windows OCR</SelectItem>
              <SelectItem value="azure">Azure Vision</SelectItem>
              <SelectItem value="google_cloud">Google Cloud Vision</SelectItem>
              <SelectItem value="aws_textract">AWS Textract</SelectItem>
              <SelectItem value="vision_llm">Vision LLM</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="rounded-lg bg-(--ui-bg-quaternary) px-3 py-2 text-xs text-(--ui-text-tertiary)">
          {PROVIDER_NOTES[state.provider]}
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Language</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Language</div>
            <div className="text-xs text-(--ui-text-tertiary)">Primary OCR language</div>
          </div>
          <Select onValueChange={setOCRLanguage} value={state.language}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {AVAILABLE_LANGUAGES.map(lang => (
                <SelectItem key={lang} value={lang}>
                  {LANGUAGE_LABELS[lang] ?? lang}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Auto-Detect Language</div>
            <div className="text-xs text-(--ui-text-tertiary)">Automatically detect text language</div>
          </div>
          <Switch checked={state.autoDetectLanguage} onCheckedChange={setAutoDetectLanguage} />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Image Processing</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Image Enhancement</div>
            <div className="text-xs text-(--ui-text-tertiary)">Pre-process images for better OCR results</div>
          </div>
          <Switch checked={state.enhanceImage} onCheckedChange={setEnhanceImage} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Deskew / Straighten</div>
            <div className="text-xs text-(--ui-text-tertiary)">Auto-correct skewed image angles</div>
          </div>
          <Switch checked={state.deskewImage} onCheckedChange={setDeskewImage} />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Advanced</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">PSM Mode</div>
            <div className="text-xs text-(--ui-text-tertiary)">Page segmentation mode for Tesseract</div>
          </div>
          <Select
            onValueChange={v => setPsmMode(Number(v))}
            value={String(state.psmMode)}
          >
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PSM_OPTIONS.map(opt => (
                <SelectItem key={opt.value} value={String(opt.value)}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Confidence Threshold</div>
            <div className="text-xs text-(--ui-text-tertiary)">Minimum confidence score to accept results</div>
          </div>
          <div className="w-48">
            <RangeSlider
              label=""
              max={100}
              min={0}
              onChange={setConfidenceThreshold}
              step={5}
              value={state.confidenceThreshold}
            />
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Test OCR</h3>

        <div className="flex items-center gap-2">
          <Button disabled={state.status === 'processing'} size="sm" variant="outline">
            {state.status === 'processing' ? 'Processing...' : 'Upload Image & Test OCR'}
          </Button>
          {state.lastResult && (
            <Badge variant={state.status === 'success' ? 'default' : 'destructive'}>
              {state.status === 'success' ? `Confidence: ${(state.lastResult.confidence * 100).toFixed(0)}%` : 'Error'}
            </Badge>
          )}
        </div>

        {state.lastResult && state.status === 'success' && (
          <div className="rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) p-3">
            <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap text-xs text-(--ui-text-secondary)">
              {state.lastResult.text}
            </pre>
            <div className="mt-2 text-xs text-(--ui-text-tertiary)">
              Processed in {(state.lastResult.processingTimeMs / 1000).toFixed(2)}s via {state.lastResult.provider}
            </div>
          </div>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Supported Languages</h3>

        <div className="flex flex-wrap gap-1">
          {AVAILABLE_LANGUAGES.map(lang => (
            <span
              className="rounded-full bg-(--ui-background-tertiary) px-2 py-0.5 text-xs text-(--ui-text-secondary)"
              key={lang}
            >
              {LANGUAGE_LABELS[lang] ?? lang}
            </span>
          ))}
        </div>
      </section>
    </div>
  )
}
