export const Dialog = ({ title, children, onClose, variant }: { title: string; children: React.ReactNode; onClose: () => void; variant?: "default" | "destructive" }) => {
  return (
    <div style={{
      position: "fixed", top: "50%", left: "50%", transform: "translate(-50%, -50%)", background: "white", padding: "2rem", borderRadius: "8px",
      boxShadow: "0 4px 20px rgba(0,0,0,0.2)", zIndex: 1000, width: "90%", maxWidth: "500px"
    }}>
      <div style={{ fontWeight: "bold", marginBottom: "1rem" }}>{title}</div>
      <div>{children}</div>
      <button onClick={onClose} style={{ marginTop: "1rem", padding: "0.5rem 1rem" }}>Close</button>
    </div>
  )
}