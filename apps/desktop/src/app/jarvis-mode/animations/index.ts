import { type Variants } from 'motion/react'

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.4 } },
  exit: { opacity: 0, transition: { duration: 0.2 } },
}

export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.15 } },
}

export const fadeInDown: Variants = {
  hidden: { opacity: 0, y: -16 },
  visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } },
  exit: { opacity: 0, y: 8, transition: { duration: 0.15 } },
}

export const fadeInLeft: Variants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } },
  exit: { opacity: 0, x: -10, transition: { duration: 0.15 } },
}

export const fadeInRight: Variants = {
  hidden: { opacity: 0, x: 20 },
  visible: { opacity: 1, x: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } },
  exit: { opacity: 0, x: 10, transition: { duration: 0.15 } },
}

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1, transition: { type: 'spring', stiffness: 350, damping: 22 } },
  exit: { opacity: 0, scale: 0.9, transition: { duration: 0.15 } },
}

export const slideUp: Variants = {
  hidden: { y: '100%' },
  visible: { y: 0, transition: { type: 'spring', stiffness: 300, damping: 28 } },
  exit: { y: '100%', transition: { duration: 0.2 } },
}

export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05, delayChildren: 0.1 },
  },
  exit: { opacity: 0, transition: { duration: 0.15 } },
}

export const pulseGlow = {
  initial: { opacity: 0.4, scale: 0.95 },
  animate: {
    opacity: [0.4, 0.8, 0.4],
    scale: [0.95, 1.05, 0.95],
    transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' },
  },
}

export const orbStates = {
  idle: {
    scale: 1,
    ringSpeed: 0.3,
    particleSpeed: 0.2,
    glowOpacity: 0.3,
    color: '#00d4ff',
  },
  listening: {
    scale: 1.05,
    ringSpeed: 1,
    particleSpeed: 0.6,
    glowOpacity: 0.6,
    color: '#00d4ff',
  },
  thinking: {
    scale: 0.95,
    ringSpeed: 2,
    particleSpeed: 0.8,
    glowOpacity: 0.8,
    color: '#a78bfa',
  },
  planning: {
    scale: 0.98,
    ringSpeed: 1.5,
    particleSpeed: 0.5,
    glowOpacity: 0.7,
    color: '#0066ff',
  },
  executing: {
    scale: 1.02,
    ringSpeed: 2.5,
    particleSpeed: 1,
    glowOpacity: 0.9,
    color: '#22c55e',
  },
  speaking: {
    scale: 1.03,
    ringSpeed: 0.8,
    particleSpeed: 0.4,
    glowOpacity: 0.7,
    color: '#00d4ff',
  },
  searching: {
    scale: 0.97,
    ringSpeed: 1.8,
    particleSpeed: 0.9,
    glowOpacity: 0.6,
    color: '#f59e0b',
  },
  coding: {
    scale: 0.96,
    ringSpeed: 1.2,
    particleSpeed: 0.7,
    glowOpacity: 0.7,
    color: '#0066ff',
  },
  error: {
    scale: 1.05,
    ringSpeed: 0.5,
    particleSpeed: 0.3,
    glowOpacity: 0.9,
    color: '#ef4444',
  },
  success: {
    scale: 1.08,
    ringSpeed: 3,
    particleSpeed: 1.2,
    glowOpacity: 1,
    color: '#22c55e',
  },
} as const

export const timelineStages = [
  { key: 'understanding', label: 'Understanding', color: '#00d4ff' },
  { key: 'planning', label: 'Planning', color: '#0066ff' },
  { key: 'researching', label: 'Researching', color: '#9933ff' },
  { key: 'executing', label: 'Executing', color: '#22c55e' },
  { key: 'testing', label: 'Testing', color: '#f59e0b' },
  { key: 'completed', label: 'Completed', color: '#22c55e' },
] as const
