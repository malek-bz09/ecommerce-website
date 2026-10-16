import './ProductGrid.css'
import ProductCard from './ProductCard'

function ProductGrid({ title, products }) {
  return (
    <section className="product-grid-section">
      {title && <h2 className="product-grid-title">{title}</h2>}
      <div className="product-grid">
        {products.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </section>
  )
}

export default ProductGrid
