export const Spinner = ({ className, size }: { className?: string; size?: "sm" | "lg" }) => {
  return (
    <div className={className} style={{ width: size === "lg" ? "3rem" : "2rem", height: size === "lg" ? "3rem" : "2rem", border: "2px solid currentColor", borderTop: "2px solid transparent", borderRadius: "50%", animation: "spin 1s linear infinite" }}>
      &
    </div>
  )
}