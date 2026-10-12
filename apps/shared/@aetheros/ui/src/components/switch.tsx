export const Switch = ({ checked, onCheckedChange, className, ...rest }: { checked: boolean; onCheckedChange: (checked: boolean) => void; className?: string; [key: string]: any }) => {
  return (
    <div className={className} onClick={(e) => { e.stopPropagation(); onCheckedChange(!checked); }} style={{ cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
      <span style={{ width: "2rem", height: "1rem", background: checked ? "#3b82f6" : "#d1d5db", borderRadius: "1rem", transition: "background 0.2s" }} />
      <span style={{ width: checked ? "1.5rem" : "0.5rem", height: "0.5rem", background: "white", borderRadius: "50%" }} />
    </div>
  )
}