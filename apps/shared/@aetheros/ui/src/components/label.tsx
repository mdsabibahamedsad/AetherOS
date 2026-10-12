export const Label = ({ children, className, ...rest }: { children: React.ReactNode; className?: string; [key: string]: any }) => {
  return <label className={className} {...rest}>{children}</label>
}