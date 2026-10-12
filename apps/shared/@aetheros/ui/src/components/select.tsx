export const Select = ({ children, className, onValueChange, ...rest }: { children: React.ReactNode; className?: string; onValueChange?: (value: string) => void; [key: string]: any }) => {
  return (
    <select className={className} onChange={(e) => onValueChange?.(e.target.value)} {...rest}>
      {children}
    </select>
  )
}