import { Link } from 'react-router'
import './NotFoundPage.css'

function NotFoundPage() {
  return (
    <section className="not-found">
      <h1>Page not found</h1>
      <p>The page you're looking for doesn't exist.</p>
      <Link to="/" className="not-found-link">
        Back to home
      </Link>
    </section>
  )
}

export default NotFoundPage
