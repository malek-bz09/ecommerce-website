import { Link } from 'react-router'
import { formatPrice } from '../utils/formatPrice'
import './ProductCard.css'

function ProductCard({ product }) {
  const { slug, name, price, compareAtPrice, images, stock } = product
  const soldOut = stock === 0
  const onSale = compareAtPrice !== null

  return (
    <Link to={`/product/${slug}`} className="product-card">
      <div className="product-card-media">
        <img className="product-card-image" src={images[0]} alt={name} loading="lazy" />
        {images[1] && (
          <img className="product-card-image-alt" src={images[1]} alt="" loading="lazy" />
        )}
        {soldOut ? (
          <span className="product-card-badge">Sold out</span>
        ) : (
          onSale && <span className="product-card-badge">Sale</span>
        )}
      </div>

      <div className="product-card-info">
        <h3 className="product-card-name">{name}</h3>
        <p className="product-card-price">
          {onSale && <s className="product-card-compare">{formatPrice(compareAtPrice)}</s>}
          {formatPrice(price)}
        </p>
      </div>
    </Link>
  )
}

export default ProductCard
