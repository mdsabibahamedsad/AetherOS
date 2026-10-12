import { beforeEach, describe, expect, it } from 'vitest'

import {
  $browserAutomation,
  addExecution, addNodeToWorkflow, connectNodes, createWorkflow,
  deleteWorkflow, removeNodeFromWorkflow, setActiveWorkflow,
  setBuilderOpen, setSelectedNode,
  setWorkflowSchedule, updateExecution, updateNodeConfig,
  updateNodePosition, updateWorkflow,
} from './browser-automation'

describe('browser-automation store', () => {
  beforeEach(() => {
    $browserAutomation.set({
      workflows: [],
      activeWorkflowId: '',
      executions: [],
      builderOpen: false,
      selectedNodeId: '',
      editingNode: false,
    })
  })

  describe('createWorkflow', () => {
    it('creates a workflow and sets it active', () => {
      const id = createWorkflow('Test Workflow', 'A description')
      const state = $browserAutomation.get()
      expect(state.workflows).toHaveLength(1)
      expect(state.activeWorkflowId).toBe(id)
      expect(state.workflows[0].name).toBe('Test Workflow')
      expect(state.workflows[0].status).toBe('draft')
    })
  })

  describe('updateWorkflow', () => {
    it('updates workflow fields', () => {
      const id = createWorkflow('Old Name')
      updateWorkflow(id, { name: 'New Name', description: 'Updated desc' })
      const wf = $browserAutomation.get().workflows[0]
      expect(wf.name).toBe('New Name')
      expect(wf.description).toBe('Updated desc')
    })
  })

  describe('deleteWorkflow', () => {
    it('removes the workflow', () => {
      const id = createWorkflow('Test')
      deleteWorkflow(id)
      expect($browserAutomation.get().workflows).toHaveLength(0)
    })

    it('clears activeWorkflowId when deleting active', () => {
      const id = createWorkflow('Test')
      deleteWorkflow(id)
      expect($browserAutomation.get().activeWorkflowId).toBe('')
    })
  })

  describe('setActiveWorkflow', () => {
    it('sets the active workflow', () => {
      createWorkflow('WF1')
      const id2 = createWorkflow('WF2')
      setActiveWorkflow(id2)
      expect($browserAutomation.get().activeWorkflowId).toBe(id2)
    })
  })

  describe('setBuilderOpen', () => {
    it('toggles builder', () => {
      setBuilderOpen(true)
      expect($browserAutomation.get().builderOpen).toBe(true)
      setBuilderOpen(false)
      expect($browserAutomation.get().builderOpen).toBe(false)
    })
  })

  describe('setSelectedNode', () => {
    it('sets selected node', () => {
      setSelectedNode('node1')
      expect($browserAutomation.get().selectedNodeId).toBe('node1')
    })
  })

  describe('addNodeToWorkflow', () => {
    it('adds a node to the workflow', () => {
      const wfId = createWorkflow('Test')
      const nodeId = addNodeToWorkflow(wfId, 'open_url', 'Open Google')
      expect(nodeId).not.toBeNull()
      const wf = $browserAutomation.get().workflows[0]
      expect(wf.nodes).toHaveLength(1)
      expect(wf.nodes[0].type).toBe('open_url')
    })

    it('returns null for missing workflow', () => {
      const result = addNodeToWorkflow('nonexistent', 'click')
      expect(result).toBeNull()
    })
  })

  describe('removeNodeFromWorkflow', () => {
    it('removes a node', () => {
      const wfId = createWorkflow('Test')
      const nodeId = addNodeToWorkflow(wfId, 'open_url')!
      removeNodeFromWorkflow(wfId, nodeId)
      expect($browserAutomation.get().workflows[0].nodes).toHaveLength(0)
    })
  })

  describe('connectNodes', () => {
    it('connects two nodes', () => {
      const wfId = createWorkflow('Test')
      const n1 = addNodeToWorkflow(wfId, 'open_url')!
      const n2 = addNodeToWorkflow(wfId, 'click')!
      connectNodes(wfId, n1, n2)
      const node1 = $browserAutomation.get().workflows[0].nodes.find(n => n.id === n1)
      expect(node1?.connections).toContain(n2)
    })
  })

  describe('updateNodeConfig', () => {
    it('updates node config', () => {
      const wfId = createWorkflow('Test')
      const nodeId = addNodeToWorkflow(wfId, 'open_url')!
      updateNodeConfig(wfId, nodeId, { url: 'https://example.com' })
      const node = $browserAutomation.get().workflows[0].nodes[0]
      expect(node.config.url).toBe('https://example.com')
    })
  })

  describe('updateNodePosition', () => {
    it('updates node position', () => {
      const wfId = createWorkflow('Test')
      const nodeId = addNodeToWorkflow(wfId, 'open_url')!
      updateNodePosition(wfId, nodeId, { x: 200, y: 300 })
      const node = $browserAutomation.get().workflows[0].nodes[0]
      expect(node.position.x).toBe(200)
      expect(node.position.y).toBe(300)
    })
  })

  describe('setWorkflowSchedule', () => {
    it('sets schedule string', () => {
      const id = createWorkflow('Test')
      setWorkflowSchedule(id, 'daily')
      expect($browserAutomation.get().workflows[0].schedule).toBe('daily')
    })
  })

  describe('addExecution', () => {
    it('adds an execution record', () => {
      addExecution({ id: 'exec1', workflowId: 'wf1', status: 'running', currentNodeId: '', results: {}, errors: [], startedAt: new Date().toISOString(), completedAt: '' })
      expect($browserAutomation.get().executions).toHaveLength(1)
      expect($browserAutomation.get().executions[0].status).toBe('running')
    })
  })

  describe('updateExecution', () => {
    it('updates an execution', () => {
      const wfId = createWorkflow('Test')
      addExecution({ id: 'exec1', workflowId: wfId, status: 'running', currentNodeId: '', results: {}, errors: [], startedAt: new Date().toISOString(), completedAt: '' })
      updateExecution('exec1', { status: 'completed', results: { output: 'done' } })
      expect($browserAutomation.get().executions[0].status).toBe('completed')
    })
  })
})
