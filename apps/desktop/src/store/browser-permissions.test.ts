import { beforeEach, describe, expect, it } from 'vitest'

import {
  $browserPermissions,
  addPermissionRequest, blockDomain, clearSessionGrants,
  denyPermission, grantPermission, setComputerUseEnabled, unblockDomain,
} from './browser-permissions'

describe('browser-permissions store', () => {
  beforeEach(() => {
    $browserPermissions.set({
      pendingRequests: [],
      grants: [],
      domainBlocklist: [],
      computerUseEnabled: false,
    })
  })

  describe('addPermissionRequest', () => {
    it('adds a pending request', () => {
      addPermissionRequest('read_page', 'https://example.com', 'Need to read content')
      expect($browserPermissions.get().pendingRequests).toHaveLength(1)
      expect($browserPermissions.get().pendingRequests[0].permissionType).toBe('read_page')
    })
  })

  describe('grantPermission', () => {
    it('grants a pending request', () => {
      addPermissionRequest('read_page', 'https://example.com', 'Testing')
      const reqId = $browserPermissions.get().pendingRequests[0].id
      grantPermission(reqId, 'session')
      expect($browserPermissions.get().pendingRequests).toHaveLength(0)
      expect($browserPermissions.get().grants).toHaveLength(1)
      expect($browserPermissions.get().grants[0].duration).toBe('session')
    })
  })

  describe('denyPermission', () => {
    it('marks request as denied', () => {
      addPermissionRequest('read_page', 'https://example.com', 'Testing')
      const reqId = $browserPermissions.get().pendingRequests[0].id
      denyPermission(reqId)
      const req = $browserPermissions.get().pendingRequests[0]
      expect(req.status).toBe('denied')
    })
  })

  describe('blockDomain', () => {
    it('adds domain to blocklist', () => {
      blockDomain('evil.com')
      expect($browserPermissions.get().domainBlocklist).toContain('evil.com')
    })

    it('does not duplicate domains', () => {
      blockDomain('evil.com')
      blockDomain('evil.com')
      expect($browserPermissions.get().domainBlocklist).toHaveLength(1)
    })
  })

  describe('unblockDomain', () => {
    it('removes domain from blocklist', () => {
      blockDomain('evil.com')
      unblockDomain('evil.com')
      expect($browserPermissions.get().domainBlocklist).toHaveLength(0)
    })
  })

  describe('setComputerUseEnabled', () => {
    it('toggles computer use', () => {
      setComputerUseEnabled(true)
      expect($browserPermissions.get().computerUseEnabled).toBe(true)
      setComputerUseEnabled(false)
      expect($browserPermissions.get().computerUseEnabled).toBe(false)
    })
  })

  describe('clearSessionGrants', () => {
    it('removes non-permanent grants', () => {
      addPermissionRequest('read_page', 'https://a.com', '')
      grantPermission($browserPermissions.get().pendingRequests[0].id, 'session')
      addPermissionRequest('navigate', 'https://b.com', '')
      grantPermission($browserPermissions.get().pendingRequests[0].id, 'permanent')
      clearSessionGrants()
      expect($browserPermissions.get().grants).toHaveLength(1)
      expect($browserPermissions.get().grants[0].duration).toBe('permanent')
    })
  })
})
