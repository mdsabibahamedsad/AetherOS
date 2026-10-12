export const Input = ({ type, value, onChange, className, ...rest }: { type?: string; value?: string; onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void; className?: string; [key: string]: any }) => {
  return (
    <input type={type} value={value} onChange={onChange} className={className} {...rest} />
  )
}