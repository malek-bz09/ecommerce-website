import { Link } from 'react-router'
import './Footer.css'
import { categories } from '../data/products'

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-columns">
        <div className="footer-about">
          <Link to="/" className="footer-logo">
            UNDERGROUND
          </Link>
          <p>Quality products, delivered to your door.</p>
        </div>

        <div className="footer-column">
          <h3>Shop</h3>
          <ul>
            {categories.map((category) => (
              <li key={category.id}>
                <Link to={`/category/${category.id}`}>{category.name}</Link>
              </li>
            ))}
          </ul>
        </div>

        <div className="footer-column">
          <h3>Help</h3>
          <ul>
            <li>
              <Link to="/faq">FAQ</Link>
            </li>
            <li>
              <Link to="/shipping">Shipping</Link>
            </li>
            <li>
              <Link to="/returns">Returns</Link>
            </li>
          </ul>
        </div>

        <div className="footer-column">
          <h3>Contact Us</h3>
          <p>Have questions? We'd love to hear from you.</p>
          <div className="footer-contact">
            <p>
            <strong>Email:</strong>{" "}
            <a href="mailto:contact@example.com">contact@example.com</a>
            </p>
            <p>
            <strong>Phone:</strong>{" "}
            <a href="tel:+213000000000">+213 XX XX XX XX</a>
            </p>
            <p>
            <strong>Address:</strong> Algiers, Algeria
            </p>
          </div>
        </div>
      </div>

      <p className="footer-copyright">
        © {new Date().getFullYear()} UNDERGROUND. All rights reserved.
      </p>
    </footer>
  )
}

export default Footer
