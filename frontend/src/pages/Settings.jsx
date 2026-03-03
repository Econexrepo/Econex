import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import api from '../api/axios'
import './Settings.css'

/* ── Eye icons (inline SVG, no extra lib needed) ───────────────────────────── */
const EyeIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
       fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
    <circle cx="12" cy="12" r="3"/>
  </svg>
)

const EyeOffIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
       fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
    <line x1="1" y1="1" x2="23" y2="23"/>
  </svg>
)

/* ── Password input with show/hide toggle ───────────────────────────────────── */
function PasswordInput({ id, name, placeholder, value, onChange, required }) {
  const [show, setShow] = useState(false)
  return (
    <div className="pw-input-wrap">
      <input
        id={id}
        name={name}
        type={show ? 'text' : 'password'}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        required={required}
        autoComplete="off"
      />
      <button
        type="button"
        className="pw-eye-btn"
        onClick={() => setShow((s) => !s)}
        tabIndex={-1}
        aria-label={show ? 'Hide password' : 'Show password'}
      >
        {show ? <EyeOffIcon /> : <EyeIcon />}
      </button>
    </div>
  )
}

export default function Settings() {
  const { user, updateUser } = useAuth()
  const fileInputRef = useRef(null)

  /* ── Profile form ──────────────────────────────────────────────────────── */
  const [form, setForm] = useState({
    first_name: '',
    last_name:  '',
    username:   '',
    email:      '',
    phone:      '',
  })
  const [fieldErrors, setFieldErrors] = useState({})   // inline per-field errors
  const [saving,      setSaving]      = useState(false)
  const [profileMsg,  setProfileMsg]  = useState({ type: '', text: '' })

  /* ── Avatar state ─────────────────────────────────────────────────────── */
  const [avatarPreview,   setAvatarPreview]   = useState(null)
  const [avatarUploading, setAvatarUploading] = useState(false)
  const [avatarMsg,       setAvatarMsg]       = useState({ type: '', text: '' })

  /* ── Password form ────────────────────────────────────────────────────── */
  const [pwForm, setPwForm] = useState({
    current_password: '',
    new_password:     '',
    confirm_password: '',
  })
  const [pwErrors,   setPwErrors]   = useState({})
  const [changingPw, setChangingPw] = useState(false)
  const [pwMsg,      setPwMsg]      = useState({ type: '', text: '' })

  /* ── Populate from stored user ─────────────────────────────────────────── */
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

  /* ── Profile handlers ─────────────────────────────────────────────────── */
  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    // Clear that field's inline error as user types
    if (fieldErrors[name]) setFieldErrors((prev) => ({ ...prev, [name]: '' }))
    setProfileMsg({ type: '', text: '' })
  }

  /** Phone: only allow digits while typing */
  const handlePhoneChange = (e) => {
    const digits = e.target.value.replace(/\D/g, '').slice(0, 10)
    setForm((prev) => ({ ...prev, phone: digits }))
    if (fieldErrors.phone) setFieldErrors((prev) => ({ ...prev, phone: '' }))
    setProfileMsg({ type: '', text: '' })
  }

  /** Validate profile fields — returns true if valid */
  const validateProfile = () => {
    const errs = {}

    if (!form.first_name.trim()) {
      errs.first_name = 'First name is required.'
    }
    if (!form.username.trim()) {
      errs.username = 'Username is required.'
    }
    if (form.phone && !/^\d{10}$/.test(form.phone)) {
      errs.phone = 'Phone must be exactly 10 digits.'
    }

    setFieldErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSave = async (e) => {
    e.preventDefault()
    if (!validateProfile()) return

    setSaving(true)
    setProfileMsg({ type: '', text: '' })
    try {
      const { data } = await api.patch('/api/settings/profile', {
        first_name: form.first_name.trim(),
        last_name:  form.last_name.trim(),
        username:   form.username.trim(),
        phone:      form.phone,
      })
      updateUser(data)
      setProfileMsg({ type: 'success', text: 'Profile updated successfully!' })
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to update profile.'
      setProfileMsg({ type: 'error', text: msg })
    } finally {
      setSaving(false)
    }
  }

  /* ── Avatar handlers ──────────────────────────────────────────────────── */
  const handleAvatarClick = () => fileInputRef.current?.click()

  const handleFileSelected = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    const allowed = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
    if (!allowed.includes(file.type)) {
      setAvatarMsg({ type: 'error', text: 'Please choose a JPEG, PNG, WebP or GIF image.' })
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setAvatarMsg({ type: 'error', text: 'Image must be smaller than 5 MB.' })
      return
    }

    const previewUrl = URL.createObjectURL(file)
    setAvatarPreview(previewUrl)
    setAvatarMsg({ type: '', text: '' })
    setAvatarUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await api.post('/api/settings/avatar/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      updateUser(data)
      setAvatarPreview(null)
      setAvatarMsg({ type: 'success', text: 'Profile picture updated!' })
    } catch (err) {
      setAvatarPreview(null)
      const msg = err?.response?.data?.detail || 'Upload failed. Please try again.'
      setAvatarMsg({ type: 'error', text: msg })
    } finally {
      setAvatarUploading(false)
      e.target.value = ''
    }
  }

  const handleRemoveAvatar = async () => {
    setAvatarMsg({ type: '', text: '' })
    setAvatarUploading(true)
    try {
      const { data } = await api.patch('/api/settings/avatar', { avatar_url: '' })
      updateUser(data)
      setAvatarPreview(null)
      setAvatarMsg({ type: 'success', text: 'Profile picture removed.' })
    } catch {
      setAvatarMsg({ type: 'error', text: 'Failed to remove picture.' })
    } finally {
      setAvatarUploading(false)
    }
  }

  /* ── Password handlers ────────────────────────────────────────────────── */
  const handlePwChange = (e) => {
    const { name, value } = e.target
    setPwForm((prev) => ({ ...prev, [name]: value }))
    if (pwErrors[name]) setPwErrors((prev) => ({ ...prev, [name]: '' }))
    setPwMsg({ type: '', text: '' })
  }

  /** Validate password form — returns true if valid */
  const validatePassword = () => {
    const errs = {}

    if (!pwForm.current_password) {
      errs.current_password = 'Enter your current password.'
    }
    if (pwForm.new_password.length < 8) {
      errs.new_password = 'Password must be at least 8 characters.'
    }
    if (pwForm.new_password !== pwForm.confirm_password) {
      errs.confirm_password = 'Passwords do not match.'
    }

    setPwErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleChangePassword = async (e) => {
    e.preventDefault()
    if (!validatePassword()) return

    setChangingPw(true)
    setPwMsg({ type: '', text: '' })
    try {
      await api.post('/api/settings/change-password', {
        current_password: pwForm.current_password,
        new_password:     pwForm.new_password,
      })
      setPwMsg({ type: 'success', text: 'Password changed successfully!' })
      setPwForm({ current_password: '', new_password: '', confirm_password: '' })
      setPwErrors({})
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to change password.'
      setPwMsg({ type: 'error', text: msg })
    } finally {
      setChangingPw(false)
    }
  }

  /* ── UI helpers ───────────────────────────────────────────────────────── */
  const initials     = user?.name
    ? user.name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()
    : 'U'
  const displayAvatar = avatarPreview || user?.avatar_url

  return (
    <div className="settings-page">
      <div className="settings-card">
        <p className="settings-email-notice">
          Your current Primary email address is{' '}
          <a href={`mailto:${user?.email}`} className="email-link">{user?.email}</a>
        </p>

        {/* ── Avatar ───────────────────────────────────────────────────── */}
        <div className="avatar-row">
          <span className="settings-label">Avatar</span>
          <div className="avatar-area">
            <div className={`settings-avatar${avatarUploading ? ' avatar--uploading' : ''}`}>
              {displayAvatar
                ? <img src={displayAvatar} alt="avatar" />
                : <span>{initials}</span>
              }
              {avatarUploading && <div className="avatar-spinner" />}
            </div>

            <input
              ref={fileInputRef}
              id="avatar-file-input"
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              style={{ display: 'none' }}
              onChange={handleFileSelected}
            />

            <button
              className="avatar-btn avatar-btn--outline"
              type="button"
              onClick={handleAvatarClick}
              disabled={avatarUploading}
            >
              {avatarUploading ? 'Uploading…' : 'Change'}
            </button>

            <button
              className="avatar-btn avatar-btn--outline avatar-btn--danger"
              type="button"
              onClick={handleRemoveAvatar}
              disabled={avatarUploading}
            >
              Remove
            </button>
          </div>
        </div>

        {avatarMsg.text && (
          <p className={`avatar-msg ${avatarMsg.type === 'success' ? 'settings-success' : 'settings-error'}`}>
            {avatarMsg.text}
          </p>
        )}

        <hr className="settings-divider" />

        {/* ── Basic Information ─────────────────────────────────────────── */}
        <div className="settings-section-heading">
          <h2>Basic information</h2>
          <p>Update your personal information. Your address will never be publicly available.</p>
        </div>

        <form className="settings-form" onSubmit={handleSave} noValidate>

          {/* Full name */}
          <div className="field-row">
            <label className="settings-label">
              Full name <span className="required-star">*</span>
            </label>
            <div className="name-inputs">
              <div className="input-group">
                <input
                  id="settings-first-name"
                  name="first_name"
                  type="text"
                  placeholder="First name"
                  value={form.first_name}
                  onChange={handleChange}
                  className={fieldErrors.first_name ? 'input--error' : ''}
                />
                {fieldErrors.first_name && (
                  <span className="field-error">{fieldErrors.first_name}</span>
                )}
              </div>
              <div className="input-group">
                <input
                  id="settings-last-name"
                  name="last_name"
                  type="text"
                  placeholder="Last name"
                  value={form.last_name}
                  onChange={handleChange}
                />
              </div>
            </div>
          </div>

          {/* Username */}
          <div className="field-row">
            <label htmlFor="settings-username" className="settings-label">
              Username <span className="required-star">*</span>
            </label>
            <div className="single-input">
              <div className="input-group">
                <input
                  id="settings-username"
                  name="username"
                  type="text"
                  placeholder="username"
                  value={form.username}
                  onChange={handleChange}
                  className={fieldErrors.username ? 'input--error' : ''}
                />
                {fieldErrors.username && (
                  <span className="field-error">{fieldErrors.username}</span>
                )}
              </div>
            </div>
          </div>

          {/* Email (read-only) */}
          <div className="field-row">
            <label htmlFor="settings-email" className="settings-label">Email</label>
            <div className="full-input">
              <input
                id="settings-email"
                name="email"
                type="email"
                value={form.email}
                disabled
              />
            </div>
          </div>

          {/* Phone */}
          <div className="field-row">
            <label htmlFor="settings-phone" className="settings-label">Phone</label>
            <div className="full-input">
              <div className="input-group">
                <input
                  id="settings-phone"
                  name="phone"
                  type="tel"
                  inputMode="numeric"
                  placeholder="10-digit phone number"
                  value={form.phone}
                  onChange={handlePhoneChange}
                  maxLength={10}
                  className={fieldErrors.phone ? 'input--error' : ''}
                />
                {fieldErrors.phone && (
                  <span className="field-error">{fieldErrors.phone}</span>
                )}
              </div>
            </div>
          </div>

          {profileMsg.text && (
            <p className={profileMsg.type === 'success' ? 'settings-success' : 'settings-error'}>
              {profileMsg.text}
            </p>
          )}

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

        <hr className="settings-divider" />

        {/* ── Change Password ───────────────────────────────────────────── */}
        <div className="settings-section-heading">
          <h2>Change password</h2>
          <p>Must be at least 8 characters. Click the eye icon to show/hide.</p>
        </div>

        <form className="settings-form" onSubmit={handleChangePassword} noValidate>

          <div className="field-row">
            <label htmlFor="settings-current-pw" className="settings-label">Current password</label>
            <div className="full-input">
              <div className="input-group">
                <PasswordInput
                  id="settings-current-pw"
                  name="current_password"
                  placeholder="Enter current password"
                  value={pwForm.current_password}
                  onChange={handlePwChange}
                  required
                />
                {pwErrors.current_password && (
                  <span className="field-error">{pwErrors.current_password}</span>
                )}
              </div>
            </div>
          </div>

          <div className="field-row">
            <label htmlFor="settings-new-pw" className="settings-label">New password</label>
            <div className="full-input">
              <div className="input-group">
                <PasswordInput
                  id="settings-new-pw"
                  name="new_password"
                  placeholder="At least 8 characters"
                  value={pwForm.new_password}
                  onChange={handlePwChange}
                  required
                />
                {pwErrors.new_password && (
                  <span className="field-error">{pwErrors.new_password}</span>
                )}
              </div>
            </div>
          </div>

          <div className="field-row">
            <label htmlFor="settings-confirm-pw" className="settings-label">Confirm new</label>
            <div className="full-input">
              <div className="input-group">
                <PasswordInput
                  id="settings-confirm-pw"
                  name="confirm_password"
                  placeholder="Repeat new password"
                  value={pwForm.confirm_password}
                  onChange={handlePwChange}
                  required
                />
                {pwErrors.confirm_password && (
                  <span className="field-error">{pwErrors.confirm_password}</span>
                )}
              </div>
            </div>
          </div>

          {pwMsg.text && (
            <p className={pwMsg.type === 'success' ? 'settings-success' : 'settings-error'}>
              {pwMsg.text}
            </p>
          )}

          <div className="settings-actions">
            <button
              id="settings-change-pw-btn"
              type="submit"
              className="save-btn"
              disabled={changingPw}
            >
              {changingPw ? 'Updating…' : 'Change Password'}
            </button>
          </div>
        </form>

      </div>
    </div>
  )
}
