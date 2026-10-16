import { STATUSES } from './orderStatus'

function StatusBadge({ status }) {
  const { label, tone } = STATUSES[status]
  return <span className={`admin-status admin-status--${tone}`}>{label}</span>
}

export default StatusBadge
