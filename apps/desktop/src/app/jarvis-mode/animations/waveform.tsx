import { motion } from 'motion/react'
import { memo } from 'react'

function WaveformComponent({ active = true, barCount = 32, color = '#00d4ff' }) {
  return (
    <div className="flex items-center justify-center gap-[2px] h-full w-full">
      {Array.from({ length: barCount }, (_, i) => (
        <motion.div
          animate={
            active
              ? {
                  height: [
                    2 + Math.random() * 16,
                    2 + Math.random() * 32,
                    2 + Math.random() * 16,
                  ],
                  opacity: [0.3, 0.8, 0.3],
                }
              : { height: 2, opacity: 0.1 }
          }
          className="w-[2px] rounded-full"
          key={i}
          style={{ backgroundColor: color, minHeight: 2 }}
          transition={{
            duration: 0.8 + Math.random() * 0.6,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: i * 0.03,
          }}
        />
      ))}
    </div>
  )
}

export const Waveform = memo(WaveformComponent)
