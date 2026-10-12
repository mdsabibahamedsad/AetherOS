export const Button = ({ children, className, onClick, ...rest }: { children: React.ReactNode; className?: string; onClick?: () => void; [key: string]: any }) => {
  return (
    <button className={className} onClick={onClick} {...rest}>
      {children}
    </button>
  )
}