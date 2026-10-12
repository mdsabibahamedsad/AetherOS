import { useStore } from '@nanostores/react'
import { useState } from 'react'

import {
  $browserAutomation, addExecution, addNodeToWorkflow, connectNodes,
  createWorkflow, deleteWorkflow,
  removeNodeFromWorkflow, setActiveWorkflow, setBuilderOpen,
  setSelectedNode, setWorkflowSchedule,
  updateExecution, updateNodeConfig,
  type WorkflowNodeType,
} from '@/store/browser-automation'

const nodeTypes: { type: WorkflowNodeType; label: string; icon: string; category: string }[] = [
  { type: 'open_url', label: 'Open Website', icon: 'globe', category: 'navigation' },
  { type: 'search', label: 'Search', icon: 'search', category: 'navigation' },
  { type: 'click', label: 'Click', icon: 'mouse', category: 'interaction' },
  { type: 'type', label: 'Type', icon: 'keyboard', category: 'interaction' },
  { type: 'select', label: 'Select', icon: 'check', category: 'interaction' },
  { type: 'scroll', label: 'Scroll', icon: 'chevron-down', category: 'interaction' },
  { type: 'wait', label: 'Wait', icon: 'clock', category: 'flow' },
  { type: 'extract', label: 'Extract Data', icon: 'database', category: 'data' },
  { type: 'screenshot', label: 'Screenshot', icon: 'device-camera', category: 'data' },
  { type: 'navigate', label: 'Navigate', icon: 'arrow-left', category: 'navigation' },
  { type: 'condition', label: 'Condition', icon: 'git-branch', category: 'flow' },
  { type: 'loop', label: 'Loop', icon: 'repeat', category: 'flow' },
  { type: 'variable', label: 'Variable', icon: 'symbol-variable', category: 'data' },
  { type: 'download', label: 'Download', icon: 'cloud-download', category: 'data' },
  { type: 'webhook', label: 'Webhook', icon: 'link', category: 'integration' },
  { type: 'save_file', label: 'Save File', icon: 'save', category: 'data' },
  { type: 'send_notification', label: 'Send Notification', icon: 'bell', category: 'integration' },
  { type: 'filter', label: 'Filter Results', icon: 'filter', category: 'data' },
]

const nodeCategories = [...new Set(nodeTypes.map(n => n.category))]

