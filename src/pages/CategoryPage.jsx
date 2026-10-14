import { useParams } from 'react-router'
import ProductGrid from '../components/ProductGrid'
import NotFoundPage from './NotFoundPage'
import { categories, getProductsByCategory } from '../data/products'

function CategoryPage() {
  const { categoryId } = useParams()
  const category = categories.find((c) => c.id === categoryId)

  if (!category) return <NotFoundPage />

  return <ProductGrid title={category.name} products={getProductsByCategory(category.id)} />
}

export default CategoryPage
