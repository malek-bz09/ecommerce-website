// Product categories. Products themselves now live in the backend database
// (manage them in Admin → Products) and are loaded by ProductsProvider.
// Keep in sync with CATEGORIES in backend/app/database.py
export const categories = [
  { id: 'tops', name: 'Tops' },
  { id: 'bottoms', name: 'Bottoms' },
  { id: 'hats', name: 'Hats' },
]

export const getCategoryName = (id) => categories.find((c) => c.id === id)?.name ?? id
