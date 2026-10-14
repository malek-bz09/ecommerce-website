import Hero from '../components/Hero'
import ProductGrid from '../components/ProductGrid'
import { products } from '../data/products'

function HomePage() {
  return (
    <>
      <Hero />
      <ProductGrid title="All products" products={products} />
    </>
  )
}

export default HomePage
