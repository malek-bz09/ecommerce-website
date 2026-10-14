import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'
import { useAuth } from '../../context/auth'
import './AdminLoginPage.css'

function AdminLoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState('')

  const destination = location.state?.from ?? '/admin'

  if (user) return <Navigate to={destination} replace />

  const handleSubmit = (event) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    if (login(form.get('username'), form.get('password'))) {
      navigate(destination, { replace: true })
    } else {
      setError('Incorrect username or password.')
    }
  }

  return (
    <section className="admin-login">
      <form className="admin-login-form" onSubmit={handleSubmit}>
        <h1>Admin sign in</h1>

        <label htmlFor="admin-username">Username</label>
        <input id="admin-username" name="username" autoComplete="username" required />

        <label htmlFor="admin-password">Password</label>
        <input
          id="admin-password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />

        {error && (
          <p className="admin-login-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit">Sign in</button>
      </form>
    </section>
  )
}

export default AdminLoginPage
