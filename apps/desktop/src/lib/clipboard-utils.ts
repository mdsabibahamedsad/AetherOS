export async function readClipboardImage(): Promise<Blob | null> {
  try {
    const items = await navigator.clipboard.read()

    for (const item of items) {
      for (const type of item.types) {
        if (type.startsWith('image/')) {
          return await item.getType(type)
        }
      }
    }

    return null
  } catch {
    return null
  }
}

export async function readClipboardText(): Promise<string | null> {
  try {
    return await navigator.clipboard.readText()
  } catch {
    return null
  }
}

export async function writeClipboardText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)

    return true
  } catch {
    return false
  }
}

export async function readClipboardFiles(): Promise<File[]> {
  try {
    const items = await navigator.clipboard.read()
    const files: File[] = []

    for (const item of items) {
      for (const type of item.types) {
        if (!type.startsWith('image/') && !type.startsWith('text/')) {
          const blob = await item.getType(type)
          const ext = type.split('/').pop() || 'bin'
          files.push(new File([blob], `clipboard.${ext}`, { type }))
        }
      }
    }

    return files
  } catch {
    return []
  }
}

export function dataUrlToBlob(dataUrl: string): Blob | null {
  try {
    const parts = dataUrl.split(',')

    if (parts.length !== 2) {return null}
    const mimeMatch = parts[0].match(/:(.*?);/)

    if (!mimeMatch) {return null}
    const mime = mimeMatch[1]
    const binary = atob(parts[1])
    const bytes = new Uint8Array(binary.length)

    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i)
    }

    return new Blob([bytes], { type: mime })
  } catch {
    return null
  }
}

export function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}
