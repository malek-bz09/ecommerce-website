import { Link } from 'react-router'
import CatalogMessage from '../components/CatalogMessage'
import { useCart } from '../context/cart'
import { useProducts } from '../context/products'
import { formatPrice } from '../utils/formatPrice'
import './CartPage.css'

function CartPage() {
  const { lines, count, subtotal, updateQuantity, removeItem, clearCart } = useCart()
  const { loading, error } = useProducts()

  if (loading || error) return <CatalogMessage error={error} />

  if (lines.length === 0) {
    return (
      <section className="cart-empty">
        <h1>Your cart is empty</h1>
        <p>Looks like you haven't added anything yet.</p>
        <Link to="/" className="cart-button">
          Continue shopping
        </Link>
      </section>
    )

  }

  return (
    <section className="cart-page">
      <h1 className="cart-title">
        Cart <span>({count} {count === 1 ? 'item' : 'items'})</span>
      </h1>

      <div className="cart-layout">
        <ul className="cart-lines">
          {lines.map(({ id, quantity, product }) => (
            <li key={id} className="cart-line">
              <Link to={`/product/${product.slug}`} className="cart-line-image">
                <img src={product.images[0]} alt={product.name} />
              </Link>

              <div className="cart-line-info">
                <Link to={`/product/${product.slug}`} className="cart-line-name">
                  {product.name}
                </Link>
                <p className="cart-line-price">{formatPrice(product.price)}</p>

                <div className="cart-line-actions">
                  <div className="cart-quantity">
                    <button
                      type="button"
                      onClick={() => updateQuantity(id, quantity - 1)}
                      aria-label={`Decrease quantity of ${product.name}`}
                    >
                      −
                    </button>
                    <span aria-live="polite">{quantity}</span>
                    <button
                      type="button"
                      onClick={() => updateQuantity(id, quantity + 1)}
                      disabled={quantity >= product.stock}
                      aria-label={`Increase quantity of ${product.name}`}
                    >
                      +
                    </button>
                  </div>
                  <button type="button" className="cart-line-remove" onClick={() => removeItem(id)}>
                    Remove
                  </button>
                </div>
              </div>

              <p className="cart-line-total">{formatPrice(product.price * quantity)}</p>
            </li>
          ))}
        </ul>

        <aside className="cart-summary">
          <h2>Order summary</h2>
          <dl>
            <div>
              <dt>Subtotal</dt>
              <dd>{formatPrice(subtotal)}</dd>
            </div>
            <div>
              <dt>Shipping</dt>
              <dd>Calculated at checkout</dd>
            </div>
            <div className="cart-summary-total">
              <dt>Total</dt>
              <dd>{formatPrice(subtotal)}</dd>
            </div>
          </dl>
          <Link to="/checkout" className="cart-button">
            Checkout
          </Link>
          <button type="button" className="cart-clear" onClick={clearCart}>
            Clear cart
          </button>
          <Link to="/" className="cart-continue">
            Continue shopping
          </Link>
        </aside>
      </div>
    </section>
  )
}

export default CartPage
