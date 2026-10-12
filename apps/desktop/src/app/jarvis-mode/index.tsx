import { memo } from 'react'

import { MissionControl } from './layout/mission-control'

function JarvisModeComponent() {
  return <MissionControl />
}

export const JarvisModeView = memo(JarvisModeComponent)
