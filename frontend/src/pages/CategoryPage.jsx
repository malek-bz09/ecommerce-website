import { useParams } from 'react-router'
import ProductGrid from '../components/ProductGrid'
import NotFoundPage from './NotFoundPage'
import CatalogMessage from '../components/CatalogMessage'
import { useProducts } from '../context/products'
import { categories } from '../data/products'

function CategoryPage() {
  const { categoryId } = useParams()
  const category = categories.find((c) => c.id === categoryId)
  const { products, loading, error } = useProducts()

  if (!category) return <NotFoundPage />

  if (loading || error) return <CatalogMessage error={error} />

  return (
    <ProductGrid
      title={category.name}
      products={products.filter((p) => p.category === category.id)}
    />
  )
}

export default CategoryPage
