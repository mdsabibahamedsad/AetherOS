export function useToast() {
  const [toasts, setToasts] = React.useState<Array<{ id: string; title: string; description: string; variant?: string }>>([])

  const addToast = (title: string, description: string, variant?: string) => {
    const id = Math.random().toString(36).substr(2, 9)
    setToasts(prev => [...prev, { id, title, description, variant }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000)
  }

  return { toasts, addToast }
}