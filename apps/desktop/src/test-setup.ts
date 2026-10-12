const mockStorage: Record<string, string> = {}

const mockLocalStorage: Storage = {
  clear: () => {
    for (const k of Object.keys(mockStorage)) {
      delete mockStorage[k]
    }
  },
  getItem: (key: string) => mockStorage[key] ?? null,
  setItem: (key: string, value: string) => { mockStorage[key] = value },
  removeItem: (key: string) => { delete mockStorage[key] },
  get length() { return Object.keys(mockStorage).length },
  key: (index: number) => Object.keys(mockStorage)[index] ?? null,
}

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
  configurable: true,
  writable: true,
})
