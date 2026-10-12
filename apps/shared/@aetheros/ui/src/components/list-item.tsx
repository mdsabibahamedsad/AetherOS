export const ListItem = ({ children, className, ...rest }: { children: React.ReactNode; className?: string; [key: string]: any }) => {
  return (
    <div className={className} style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.5rem", borderRadius: "4px" }}>
      {children}
    </div>
  )
}