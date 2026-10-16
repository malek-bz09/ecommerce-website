import { useState } from 'react'
import { Link, useParams } from 'react-router'
import ProductGrid from '../components/ProductGrid'
import NotFoundPage from './NotFoundPage'
import CatalogMessage from '../components/CatalogMessage'
import { categories } from '../data/products'
import { useProducts } from '../context/products'
import { useCart } from '../context/cart'
import { formatPrice } from '../utils/formatPrice'
import './ProductPage.css'

function ProductPage() {
  const { slug } = useParams()
  const { products, loading, error } = useProducts()
  const product = products.find((p) => p.slug === slug)

  if (!product && (loading || error)) return <CatalogMessage error={error} />
  if (!product) return <NotFoundPage />

  const related = products.filter((p) => p.category === product.category && p.id !== product.id)

  // key resets the selected image and quantity when moving to another product
  return <ProductDetails key={product.id} product={product} related={related} />
}

function ProductDetails({ product, related }) {
  const { name, description, price, compareAtPrice, images, rating, reviewCount, stock } = product
  const [selectedImage, setSelectedImage] = useState(0)
  const [quantity, setQuantity] = useState(1)
  const [added, setAdded] = useState(false)
  const { addItem } = useCart()

  const category = categories.find((c) => c.id === product.category)
  const soldOut = stock === 0
  const onSale = compareAtPrice !== null

  const handleAddToCart = () => {
    addItem(product, quantity)
    setAdded(true)
    setTimeout(() => setAdded(false), 2000)
  }

  return (
    <>
      <section className="product-page">
        <nav className="product-breadcrumb" aria-label="Breadcrumb">
          <Link to="/">Home</Link>
          <span>/</span>
          <Link to={`/category/${product.category}`}>{category?.name}</Link>
          <span>/</span>
          <span aria-current="page">{name}</span>
        </nav>

        <div className="product-layout">
          <div className="product-gallery">
            <img className="product-gallery-main" src={images[selectedImage]} alt={name} />
            {images.length > 1 && (
              <div className="product-gallery-thumbs">
                {images.map((src, index) => (
                  <button
                    key={src}
                    type="button"
                    className={`product-gallery-thumb${index === selectedImage ? ' is-active' : ''}`}
                    onClick={() => setSelectedImage(index)}
                    aria-label={`Show image ${index + 1}`}
                  >
                    <img src={src} alt="" />
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="product-info">
            <p className="product-category">{category?.name}</p>
            <h1 className="product-name">{name}</h1>

            <p className="product-price">
              {onSale && <s className="product-compare">{formatPrice(compareAtPrice)}</s>}
              {formatPrice(price)}
            </p>

            {reviewCount > 0 && (
              <p className="product-rating">
                ★ {rating.toFixed(1)} <span>({reviewCount} reviews)</span>
              </p>
            )}

            <p className="product-description">{description}</p>

            <p className="product-stock">
              {soldOut ? 'Sold out' : stock <= 10 ? `Only ${stock} left` : 'In stock'}
            </p>

            <div className="product-actions">
              <div className="product-quantity">
                <button
                  type="button"
                  onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                  disabled={soldOut || quantity <= 1}
                  aria-label="Decrease quantity"
                >
                  −
                </button>
                <span aria-live="polite">{quantity}</span>
                <button
                  type="button"
                  onClick={() => setQuantity((q) => Math.min(stock, q + 1))}
                  disabled={soldOut || quantity >= stock}
                  aria-label="Increase quantity"
                >
                  +
                </button>
              </div>

              <button
                type="button"
                className="product-add"
                onClick={handleAddToCart}
                disabled={soldOut}
              >
                {soldOut ? 'Sold out' : added ? 'Added to cart' : 'Add to cart'}
              </button>
            </div>

            <ul className="product-perks">
              <li>Free shipping on orders over DZD 10000</li>
              <li>Free returns within 30 days</li>
            </ul>
          </div>
        </div>
      </section>

      {related.length > 0 && <ProductGrid title="You may also like" products={related} />}
    </>
  )
}

export default ProductPage
