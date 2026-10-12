export const Toast = ({ title, description, variant }: { title: string; description: string; variant?: "default" | "destructive" }) => {
  return (
    <div style={{
      position: "fixed", bottom: "1rem", right: "1rem", background: "white", padding: "1rem", borderRadius: "8px",
      boxShadow: "0 4px 12px rgba(0,0,0,0.15)", zIndex: 1000
    }}>
      <strong>{title}</strong>: {description}
    </div>
  )
}