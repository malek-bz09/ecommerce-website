import { Link } from 'react-router'
import './Hero.css'

function Hero() {
  return (
    <section className="hero">
      <img
        className="hero-image"
        src="/hero-street-crowd.jpg"
        alt="A crowd in casual streetwear on a city street"
      />
      <Link to="/shop" className="hero-cta">
        Shop now
      </Link>
    </section>
  )
}

export default Hero
