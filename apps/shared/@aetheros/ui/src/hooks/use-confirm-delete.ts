export function useConfirmDelete() {
  const confirmDelete = (onConfirm: () => void) => {
    if (window.confirm("Are you sure you want to delete this item?")) {
      onConfirm()
    }
  }

  return { confirmDelete }
}