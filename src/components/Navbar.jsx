import { Link, useNavigate, useSearchParams } from 'react-router'
import './Navbar.css'
import { categories } from '../data/products'
import { useCart } from '../context/cart'

function Navbar() {
  const { count } = useCart()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const query = searchParams.get('q') ?? ''

  const handleSearch = (event) => {
    event.preventDefault()
    const q = new FormData(event.currentTarget).get('q').trim()
    if (q) navigate(`/search?q=${encodeURIComponent(q)}`)
  }

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
        <form className="navbar-search" role="search" onSubmit={handleSearch}>
          {/* key: when the URL's query changes (e.g. Back button), show the new one */}
          <input
            key={query}
            type="search"
            name="q"
            defaultValue={query}
            placeholder="Search products"
            aria-label="Search products"
          />
          <button type="submit">Search</button>
        </form>
        <Link to="/cart">Cart ({count})</Link>
      </div>
    </header>
  )
}

export default Navbar
