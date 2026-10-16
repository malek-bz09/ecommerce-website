import Hero from '../components/Hero'
import ProductGrid from '../components/ProductGrid'
import CatalogMessage from '../components/CatalogMessage'
import { useProducts } from '../context/products'

function HomePage() {
  const { products, loading, error } = useProducts()

  return (
    <>
      <Hero />
      {loading || error ? (
        <CatalogMessage error={error} />
      ) : (
        <ProductGrid title="All products" products={products} />
      )}
    </>
  )
}

export default HomePage
