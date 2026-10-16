import { wilayas } from '../data/wilayas'

export const LIMITS = {
  fullName: 80,
  phone: 20,
  email: 254,
  commune: 60,
  address: 200,
  notes: 500,
}

const NAME_PATTERN = /^[\p{L}\s'.-]+$/u
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
// Algerian mobile: 05/06/07 + 8 digits, with optional +213 / 00213 prefix
const PHONE_PATTERN = /^(?:\+213|00213|0)([567]\d{8})$/

// Strip spaces, dots, dashes and brackets people type into phone numbers
const compactPhone = (value) => value.replace(/[\s.\-()]/g, '')

// Normalize to the local 0XXXXXXXXX format, or null when invalid
export function normalizePhone(value) {
  const match = compactPhone(value).match(PHONE_PATTERN)
  return match ? `0${match[1]}` : null
}

const validators = {
  fullName(value) {
    const name = value.trim()
    if (!name) return 'Please enter your full name.'
    if (name.length < 3) return 'Name must be at least 3 characters.'
    if (name.length > LIMITS.fullName) return `Name must be under ${LIMITS.fullName} characters.`
    if (!NAME_PATTERN.test(name)) return 'Name can only contain letters, spaces, apostrophes and hyphens.'
    if (name.split(/\s+/).length < 2) return 'Please enter your first and last name.'
    return null
  },
  phone(value) {
    if (!value.trim()) return 'Please enter your phone number.'
    if (/[^\d\s.\-()+]/.test(value)) return 'Phone number can only contain digits.'
    if (!normalizePhone(value)) return 'Enter a valid mobile number, e.g. 0555 12 34 56.'
    return null
  },
  email(value) {
    const email = value.trim()
    if (!email) return 'Please enter your email address.'
    if (email.length > LIMITS.email) return 'Email address is too long.'
    if (!EMAIL_PATTERN.test(email)) return 'Enter a valid email address, e.g. name@example.com.'
    return null
  },
  wilaya(value) {
    if (!value) return 'Please select your wilaya.'
    if (!wilayas.some((w) => w.code === value)) return 'Please select a valid wilaya.'
    return null
  },
  commune(value) {
    const commune = value.trim()
    if (!commune) return 'Please enter your commune.'
    if (commune.length < 2) return 'Commune must be at least 2 characters.'
    if (commune.length > LIMITS.commune) return `Commune must be under ${LIMITS.commune} characters.`
    return null
  },
  address(value) {
    const address = value.trim()
    if (!address) return 'Please enter your delivery address.'
    if (address.length < 10) return 'Please give a more detailed address (street, building, floor…).'
    if (address.length > LIMITS.address) return `Address must be under ${LIMITS.address} characters.`
    return null
  },
  notes(value) {
    if (value.trim().length > LIMITS.notes) return `Notes must be under ${LIMITS.notes} characters.`
    return null
  },
}

export const FIELDS = Object.keys(validators)

export const validateField = (field, value) => validators[field](value ?? '')

// Returns { field: message } for every invalid field
export function validateCheckout(values) {
  const errors = {}
  for (const field of FIELDS) {
    const error = validateField(field, values[field])
    if (error) errors[field] = error
  }
  return errors
}
