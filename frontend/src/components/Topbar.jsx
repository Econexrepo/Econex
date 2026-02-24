import { useAuth } from '../context/AuthContext'
import './Topbar.css'

export default function Topbar() {
  const { user } = useAuth()
  const initials = user?.name
    ? user.name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()
    : 'U'

  return (
    <header className="topbar">
      <div className="topbar-left" />
      <div className="topbar-right">
        <div className="topbar-avatar" title={user?.name}>
          {user?.avatar_url
            ? <img src={user.avatar_url} alt={user.name} />
            : <span>{initials}</span>
          }
        </div>
      </div>
    </header>
  )
}
