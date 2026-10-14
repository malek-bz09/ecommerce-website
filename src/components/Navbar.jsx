import { Link } from 'react-router'
import './Navbar.css'
import { categories } from '../data/products'
import { useCart } from '../context/cart'

function Navbar() {
  const { count } = useCart()

  return (
    <header className="navbar">
      <Link to="/" className="navbar-logo">
        UNDERGROUND
      </Link>

      <nav className="navbar-links">
        <ul>
          {categories.map((category) => (
            <li key={category.id}>
              <Link to={`/category/${category.id}`}>{category.name}</Link>
            </li>
          ))}
        </ul>
      </nav>

      <div className="navbar-actions">
        <form className="navbar-search" role="search">
          <input type="search" name="q" placeholder="Search products" aria-label="Search products" />
          <button type="submit">Search</button>
        </form>
        <Link to="/cart">Cart ({count})</Link>
      </div>
    </header>
  )
}

export default Navbar
