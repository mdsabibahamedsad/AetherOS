import { useStore } from '@nanostores/react'
import { AnimatePresence, motion } from 'motion/react'
import { memo } from 'react'

import { $jarvisToasts, dismissJarvisToast, type JarvisToast } from '@/store/jarvis-mode'

const TOAST_ICONS = {
  info: 'info',
  success: 'pass',
  warning: 'warning',
  error: 'error'
} as const

const TOAST_COLORS = {
  info: '#00d4ff',
  success: '#22c55e',
  warning: '#f59e0b',
  error: '#ef4444'
} as const

function ToastItem({ toast }: { toast: JarvisToast }) {
  const color = TOAST_COLORS[toast.type]

  return (
    <motion.div
      animate={{
        opacity: toast.dismissing ? 0 : 1,
        x: toast.dismissing ? 80 : 0,
        scale: toast.dismissing ? 0.95 : 1
      }}
      className="relative overflow-hidden rounded-xl bg-black/70 backdrop-blur-2xl border border-white/[0.08] shadow-2xl cursor-pointer group"
      exit={{ opacity: 0, x: 80, scale: 0.95 }}
      initial={{ opacity: 0, x: 80, scale: 0.95 }}
      layout
      onClick={() => dismissJarvisToast(toast.id)}
      transition={{ type: 'spring', damping: 25, stiffness: 300 }}
    >
      {/* Progress bar */}
      {toast.duration > 0 && !toast.dismissing && (
        <motion.div
          animate={{ width: '0%' }}
          className="absolute bottom-0 left-0 h-0.5"
          initial={{ width: '100%' }}
          style={{ backgroundColor: color }}
          transition={{ duration: toast.duration / 1000, ease: 'linear' }}
        />
      )}

      <div className="flex items-start gap-3 p-3">
        {/* Icon */}
        <div className="flex items-center justify-center size-8 rounded-lg shrink-0" style={{ backgroundColor: `${color}15` }}>
          <span className={`codicon codicon-${TOAST_ICONS[toast.type]} text-lg`} style={{ color }} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="text-[12px] font-medium text-white/80">{toast.title}</div>
          <div className="text-[10px] text-white/40 mt-0.5 line-clamp-2">{toast.message}</div>
        </div>

        {/* Close */}
        <button
          aria-label={`Dismiss notification: ${toast.title}`}
          className="opacity-0 group-hover:opacity-100 transition-opacity text-white/20 hover:text-white/50"
          onClick={e => { e.stopPropagation(); dismissJarvisToast(toast.id) }}
        >
          <span className="codicon codicon-close text-sm" />
        </button>
      </div>
    </motion.div>
  )
}

export function NotificationCenterComponent() {
  const toasts = useStore($jarvisToasts)

  if (toasts.length === 0) {return null}

  return (
    <div className="fixed top-16 right-4 z-[10001] flex flex-col gap-2 w-[360px] pointer-events-none">
      <AnimatePresence mode="popLayout">
        {toasts.slice(0, 5).map(toast => (
          <div className="pointer-events-auto" key={toast.id}>
            <ToastItem toast={toast} />
          </div>
        ))}
      </AnimatePresence>
    </div>
  )
}

export const NotificationCenter = memo(NotificationCenterComponent)
