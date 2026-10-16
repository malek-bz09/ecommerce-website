import { createContext, useContext } from 'react'

export const ProductsContext = createContext(null)

export function useProducts() {
  const catalog = useContext(ProductsContext)
  if (!catalog) throw new Error('useProducts must be used inside <ProductsProvider>')
  return catalog
}
