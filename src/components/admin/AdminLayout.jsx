import { useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router'
import { useAuth } from '../../context/auth'
import './AdminLayout.css'

const links = [
  { to: '/admin', label: 'Dashboard', end: true },
  { to: '/admin/orders', label: 'Orders' },
  { to: '/admin/products', label: 'Products' },

]

function AdminLayout() {
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className={`admin ${menuOpen ? 'admin--menu-open' : ''}`}>
      <aside className="admin-sidebar">
        <div className="admin-sidebar-header">
          <Link to="/admin" className="admin-logo">
            UNDERGROUND
          </Link>
          <span className="admin-badge">Admin</span>
        </div>

        <nav className="admin-nav" aria-label="Admin">
          <ul>
            {links.map((link) => (
              <li key={link.to}>
                <NavLink to={link.to} end={link.end} onClick={() => setMenuOpen(false)}>
                  {link.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="admin-sidebar-footer">
          <Link to="/">View store</Link>
          <button type="button" onClick={logout}>
            Log out
          </button>
        </div>
      </aside>

      {menuOpen && <div className="admin-overlay" onClick={() => setMenuOpen(false)} />}

      <div className="admin-main">
        <header className="admin-topbar">
          <button
            type="button"
            className="admin-menu-toggle"
            aria-label="Open menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(true)}
          >
            Menu
          </button>
          <span className="admin-user">{user.name}</span>
        </header>

        <div className="admin-content">
          <Outlet />
        </div>
      </div>
    </div>
  )
}

export default AdminLayout
