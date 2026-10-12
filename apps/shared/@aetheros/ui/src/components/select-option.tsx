export const SelectOption = ({ value, children, className }: { value: string; children: React.ReactNode; className?: string }) => {
  return (
    <option value={value} className={className}>
      {children}
    </option>
  )
}