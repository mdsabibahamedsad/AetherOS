export const Card = ({ children, className }: { children: React.ReactNode; className?: string }) => {
  return (
    <div className={className} style={{ background: "white", borderRadius: "8px", padding: "1.5rem", boxShadow: "0 2px 4px rgba(0,0,0,0.1)" }}>
      {children}
    </div>
  )
}

export const CardHeader = ({ children, className }: { children: React.ReactNode; className?: string }) => {
  return <div className={className} style={{ fontWeight: "bold", marginBottom: "0.5rem" }}>{children}</div>
}

export const CardTitle = ({ children, className }: { children: React.ReactNode; className?: string }) => {
  return <div className={className}>{children}</div>
}