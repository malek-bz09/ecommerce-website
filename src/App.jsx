import { Routes, Route, Outlet } from 'react-router'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import ScrollToTop from './components/ScrollToTop'
import HomePage from './pages/HomePage'
import CategoryPage from './pages/CategoryPage'
import SearchPage from './pages/SearchPage'
import ProductPage from './pages/ProductPage'
import CartPage from './pages/CartPage'
import CheckoutPage from './pages/CheckoutPage'
import OrderConfirmationPage from './pages/OrderConfirmationPage'
import NotFoundPage from './pages/NotFoundPage'
import RequireAdmin from './components/admin/RequireAdmin'
import AdminLayout from './components/admin/AdminLayout'
import AdminLoginPage from './pages/admin/AdminLoginPage'
import AdminSectionPage from './pages/admin/AdminSectionPage'
import AdminDashboardPage from './pages/admin/AdminDashboardPage'
import AdminOrdersPage from './pages/admin/AdminOrdersPage'
import AdminOrderPage from './pages/admin/AdminOrderPage'
import AdminProductFormPage from './pages/admin/AdminProductFormPage'
import AdminProductsPage from './pages/admin/AdminProductsPage'
import AdminCustomersPage from './pages/admin/AdminCustomersPage'

// Storefront pages share the navbar and footer; admin pages have their own layout
function StoreLayout() {
  return (
    <>
      <Navbar />
      <main>
        <Outlet />
      </main>
      <Footer />
    </>
  )
}

function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route element={<StoreLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/category/:categoryId" element={<CategoryPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/product/:slug" element={<ProductPage />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/order-confirmed" element={<OrderConfirmationPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>

        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route element={<RequireAdmin />}>
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboardPage />} />
            <Route path="orders" element={<AdminOrdersPage />} />
            <Route path="orders/:orderId" element={<AdminOrderPage />} />
            <Route path="products" element={<AdminProductsPage />} />
            <Route path="products/new" element={<AdminProductFormPage />} />
            <Route path="products/:productId" element={<AdminProductFormPage />} />
            <Route path="customers" element={<AdminCustomersPage />} />
            <Route path="settings" element={<AdminSectionPage title="Settings" />} />
          </Route>
        </Route>
      </Routes>
    </>
  )
}

export default App
