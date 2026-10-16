// "2026-10-15T21:31:19+00:00" → "15 Oct 2026, 22:31" (in the viewer's time zone)
export const formatDate = (iso) =>
  new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
