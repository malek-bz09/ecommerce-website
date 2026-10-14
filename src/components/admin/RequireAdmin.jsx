import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from '../../context/auth'

// Sends anyone without a session to the login page, remembering where they were going
function RequireAdmin() {
  const { user } = useAuth()
  const location = useLocation()

  if (!user) return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

export default RequireAdmin
