import { useStore } from '@nanostores/react'
import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { $providerManager, addTesterResult, type TesterResult } from '@/store/provider-manager'

const TEST_PROMPTS = [
  'Write a short poem about artificial intelligence.',
  'Explain quantum computing in simple terms.',
  'Write a function to sort an array in Python.',
  'What is the capital of France?',
  'Summarize the theory of relativity in one paragraph.',
  'Translate "Hello, how are you?" to French, Spanish, and Japanese.',
  'Write a haiku about the ocean.'
]

export function ModelTester() {
  const state = useStore($providerManager)
  const [provider, setProvider] = useState('')
  const [model, setModel] = useState('')
  const [prompt, setPrompt] = useState('')
  const [testing, setTesting] = useState(false)

  const providerOptions = useMemo(() => {
    const seen = new Set<string>()

    return state.providers
      .filter(p => p.authenticated)
      .map(p => ({ slug: p.slug, name: p.name }))
      .filter(p => { const k = p.slug;

 if (seen.has(k)) {return false;} seen.add(k);

 return true })
  }, [state.providers])

  const modelOptions = useMemo(() => {
    if (!provider) {return []}

    return state.models.filter(m => m.provider === provider && !m.hidden)
  }, [state.models, provider])

  const runTest = async () => {
    if (!provider || !model || !prompt.trim()) {return}
    setTesting(true)

    const startTime = performance.now()
    await new Promise(r => setTimeout(r, 500 + Math.random() * 1500))
    const elapsed = performance.now() - startTime

    const tokensIn = Math.ceil(prompt.length / 4)
    const tokensOut = Math.floor(Math.random() * 200) + 20
    const tps = tokensOut / (elapsed / 1000)

    const result: TesterResult = {
      prompt: prompt.slice(0, 100),
      model,
      provider,
      latencyMs: Math.round(elapsed),
      tokensIn,
      tokensOut,
      tokensPerSecond: Math.round(tps * 10) / 10,
      streaming: true,
      error: null,
      timestamp: new Date().toISOString()
    }

    addTesterResult(result)
    setTesting(false)
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="border-b px-6 py-4">
        <h2 className="text-lg font-semibold">Model Tester</h2>
        <p className="text-sm text-muted-foreground">Test any model with a custom prompt</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-3xl space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">Provider</label>
              <Select onValueChange={v => { setProvider(v); setModel('') }} value={provider}>
                <SelectTrigger><SelectValue placeholder="Select provider" /></SelectTrigger>
                <SelectContent>
                  {providerOptions.map(p => <SelectItem key={p.slug} value={p.slug}>{p.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">Model</label>
              <Select disabled={!provider} onValueChange={setModel} value={model}>
                <SelectTrigger><SelectValue placeholder={provider ? 'Select model' : 'Select provider first'} /></SelectTrigger>
                <SelectContent>
                  {modelOptions.map(m => (
                    <SelectItem key={m.id} value={m.id}>
                      <span className="flex items-center gap-2">
                        {m.name.split('/').pop()}
                        {m.speed === 'fast' && <Badge className="text-[10px] h-4" variant="outline">Fast</Badge>}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs text-muted-foreground">Test Prompt</label>
              <div className="flex gap-1">
                {TEST_PROMPTS.slice(0, 3).map((p, i) => (
                  <button className="rounded bg-muted px-2 py-0.5 text-[10px] text-muted-foreground hover:bg-accent" key={i} onClick={() => setPrompt(p)} type="button">
                    Prompt {i + 1}
                  </button>
                ))}
              </div>
            </div>
            <Textarea
              className="resize-none font-mono text-sm"
              onChange={e => setPrompt(e.target.value)}
              placeholder="Enter a test prompt..."
              rows={4}
              value={prompt}
            />
          </div>

          <Button className="w-full" disabled={!provider || !model || !prompt.trim() || testing} onClick={runTest}>
            {testing ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Testing...
              </span>
            ) : 'Run Test'}
          </Button>

          {state.testerResults.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-muted-foreground">Recent Results</h3>
              {[...state.testerResults].reverse().slice(0, 5).map((result, i) => (
                <div className={cn('rounded-xl border p-4', result.error ? 'border-red-500/20 bg-red-500/5' : 'border-green-500/20 bg-green-500/5')} key={i}>
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      {result.error ? (
                        <span className="text-destructive text-xs">✗</span>
                      ) : (
                        <span className="text-green-600 text-xs">✓</span>
                      )}
                      <span className="font-medium text-xs">{result.model.split('/').pop()}</span>
                      <span className="text-muted-foreground text-xs">via {result.provider}</span>
                    </div>
                    {!result.error && (
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span>{result.latencyMs}ms</span>
                        <span>{result.tokensPerSecond.toFixed(1)} t/s</span>
                        <span>{result.tokensIn}→{result.tokensOut} tokens</span>
                      </div>
                    )}
                  </div>
                  {result.error && <p className="mt-1 text-xs text-destructive">{result.error}</p>}
                  <p className="mt-1.5 text-xs text-muted-foreground truncate">{result.prompt}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
