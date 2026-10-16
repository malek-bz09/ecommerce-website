const formatter = new Intl.NumberFormat('en-dz', { style: 'currency', currency: 'DZD' })

export const formatPrice = (price) => formatter.format(price)
