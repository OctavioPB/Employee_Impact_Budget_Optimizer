import { useState, useEffect } from 'react'
import { api, Notification } from '../services/api'

const SEV_COLORS: Record<Notification['severity'], string> = {
  info:     'var(--primary-60)',
  warning:  'var(--status-orange)',
  critical: 'var(--status-red)',
}

const SEV_BG: Record<Notification['severity'], string> = {
  info:     'rgba(51,102,153,0.08)',
  warning:  'rgba(240,112,32,0.08)',
  critical: 'rgba(224,52,72,0.08)',
}

function NotificationCard({ notif, onMarkRead }: { notif: Notification; onMarkRead: (id: string) => void }) {
  const color = SEV_COLORS[notif.severity]
  const bg    = SEV_BG[notif.severity]

  const timeAgo = (() => {
    const diff = Date.now() - new Date(notif.created_at).getTime()
    const mins  = Math.floor(diff / 60000)
    if (mins < 60)  return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs  < 24)  return `${hrs}h ago`
    return `${Math.floor(hrs / 24)}d ago`
  })()

  return (
    <div style={{
      backgroundColor: notif.read ? 'var(--white)' : bg,
      borderRadius:    'var(--radius-md)',
      boxShadow:       'var(--shadow-card)',
      padding:         '20px 24px',
      borderLeft:      `3px solid ${notif.read ? 'var(--primary-10)' : color}`,
      display:         'flex',
      alignItems:      'flex-start',
      gap:             16,
      opacity:         notif.read ? 0.65 : 1,
    }}>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 5 }}>
          <span style={{
            fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '2px', textTransform: 'uppercase',
            fontWeight: 700, color, padding: '2px 8px', borderRadius: 'var(--radius-pill)',
            backgroundColor: `${color}18`, border: `1px solid ${color}40`,
          }}>{notif.severity}</span>
          {!notif.read && (
            <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: color, display: 'inline-block' }} />
          )}
          <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginLeft: 'auto' }}>{timeAgo}</span>
        </div>
        <div style={{ fontFamily: 'var(--fd)', fontSize: 15, fontWeight: 600, color: 'var(--primary)', marginBottom: 5 }}>{notif.title}</div>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', lineHeight: 1.6 }}>{notif.body}</div>
      </div>
      {!notif.read && (
        <button
          onClick={() => onMarkRead(notif.id)}
          style={{
            flexShrink: 0, background: 'none', border: '1px solid var(--primary-10)',
            borderRadius: 'var(--radius-sm)', padding: '5px 12px',
            fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase',
            color: 'var(--mid)', cursor: 'pointer',
          }}
        >Dismiss</button>
      )}
    </div>
  )
}

export default function NotificationsPage() {
  const [notifications, setNotifs] = useState<Notification[]>([])
  const [loading, setLoading]      = useState(true)
  const [error,   setError]        = useState<string | null>(null)
  const [filter,  setFilter]       = useState<'all' | 'unread'>('all')

  useEffect(() => {
    api.notifications.list()
      .then(setNotifs)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const markRead = async (id: string) => {
    try {
      await api.notifications.markRead(id)
      setNotifs(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
    } catch {
      // best-effort
    }
  }

  const markAllRead = async () => {
    const unread = notifications.filter(n => !n.read)
    await Promise.all(unread.map(n => api.notifications.markRead(n.id).catch(() => undefined)))
    setNotifs(prev => prev.map(n => ({ ...n, read: true })))
  }

  const displayed = filter === 'unread' ? notifications.filter(n => !n.read) : notifications
  const unreadCount = notifications.filter(n => !n.read).length

  const criticalCount = notifications.filter(n => n.severity === 'critical' && !n.read).length
  const warningCount  = notifications.filter(n => n.severity === 'warning'  && !n.read).length

  return (
    <div>
      {/* Hero */}
      <div style={{ background: 'var(--primary)', paddingTop: 48, paddingBottom: 48, paddingLeft: 48, paddingRight: 48 }}>
        <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 10 }}>
            Alerts & Notifications
          </div>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 38, fontWeight: 600, fontStyle: 'italic', color: '#fff', margin: '0 0 24px' }}>
            Notification Center
          </h1>

          {/* Counts */}
          <div style={{ display: 'flex', gap: 28 }}>
            {[
              { val: String(unreadCount),    label: 'Unread',   color: 'var(--gold-light)'  },
              { val: String(criticalCount),  label: 'Critical', color: 'var(--status-red)'  },
              { val: String(warningCount),   label: 'Warnings', color: 'var(--status-orange)' },
            ].map(({ val, label, color }) => (
              <div key={label} style={{ borderLeft: `3px solid ${color}`, paddingLeft: 14 }}>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 700, color }}>{val}</div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)' }}>{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto', padding: '32px 48px' }}>
        {/* Toolbar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            {(['all', 'unread'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                style={{
                  fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase',
                  fontWeight: 600, padding: '6px 14px', borderRadius: 'var(--radius-pill)',
                  border: 'none', cursor: 'pointer',
                  backgroundColor: filter === f ? 'var(--primary)' : 'var(--white)',
                  color:           filter === f ? '#fff' : 'var(--mid)',
                  boxShadow:       'var(--shadow-card)',
                }}
              >{f === 'all' ? `All (${notifications.length})` : `Unread (${unreadCount})`}</button>
            ))}
          </div>

          {unreadCount > 0 && (
            <button
              onClick={markAllRead}
              style={{
                fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase',
                fontWeight: 600, padding: '6px 16px', borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--primary-30)', backgroundColor: 'transparent',
                color: 'var(--primary)', cursor: 'pointer',
              }}
            >Mark All Read</button>
          )}
        </div>

        {loading && <div style={{ fontFamily: 'var(--fd)', fontSize: 20, color: 'var(--primary)' }}>Loading…</div>}
        {error   && <div style={{ color: 'var(--status-red)', fontFamily: 'var(--fb)', fontSize: 13 }}>{error}</div>}

        {!loading && !error && (
          displayed.length > 0
            ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {displayed.map(n => (
                  <NotificationCard key={n.id} notif={n} onMarkRead={markRead} />
                ))}
              </div>
            )
            : (
              <div style={{
                backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)',
                boxShadow: 'var(--shadow-card)', padding: 48, textAlign: 'center',
              }}>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 20, color: 'var(--primary)', marginBottom: 8 }}>All clear</div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>No {filter === 'unread' ? 'unread ' : ''}notifications at this time.</div>
              </div>
            )
        )}
      </div>
    </div>
  )
}
