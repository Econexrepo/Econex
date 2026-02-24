import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import api from '../api/axios'
import './Settings.css'

export default function Settings() {
  const { user, updateUser } = useAuth()

  const [form, setForm] = useState({
    first_name: '',
    last_name:  '',
    username:   '',
    email:      '',
    phone:      '',
  })
  const [saving,   setSaving]   = useState(false)
  const [success,  setSuccess]  = useState('')
  const [error,    setError]    = useState('')

  // Populate from stored user
  useEffect(() => {
    if (user) {
      const parts = (user.name || '').split(' ')
      setForm({
        first_name: parts[0] || '',
        last_name:  parts.slice(1).join(' ') || '',
        username:   user.username || '',
        email:      user.email    || '',
        phone:      user.phone    || '',
      })
    }
  }, [user])

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
    setSuccess('')
    setError('')
  }

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setSuccess('')
    setError('')
    try {
      const { data } = await api.patch('/api/settings/profile', {
        first_name: form.first_name,
        last_name:  form.last_name,
        username:   form.username,
        phone:      form.phone,
      })
      updateUser(data)
      setSuccess('Profile updated successfully!')
    } catch {
      // Silently apply locally when API isn't running
      updateUser({
        ...user,
        name:     `${form.first_name} ${form.last_name}`.trim(),
        username: form.username,
        phone:    form.phone,
      })
      setSuccess('Profile saved locally (API not connected).')
    } finally {
      setSaving(false)
    }
  }

  const initials = user?.name
    ? user.name.split(' ').map((n) => n[0]).join('').slice(0,2).toUpperCase()
    : 'U'

  return (
    <div className="settings-page">
      <div className="settings-card">
        <p className="settings-email-notice">
          Your current Primary email address is{' '}
          <a href={`mailto:${user?.email}`} className="email-link">{user?.email}</a>
        </p>

        {/* Avatar */}
        <div className="avatar-row">
          <span className="settings-label">Avatar</span>
          <div className="avatar-area">
            <div className="settings-avatar">
              {user?.avatar_url
                ? <img src={user.avatar_url} alt="avatar" />
                : <span>{initials}</span>
              }
            </div>
            <button className="avatar-btn avatar-btn--outline" type="button">Change</button>
            <button className="avatar-btn avatar-btn--outline" type="button">Remove</button>
          </div>
        </div>

        <hr className="settings-divider" />

        <div className="settings-section-heading">
          <h2>Basic information</h2>
          <p>Update some personal information. Your address will never be publicly available.</p>
        </div>

        <form className="settings-form" onSubmit={handleSave}>
          {/* Full name */}
          <div className="field-row">
            <label className="settings-label">Full name</label>
            <div className="name-inputs">
              <input
                id="settings-first-name"
                name="first_name"
                type="text"
                placeholder="First name"
                value={form.first_name}
                onChange={handleChange}
              />
              <input
                id="settings-last-name"
                name="last_name"
                type="text"
                placeholder="Last Name"
                value={form.last_name}
                onChange={handleChange}
              />
            </div>
          </div>

          {/* Username */}
          <div className="field-row">
            <label htmlFor="settings-username" className="settings-label">User name</label>
            <div className="single-input">
              <input
                id="settings-username"
                name="username"
                type="text"
                placeholder="user name"
                value={form.username}
                onChange={handleChange}
              />
            </div>
          </div>

          {/* Email */}
          <div className="field-row">
            <label htmlFor="settings-email" className="settings-label">Email</label>
            <div className="full-input">
              <input
                id="settings-email"
                name="email"
                type="email"
                placeholder="Email"
                value={form.email}
                disabled
              />
            </div>
          </div>

          {/* Phone */}
          <div className="field-row">
            <label htmlFor="settings-phone" className="settings-label">Phone</label>
            <div className="full-input">
              <input
                id="settings-phone"
                name="phone"
                type="tel"
                placeholder="Phone"
                value={form.phone}
                onChange={handleChange}
              />
            </div>
          </div>

          {success && <p className="settings-success">{success}</p>}
          {error   && <p className="settings-error">{error}</p>}

          <div className="settings-actions">
            <button
              id="settings-save-btn"
              type="submit"
              className="save-btn"
              disabled={saving}
            >
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
