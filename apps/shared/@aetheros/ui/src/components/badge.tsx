export const Badge = ({ children, className }: { children: React.ReactNode; className?: string }) => {
  return (
    <span className={className} style={{ display: "inline-flex", alignItems: "center", gap: "0.2rem" }}>
      {children}
    </span>
  )
}