export function BrowserAutomationBuilder() {
  const browserAuto = useStore($browserAutomation)
  const [showNodePalette, setShowNodePalette] = useState(false)
  const [draggedNode, setDraggedNode] = useState<WorkflowNodeType | null>(null)
  const [editingSchedule, setEditingSchedule] = useState(false)
  const [scheduleInput, setScheduleInput] = useState('')

  const activeWorkflow = browserAuto.workflows.find(w => w.id === browserAuto.activeWorkflowId)

  if (!browserAuto.builderOpen) {
    return (
      <div className="flex-1 overflow-auto">
        {browserAuto.workflows.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <span className="codicon codicon-run-all text-4xl text-(--ui-text-tertiary) mb-3" />
            <h2 className="text-lg font-semibold mb-1">Web Automation</h2>
            <p className="text-sm text-(--ui-text-tertiary) mb-4">Create automated browser workflows</p>
            <button className="px-4 py-2 bg-(--ui-accent) text-white text-sm rounded hover:opacity-90"
              onClick={() => setBuilderOpen(true)}>
              Create Your First Workflow
            </button>
          </div>
        ) : (
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium">Workflows</h2>
              <button className="px-3 py-1 text-xs bg-(--ui-accent) text-white rounded hover:opacity-90"
                onClick={() => {
                const id = createWorkflow(`Workflow ${browserAuto.workflows.length + 1}`)
                setActiveWorkflow(id)
              }}>
                + New
              </button>
            </div>
            <div className="space-y-2">
              {browserAuto.workflows.map(wf => (
                <div className={`flex items-center gap-2 px-3 py-2 text-xs border border-(--ui-border) rounded cursor-pointer hover:bg-(--ui-surface-hover) ${wf.id === browserAuto.activeWorkflowId ? 'border-(--ui-accent) bg-(--ui-accent)/5' : ''}`}
                  key={wf.id}
                  onClick={() => setActiveWorkflow(wf.id)}
                >
                  <span className="codicon codicon-run-all text-(--ui-accent)" />
                  <div className="flex-1 min-w-0">
                    <div className="truncate font-medium">{wf.name}</div>
                    <div className="text-(--ui-text-tertiary)">{wf.nodes.length} nodes {wf.schedule ? `· ${wf.schedule}` : ''}</div>
                  </div>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] ${wf.status === 'active' ? 'bg-green-100 text-green-700' : wf.status === 'draft' ? 'bg-gray-100 text-gray-600' : 'bg-yellow-100 text-yellow-700'}`}>
                    {wf.status}
                  </span>
                  <button className="p-0.5 hover:bg-(--ui-surface-hover) rounded opacity-0 hover:opacity-100"
                    onClick={e => { e.stopPropagation(); deleteWorkflow(wf.id) }}>
                    <span className="codicon codicon-trash text-[10px]" />
                  </button>
                </div>
              ))}
            </div>
            {browserAuto.executions.length > 0 && (
              <div className="mt-6">
                <h3 className="text-xs font-medium mb-2 text-(--ui-text-tertiary)">Recent Executions</h3>
                <div className="space-y-1">
                  {browserAuto.executions.slice(-5).reverse().map(ex => (
                    <div className="flex items-center gap-2 px-2 py-1 text-xs text-(--ui-text-tertiary)" key={ex.id}>
                      <span className={`codicon codicon-${ex.status === 'completed' ? 'check' : ex.status === 'failed' ? 'error' : 'clock'} ${ex.status === 'completed' ? 'text-green-600' : ex.status === 'failed' ? 'text-red-600' : ''}`} />
                      <span className="flex-1 truncate">{ex.workflowId}</span>
                      <span>{ex.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  if (!activeWorkflow) {
    return (
      <div className="flex-1 flex items-center justify-center text-sm text-(--ui-text-tertiary)">
        Select or create a workflow to start building.
      </div>
    )
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      <div className="w-56 border-r border-(--ui-border) bg-(--ui-surface-secondary) flex flex-col">
        <div className="px-3 py-2 border-b border-(--ui-border) text-xs font-medium">
          {activeWorkflow.name}
        </div>
        <div className="flex-1 overflow-auto p-2 space-y-1">
          <div className="text-[10px] font-medium text-(--ui-text-tertiary) uppercase tracking-wider mb-1">Nodes</div>
          {activeWorkflow.nodes.map((node, i) => (
            <div className={`flex items-center gap-1.5 px-2 py-1 text-xs rounded cursor-pointer
                ${browserAuto.selectedNodeId === node.id ? 'bg-(--ui-accent)/10 text-(--ui-accent)' : 'hover:bg-(--ui-surface-hover)'}`}
              key={node.id}
              onClick={() => setSelectedNode(node.id)}
            >
              <span className="codicon codicon-{getNodeIcon(node.type)} text-[10px]" />
              <span className="truncate flex-1">{node.label || node.type}</span>
              <span className="text-[10px] text-(--ui-text-tertiary)">{i + 1}</span>
            </div>
          ))}
        </div>
        <div className="p-2 border-t border-(--ui-border)">
          <button className="w-full px-2 py-1 text-xs bg-(--ui-accent) text-white rounded hover:opacity-90 flex items-center gap-1 justify-center"
            onClick={() => setShowNodePalette(!showNodePalette)}>
            <span className="codicon codicon-add" /> Add Node
          </button>
        </div>
      </div>

      <div className="flex-1 relative overflow-auto bg-gray-50">
        <div className="absolute inset-0 p-8">
          {activeWorkflow.nodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-sm text-(--ui-text-tertiary)">
              <span className="codicon codicon-run-all text-3xl mb-2" />
              <p>Add nodes to build your workflow</p>
              <button className="mt-2 px-3 py-1 text-xs bg-(--ui-accent) text-white rounded hover:opacity-90"
                onClick={() => setShowNodePalette(true)}>
                Add First Node
              </button>
            </div>
          ) : (
            <div className="relative">
              {activeWorkflow.nodes.map((node, i) => (
                <div className={`absolute p-3 border rounded shadow-sm bg-white cursor-pointer min-w-[160px]
                    ${browserAuto.selectedNodeId === node.id ? 'border-(--ui-accent) ring-1 ring-(--ui-accent)' : 'border-(--ui-border) hover:shadow'}`}
                  key={node.id}
                  onClick={() => setSelectedNode(node.id)}
                  style={{ left: node.position.x, top: node.position.y }}
                >
                  <div className="flex items-center gap-1 text-xs font-medium mb-1">
                    <span className={`codicon codicon-${getNodeIcon(node.type)} text-(--ui-accent)`} />
                    {node.label}
                  </div>
                  <div className="text-[10px] text-(--ui-text-tertiary)">{node.type.replace(/_/g, ' ')}</div>
                  {i < activeWorkflow.nodes.length - 1 && (
                    <div className="absolute -bottom-4 left-1/2 -translate-x-1/2">
                      <span className="codicon codicon-arrow-down text-(--ui-text-tertiary)" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="w-64 border-l border-(--ui-border) bg-(--ui-surface-secondary) flex flex-col">
        <div className="px-3 py-2 border-b border-(--ui-border) text-xs font-medium">Config</div>
        <div className="flex-1 overflow-auto p-3">
          {browserAuto.selectedNodeId ? (
            <NodeConfigPanel nodeId={browserAuto.selectedNodeId} workflowId={activeWorkflow.id} />
          ) : (
            <div className="text-xs text-(--ui-text-tertiary)">Select a node to configure</div>
          )}
        </div>
        <div className="p-3 border-t border-(--ui-border)">
          <button className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded hover:bg-(--ui-surface-hover) mb-2"
            onClick={() => {
            setEditingSchedule(!editingSchedule)

            if (!editingSchedule) {setScheduleInput(activeWorkflow.schedule)}
          }}>
            {activeWorkflow.schedule ? `Schedule: ${activeWorkflow.schedule}` : 'Set Schedule'}
          </button>
          {editingSchedule && (
            <div className="flex gap-1 mb-2">
              <input className="flex-1 px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => setScheduleInput(e.target.value)}
                placeholder="daily, weekly, cron..."
                type="text"
                value={scheduleInput}
              />
              <button className="px-2 py-1 text-xs bg-(--ui-accent) text-white rounded"
                onClick={() => { setWorkflowSchedule(activeWorkflow.id, scheduleInput); setEditingSchedule(false) }}>Set</button>
            </div>
          )}
          <button className="w-full px-2 py-1 text-xs bg-green-600 text-white rounded hover:opacity-90 flex items-center gap-1 justify-center"
            onClick={() => {
            addExecution({ id: `exec_${Date.now()}`, workflowId: activeWorkflow.id, status: 'running', currentNodeId: '', results: {}, errors: [], startedAt: new Date().toISOString(), completedAt: '' })
            setTimeout(() => {
              updateExecution(`exec_${Date.now()}`, { status: 'completed' })
            }, 2000)
          }}>
            <span className="codicon codicon-play" /> Run Workflow
          </button>
        </div>
      </div>

      {showNodePalette && (
        <div className="absolute inset-0 bg-black/20 z-50 flex items-center justify-center"
          onClick={() => setShowNodePalette(false)}>
          <div className="bg-(--ui-surface) rounded-lg shadow-xl border border-(--ui-border) w-96 max-h-[70vh] overflow-auto"
            onClick={e => e.stopPropagation()}>
            <div className="px-4 py-2 border-b border-(--ui-border) flex items-center justify-between">
              <span className="text-sm font-medium">Add Node</span>
              <button className="p-0.5 hover:bg-(--ui-surface-hover) rounded" onClick={() => setShowNodePalette(false)}>
                <span className="codicon codicon-close" />
              </button>
            </div>
            <div className="p-4">
              {nodeCategories.map(cat => (
                <div className="mb-4" key={cat}>
                  <h4 className="text-[10px] font-medium text-(--ui-text-tertiary) uppercase tracking-wider mb-2">{cat}</h4>
                  <div className="grid grid-cols-2 gap-1">
                    {nodeTypes.filter(n => n.category === cat).map(nt => (
                      <button className="flex items-center gap-1.5 px-2 py-1.5 text-xs rounded hover:bg-(--ui-surface-hover) border border-(--ui-border) text-left"
                        key={nt.type}
                        onClick={() => {
                          addNodeToWorkflow(activeWorkflow.id, nt.type, nt.label)
                          setShowNodePalette(false)
                        }}
                      >
                        <span className={`codicon codicon-${nt.icon} text-(--ui-accent)`} />
                        {nt.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function NodeConfigPanel({ workflowId, nodeId }: { workflowId: string; nodeId: string }) {
  const browserAuto = useStore($browserAutomation)
  const wf = browserAuto.workflows.find(w => w.id === workflowId)
  const node = wf?.nodes.find(n => n.id === nodeId)

  if (!node) {return <div className="text-xs text-(--ui-text-tertiary)">Node not found</div>}

  return (
    <div className="space-y-3">
      <div>
        <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">Label</label>
        <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => updateNodeConfig(workflowId, nodeId, { label: e.target.value })}
          type="text"
          value={node.label}
        />
      </div>

      {node.type === 'open_url' && (
        <div>
          <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">URL</label>
          <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => updateNodeConfig(workflowId, nodeId, { url: e.target.value })}
            placeholder="https://example.com"
            type="text"
          />
        </div>
      )}

      {node.type === 'search' && (
        <div>
          <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">Search Query</label>
          <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => updateNodeConfig(workflowId, nodeId, { query: e.target.value })}
            placeholder="Enter search query"
            type="text"
          />
        </div>
      )}

      {node.type === 'click' && (
        <div>
          <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">CSS Selector</label>
          <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => updateNodeConfig(workflowId, nodeId, { selector: e.target.value })}
            placeholder=".button, #submit, a[href='...']"
            type="text"
          />
        </div>
      )}

      {(node.type === 'type' || node.type === 'select') && (
        <>
          <div>
            <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">CSS Selector</label>
            <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => updateNodeConfig(workflowId, nodeId, { selector: e.target.value })}
              placeholder="input[name='...']"
              type="text"
            />
          </div>
          <div>
            <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">Text / Value</label>
            <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => updateNodeConfig(workflowId, nodeId, { text: e.target.value })}
              placeholder="Enter text"
              type="text"
            />
          </div>
        </>
      )}

      {node.type === 'wait' && (
        <div>
          <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">Seconds</label>
          <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" defaultValue="1" min="0.1" onChange={e => updateNodeConfig(workflowId, nodeId, { seconds: parseFloat(e.target.value) })}
            step="0.1"
            type="number"
          />
        </div>
      )}

      {node.type === 'extract' && (
        <div>
          <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">CSS Selector</label>
          <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => updateNodeConfig(workflowId, nodeId, { selector: e.target.value })}
            placeholder=".result, .price, table"
            type="text"
          />
        </div>
      )}

      {node.type === 'condition' && (
        <div>
          <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">Expression</label>
          <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => updateNodeConfig(workflowId, nodeId, { expression: e.target.value })}
            placeholder="{{count}} > 0"
            type="text"
          />
        </div>
      )}

      {node.type === 'loop' && (
        <div>
          <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">Max Iterations</label>
          <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" defaultValue="10" max="100" min="1"
            onChange={e => updateNodeConfig(workflowId, nodeId, { max_iterations: parseInt(e.target.value) })}
            type="number"
          />
        </div>
      )}

      {node.type === 'download' && (
        <>
          <div>
            <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">File URL</label>
            <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => updateNodeConfig(workflowId, nodeId, { url: e.target.value })}
              placeholder="https://example.com/file.pdf"
              type="text"
            />
          </div>
          <div>
            <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">Destination Path</label>
            <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => updateNodeConfig(workflowId, nodeId, { destination: e.target.value })}
              placeholder="~/Downloads/file.pdf"
              type="text"
            />
          </div>
        </>
      )}

      {node.type === 'save_file' && (
        <>
          <div>
            <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">Content</label>
            <textarea
              className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none h-20 resize-none"
              onChange={e => updateNodeConfig(workflowId, nodeId, { content: e.target.value })}
            />
          </div>
          <div>
            <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">File Path</label>
            <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => updateNodeConfig(workflowId, nodeId, { filepath: e.target.value })}
              placeholder="/path/to/output.txt"
              type="text"
            />
          </div>
        </>
      )}

      {node.type === 'webhook' && (
        <>
          <div>
            <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">Webhook URL</label>
            <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => updateNodeConfig(workflowId, nodeId, { webhook_url: e.target.value })}
              placeholder="https://hooks.example.com/..."
              type="text"
            />
          </div>
          <div>
            <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">Payload (JSON)</label>
            <textarea
              className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none h-20 font-mono resize-none"
              onChange={e => {
                try { updateNodeConfig(workflowId, nodeId, { payload: JSON.parse(e.target.value) }) }
                catch { }
              }}
              placeholder='{"key": "value"}'
            />
          </div>
        </>
      )}

      {node.type === 'variable' && (
        <>
          <div>
            <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">Name</label>
            <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => updateNodeConfig(workflowId, nodeId, { name: e.target.value })}
              placeholder="variable_name"
              type="text"
            />
          </div>
          <div>
            <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">Value</label>
            <input className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" onChange={e => updateNodeConfig(workflowId, nodeId, { value: e.target.value })}
              placeholder="Initial value"
              type="text"
            />
          </div>
        </>
      )}

      {node.type === 'send_notification' && (
        <div>
          <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">Message</label>
          <textarea
            className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none h-20 resize-none"
            onChange={e => updateNodeConfig(workflowId, nodeId, { message: e.target.value })}
            placeholder="Workflow completed!"
          />
        </div>
      )}

      <div className="pt-2 border-t border-(--ui-border)">
        <label className="text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5">Connections</label>
        <select className="w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none" multiple
          size={3}
        >
          {wf?.nodes.filter(n => n.id !== nodeId).map(n => (
            <option key={n.id} onClick={() => connectNodes(workflowId, nodeId, n.id)}
              selected={node.connections.includes(n.id)}
              value={n.id}
            >{n.label}</option>
          ))}
        </select>
      </div>

      <button className="w-full px-2 py-1 text-xs text-red-600 border border-red-200 rounded hover:bg-red-50"
        onClick={() => removeNodeFromWorkflow(workflowId, nodeId)}>
        Delete Node
      </button>
    </div>
  )
}

function getNodeIcon(type: string): string {
  const found = nodeTypes.find(n => n.type === type)

  return found?.icon ?? 'gear'
}
