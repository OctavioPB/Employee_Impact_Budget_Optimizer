import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  api,
  DecisionSession,
  SessionConflict,
  EmployeeRow,
  CreateSessionBody,
} from '../services/api'
import { useDemoStore } from '../stores/demoStore'

// ── Personas (simulate multi-user) ────────────────────────────────────────────

const PERSONAS = [
  { user_id: 'u_chen',    display_name: 'Director Chen',        role: 'Owner'       as const },
  { user_id: 'u_rivera',  display_name: 'HR Partner Rivera',    role: 'Participant' as const },
  { user_id: 'u_hoffman', display_name: 'Manager Hoffman',      role: 'Participant' as const },
  { user_id: 'u_okonkwo', display_name: 'Finance Lead Okonkwo', role: 'Observer'    as const },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

function StatusBadge({ status }: { status: DecisionSession['status'] }) {
  const MAP: Record<string, [string, string]> = {
    'Draft':        ['#a0a0a0', 'rgba(160,160,160,0.12)'],
    'Active':       ['#1a8c4e', 'rgba(26,140,78,0.12)'],
    'Under Review': ['#c8982a', 'rgba(200,152,42,0.12)'],
    'Finalized':    ['#003366', 'rgba(0,51,102,0.12)'],
  }
  const [color, bg] = MAP[status] ?? ['#888', '#eee']
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 4,
      fontSize: 10, fontFamily: 'var(--fb)', fontWeight: 600,
      letterSpacing: '1px', textTransform: 'uppercase',
      backgroundColor: bg, color,
    }}>
      {status}
    </span>
  )
}

function RoleBadge({ role }: { role: string }) {
  const c = role === 'Owner' ? '#003366' : role === 'Participant' ? '#1a5c8c' : '#888'
  return (
    <span style={{
      fontSize: 9, fontFamily: 'var(--fb)', letterSpacing: '1px',
      textTransform: 'uppercase', color: c, border: `1px solid ${c}`,
      borderRadius: 3, padding: '1px 5px',
    }}>
      {role}
    </span>
  )
}

function OverrideChip({ type }: { type: 'retain' | 'exclude' }) {
  return (
    <span style={{
      display: 'inline-block', padding: '1px 7px', borderRadius: 10,
      fontSize: 9, fontFamily: 'var(--fb)', fontWeight: 600, letterSpacing: '1px',
      textTransform: 'uppercase',
      backgroundColor: type === 'retain' ? 'rgba(26,140,78,0.12)' : 'rgba(100,100,100,0.10)',
      color: type === 'retain' ? '#1a8c4e' : '#666',
    }}>
      {type === 'retain' ? 'Retain' : 'Under Review'}
    </span>
  )
}

// ── Action button styles ──────────────────────────────────────────────────────

const btnBase: React.CSSProperties = {
  border: '1px solid var(--border)', borderRadius: 4, cursor: 'pointer',
  fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
  textTransform: 'uppercase', padding: '4px 10px',
  background: 'none', transition: 'background 0.15s, color 0.15s',
}
const btnPrimary: React.CSSProperties = {
  ...btnBase, backgroundColor: 'var(--navy)', color: '#fff', border: 'none',
}
const btnGold: React.CSSProperties = {
  ...btnBase, backgroundColor: 'rgba(201,168,76,0.12)', color: 'var(--gold-mid)',
  border: '1px solid rgba(201,168,76,0.3)',
}
// ── Session List View ─────────────────────────────────────────────────────────

function SessionListView({
  sessions,
  onSelect,
  onSeed,
  onCreateNew,
  loading,
}: {
  sessions: DecisionSession[]
  onSelect: (id: string) => void
  onSeed:   () => void
  onCreateNew: () => void
  loading: boolean
}) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 24 }}>
        <div>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold-mid)', marginBottom: 6 }}>
            Sprint 14 · Collaborative Decision Room
          </p>
          <h1 style={{ fontFamily: 'var(--fd)', fontWeight: 300, fontSize: 28, color: 'var(--navy)', margin: 0 }}>
            Decision Sessions
          </h1>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button style={btnGold} onClick={onSeed}>Load Demo Session</button>
          <button style={btnPrimary} onClick={onCreateNew}>+ New Session</button>
        </div>
      </div>

      {loading && (
        <p style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--fb)', letterSpacing: '1px' }}>
          Loading sessions…
        </p>
      )}

      {!loading && sessions.length === 0 && (
        <div style={{
          border: '1px dashed var(--border)', borderRadius: 8,
          padding: '48px 32px', textAlign: 'center',
        }}>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
            No sessions yet. Load the demo session or create a new one.
          </p>
          <button style={btnGold} onClick={onSeed}>Load Demo Session</button>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {sessions.map(s => (
          <div
            key={s.session_id}
            onClick={() => onSelect(s.session_id)}
            style={{
              backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)',
              borderRadius: 8, padding: '16px 20px', cursor: 'pointer',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              transition: 'border-color 0.15s',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <span style={{ fontFamily: 'var(--fd)', fontSize: 16, color: 'var(--navy)', fontWeight: 300 }}>
                  {s.name}
                </span>
                <StatusBadge status={s.status} />
              </div>
              <div style={{ display: 'flex', gap: 16, fontSize: 11, color: 'var(--text-muted)' }}>
                <span>Scenario {s.scenario.toUpperCase()} · {s.size}</span>
                <span>Budget: {s.budget_pct}%</span>
                <span>{s.participants.length} participant{s.participants.length !== 1 ? 's' : ''}</span>
                <span>{s.overrides.length} override{s.overrides.length !== 1 ? 's' : ''}</span>
                {s.conflicts.filter(c => !c.resolved).length > 0 && (
                  <span style={{ color: '#c8982a' }}>
                    ⚠ {s.conflicts.filter(c => !c.resolved).length} conflict{s.conflicts.filter(c => !c.resolved).length !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {fmtDate(s.created_at)} →
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Create Session Dialog ─────────────────────────────────────────────────────

function CreateSessionDialog({
  scenario,
  size,
  onCreated,
  onCancel,
}: {
  scenario: string
  size:     string
  onCreated: (s: DecisionSession) => void
  onCancel:  () => void
}) {
  const [name, setName]   = useState('Q3 Budget Planning Session')
  const [persona]         = useState(PERSONAS[0])
  const [budgetPct, setBudgetPct] = useState(85)
  const [resMode, setResMode]     = useState('owner')
  const [busy, setBusy]           = useState(false)

  async function handleCreate() {
    setBusy(true)
    try {
      const body: CreateSessionBody = {
        name,
        owner_name:      persona.display_name,
        owner_id:        persona.user_id,
        scenario,
        size,
        budget_pct:      budgetPct,
        resolution_mode: resMode,
      }
      const session = await api.decisionRoom.create(body)
      onCreated(session)
    } finally {
      setBusy(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%', border: '1px solid var(--border)', borderRadius: 4,
    padding: '7px 10px', fontFamily: 'var(--fb)', fontSize: 12,
    backgroundColor: 'var(--card-bg)', color: 'var(--text-body)',
    boxSizing: 'border-box',
  }
  const labelStyle: React.CSSProperties = {
    fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
    textTransform: 'uppercase', color: 'var(--text-muted)',
    display: 'block', marginBottom: 5,
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }}>
      <div style={{
        backgroundColor: 'var(--card-bg)', borderRadius: 10,
        padding: 32, width: 480, border: '1px solid var(--border)',
      }}>
        <h2 style={{ fontFamily: 'var(--fd)', fontWeight: 300, color: 'var(--navy)', margin: '0 0 24px', fontSize: 22 }}>
          New Decision Session
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={labelStyle}>Session Name</label>
            <input style={inputStyle} value={name} onChange={e => setName(e.target.value)} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>Target Budget %</label>
              <input style={inputStyle} type="number" min={50} max={120}
                value={budgetPct} onChange={e => setBudgetPct(Number(e.target.value))} />
            </div>
            <div>
              <label style={labelStyle}>Conflict Resolution</label>
              <select style={inputStyle} value={resMode} onChange={e => setResMode(e.target.value)}>
                <option value="owner">Owner decides</option>
                <option value="vote">Majority vote</option>
                <option value="last_write">Last write wins</option>
              </select>
            </div>
          </div>
          <div style={{ padding: '10px 12px', backgroundColor: 'rgba(0,51,102,0.04)', borderRadius: 6, fontSize: 11, color: 'var(--text-muted)' }}>
            Session will use <strong>Scenario {scenario.toUpperCase()}</strong> · <strong>{size}</strong> org.
            You will join as <strong>{persona.display_name}</strong> (Owner).
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, marginTop: 24, justifyContent: 'flex-end' }}>
          <button style={btnBase} onClick={onCancel}>Cancel</button>
          <button style={btnPrimary} onClick={handleCreate} disabled={busy}>
            {busy ? 'Creating…' : 'Create Session'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Participants Panel ────────────────────────────────────────────────────────

function ParticipantsPanel({
  session,
  currentUser,
}: {
  session:     DecisionSession
  currentUser: typeof PERSONAS[0]
}) {
  return (
    <div style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 16 }}>
      <h3 style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12, fontWeight: 500 }}>
        Participants
      </h3>
      {session.participants.map(p => (
        <div key={p.user_id} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 10 }}>
          <div style={{
            width: 28, height: 28, borderRadius: '50%',
            backgroundColor: p.user_id === currentUser.user_id ? 'var(--navy)' : 'rgba(0,51,102,0.12)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 11, fontWeight: 600, color: p.user_id === currentUser.user_id ? '#fff' : 'var(--navy)',
            flexShrink: 0,
          }}>
            {p.display_name.charAt(0)}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, color: 'var(--text-body)', fontWeight: p.user_id === currentUser.user_id ? 600 : 400 }}>
                {p.display_name}
              </span>
              <RoleBadge role={p.role} />
              {p.user_id === currentUser.user_id && (
                <span style={{ fontSize: 9, color: 'var(--gold-mid)', fontFamily: 'var(--fb)', letterSpacing: '1px' }}>YOU</span>
              )}
            </div>
            <p style={{ fontSize: 10, color: 'var(--text-muted)', margin: '2px 0 0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {p.last_action}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Activity Feed ─────────────────────────────────────────────────────────────

function ActivityFeed({ session }: { session: DecisionSession }) {
  const feed = [...session.activity].reverse().slice(0, 30)
  const actionColor: Record<string, string> = {
    retain_override:  '#1a8c4e',
    exclude_override: '#888',
    removed_override: '#c8982a',
    resolved_conflict:'#003366',
    proposed:         '#1a5c8c',
    objected_to:      '#e07030',
    voted:            '#003366',
    vote_closed:      '#1a5c8c',
    signed_off:       '#1a8c4e',
    finalized:        '#003366',
    commented_on:     'var(--text-muted)',
  }
  return (
    <div style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 16, marginTop: 12 }}>
      <h3 style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 10, fontWeight: 500 }}>
        Activity Feed
      </h3>
      <div style={{ maxHeight: 300, overflowY: 'auto' }}>
        {feed.length === 0 && (
          <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0 }}>No activity yet.</p>
        )}
        {feed.map(ev => (
          <div key={ev.id} style={{ display: 'flex', gap: 6, marginBottom: 8, alignItems: 'flex-start' }}>
            <span style={{ fontSize: 9, color: 'var(--text-muted)', whiteSpace: 'nowrap', marginTop: 1 }}>
              {fmtTime(ev.timestamp)}
            </span>
            <div style={{ flex: 1, fontSize: 11, lineHeight: 1.4 }}>
              <span style={{ fontWeight: 600, color: actionColor[ev.action] ?? 'var(--text-body)' }}>
                {ev.actor}
              </span>
              {' '}
              <span style={{ color: 'var(--text-muted)' }}>
                {ev.action.replace(/_/g, ' ')}
              </span>
              {ev.subject && (
                <span style={{ color: 'var(--text-body)' }}> {ev.subject}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Conflict Banner ───────────────────────────────────────────────────────────

function ConflictBanner({
  conflicts,
  session,
  currentUser,
  onRefresh,
}: {
  conflicts:   SessionConflict[]
  session:     DecisionSession
  currentUser: typeof PERSONAS[0]
  onRefresh:   () => void
}) {
  const open = conflicts.filter(c => !c.resolved)
  if (open.length === 0) return null

  const isOwner  = currentUser.role === 'Owner'
  const isVoteMode = session.resolution_mode === 'vote'

  async function resolve(eid: string, resolution: 'retain' | 'exclude') {
    await api.decisionRoom.resolveConflict(session.session_id, eid, resolution, currentUser.display_name)
    onRefresh()
  }

  return (
    <div style={{
      backgroundColor: 'rgba(200,152,42,0.08)', border: '1px solid rgba(200,152,42,0.3)',
      borderRadius: 8, padding: '14px 18px', marginBottom: 16,
    }}>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: '#c8982a', marginBottom: 10, fontWeight: 600 }}>
        ⚠ Override Conflicts — {open.length} unresolved
      </p>
      {open.map(c => (
        <div key={c.employee_id} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-body)', minWidth: 120 }}>
            {c.employee_name}
          </span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            <span style={{ color: '#1a8c4e' }}>{c.retain_by}</span> → Retain
            &nbsp;vs&nbsp;
            <span style={{ color: '#888' }}>{c.exclude_by}</span> → Under Review
          </span>
          {(isOwner || isVoteMode) && (
            <div style={{ display: 'flex', gap: 6 }}>
              <button style={{ ...btnBase, fontSize: 9, color: '#1a8c4e', borderColor: 'rgba(26,140,78,0.3)' }}
                onClick={() => resolve(c.employee_id, 'retain')}>
                Keep Retain
              </button>
              <button style={{ ...btnBase, fontSize: 9, color: '#888', borderColor: 'rgba(0,0,0,0.15)' }}
                onClick={() => resolve(c.employee_id, 'exclude')}>
                Keep Under Review
              </button>
            </div>
          )}
          {!isOwner && !isVoteMode && (
            <span style={{ fontSize: 10, color: 'var(--text-muted)', fontStyle: 'italic' }}>
              Awaiting Owner decision
            </span>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Employee Row in Workspace ─────────────────────────────────────────────────

function EmployeeWorkspaceRow({
  emp,
  session,
  currentUser,
  isObserver,
  onRefresh,
  onSelectForDeliberation,
  selectedId,
}: {
  emp:                    EmployeeRow
  session:                DecisionSession
  currentUser:            typeof PERSONAS[0]
  isObserver:             boolean
  onRefresh:              () => void
  onSelectForDeliberation:(id: string, name: string) => void
  selectedId:             string | null
}) {
  const retainOverrides  = session.overrides.filter(o => o.employee_id === emp.employee_id && o.override_type === 'retain')
  const excludeOverrides = session.overrides.filter(o => o.employee_id === emp.employee_id && o.override_type === 'exclude')
  const myOverride       = session.overrides.find(o => o.employee_id === emp.employee_id && o.set_by === currentUser.display_name)
  const conflict         = session.conflicts.find(c => c.employee_id === emp.employee_id && !c.resolved)
  const commentCount     = session.comments.filter(c => c.employee_id === emp.employee_id).length
  const proposalCount    = session.proposals.filter(p => p.employee_id === emp.employee_id).length
  const isSelected       = selectedId === emp.employee_id

  async function setOverride(type: 'retain' | 'exclude') {
    await api.decisionRoom.addOverride(session.session_id, {
      employee_id:   emp.employee_id,
      employee_name: emp.full_name,
      override_type: type,
      set_by:        currentUser.display_name,
      rationale:     '',
    })
    onRefresh()
  }

  async function clearOverride() {
    await api.decisionRoom.removeOverride(session.session_id, emp.employee_id, currentUser.display_name)
    onRefresh()
  }

  const isFinalized = session.status === 'Finalized'
  const rowBg = conflict ? 'rgba(200,152,42,0.06)' : isSelected ? 'rgba(0,51,102,0.04)' : 'transparent'

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '8px 12px', borderRadius: 6,
      backgroundColor: rowBg,
      borderBottom: '1px solid var(--border)',
      cursor: 'pointer',
    }}
      onClick={() => onSelectForDeliberation(emp.employee_id, emp.full_name)}
    >
      {/* Impact indicator bar */}
      <div style={{ width: 3, height: 32, borderRadius: 2, backgroundColor: `hsl(${emp.impact_score * 1.2}, 60%, 45%)`, flexShrink: 0 }} />

      {/* Name + meta */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-body)' }}>
            {emp.full_name}
          </span>
          {emp.is_nexus && (
            <span style={{ fontSize: 8, backgroundColor: 'rgba(201,168,76,0.15)', color: 'var(--gold-mid)', padding: '1px 5px', borderRadius: 3, fontFamily: 'var(--fb)', letterSpacing: '1px' }}>
              NEXUS
            </span>
          )}
          {conflict && <span title="Override conflict" style={{ fontSize: 12 }}>⚠️</span>}
        </div>
        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
          {emp.department} · Impact {emp.impact_score.toFixed(0)}
        </span>
      </div>

      {/* Override chips from all users */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', maxWidth: 160 }}>
        {retainOverrides.map(o => (
          <OverrideChip key={o.id} type="retain" />
        ))}
        {excludeOverrides.map(o => (
          <OverrideChip key={o.id} type="exclude" />
        ))}
      </div>

      {/* Deliberation indicators */}
      <div style={{ display: 'flex', gap: 6, fontSize: 10, color: 'var(--text-muted)' }}>
        {commentCount > 0  && <span>💬 {commentCount}</span>}
        {proposalCount > 0 && <span>📋 {proposalCount}</span>}
      </div>

      {/* Action buttons */}
      {!isObserver && !isFinalized && (
        <div style={{ display: 'flex', gap: 4 }} onClick={e => e.stopPropagation()}>
          {myOverride?.override_type === 'retain' ? (
            <button style={{ ...btnBase, fontSize: 8, color: '#1a8c4e', borderColor: 'rgba(26,140,78,0.4)', padding: '3px 8px' }}
              onClick={clearOverride}>✓ Retain</button>
          ) : (
            <button style={{ ...btnBase, fontSize: 8, padding: '3px 8px' }}
              onClick={() => setOverride('retain')}>Retain</button>
          )}
          {myOverride?.override_type === 'exclude' ? (
            <button style={{ ...btnBase, fontSize: 8, color: '#666', borderColor: 'rgba(0,0,0,0.3)', padding: '3px 8px' }}
              onClick={clearOverride}>✓ Review</button>
          ) : (
            <button style={{ ...btnBase, fontSize: 8, padding: '3px 8px' }}
              onClick={() => setOverride('exclude')}>Review</button>
          )}
        </div>
      )}
    </div>
  )
}

// ── Deliberation Panel ────────────────────────────────────────────────────────

function DeliberationPanel({
  session,
  currentUser,
  selectedEmployeeId,
  selectedEmployeeName,
  onRefresh,
}: {
  session:             DecisionSession
  currentUser:         typeof PERSONAS[0]
  selectedEmployeeId:  string | null
  selectedEmployeeName:string | null
  onRefresh:           () => void
}) {
  const [tab, setTab] = useState<'proposals' | 'comments'>('proposals')
  const [commentText, setCommentText] = useState('')
  const [proposalText, setProposalText] = useState('')
  const [proposalType, setProposalType] = useState<'retain' | 'exclude'>('retain')
  const [objectionText, setObjectionText] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  const isObserver   = currentUser.role === 'Observer'
  const isOwner      = currentUser.role === 'Owner'
  const isFinalized  = session.status === 'Finalized'

  const proposals = selectedEmployeeId
    ? session.proposals.filter(p => p.employee_id === selectedEmployeeId)
    : session.proposals

  const comments = selectedEmployeeId
    ? session.comments.filter(c => c.employee_id === selectedEmployeeId)
    : session.comments

  async function submitComment() {
    if (!selectedEmployeeId || !commentText.trim()) return
    setBusy(true)
    try {
      await api.decisionRoom.addComment(session.session_id, {
        employee_id:   selectedEmployeeId,
        employee_name: selectedEmployeeName ?? '',
        author:        currentUser.display_name,
        body:          commentText.trim(),
      })
      setCommentText('')
      onRefresh()
    } finally { setBusy(false) }
  }

  async function submitProposal() {
    if (!selectedEmployeeId || !proposalText.trim()) return
    setBusy(true)
    try {
      await api.decisionRoom.addProposal(session.session_id, {
        employee_id:   selectedEmployeeId,
        employee_name: selectedEmployeeName ?? '',
        override_type: proposalType,
        rationale:     proposalText.trim(),
        proposed_by:   currentUser.display_name,
      })
      setProposalText('')
      onRefresh()
    } finally { setBusy(false) }
  }

  async function submitObjection(pid: string) {
    const reason = (objectionText[pid] ?? '').trim()
    if (!reason) return
    await api.decisionRoom.addObjection(session.session_id, pid, currentUser.display_name, reason)
    setObjectionText(prev => ({ ...prev, [pid]: '' }))
    onRefresh()
  }

  async function openVote(pid: string) {
    await api.decisionRoom.openVote(session.session_id, pid, currentUser.display_name)
    onRefresh()
  }

  async function vote(pid: string, decision: 'yes' | 'no') {
    await api.decisionRoom.castVote(session.session_id, pid, currentUser.display_name, decision)
    onRefresh()
  }

  const tabStyle = (active: boolean): React.CSSProperties => ({
    background: 'none', border: 'none', cursor: 'pointer',
    fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '1.5px',
    textTransform: 'uppercase', padding: '6px 12px',
    borderBottom: active ? '2px solid var(--navy)' : '2px solid transparent',
    color: active ? 'var(--navy)' : 'var(--text-muted)',
  })

  return (
    <div style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '12px 16px 0', borderBottom: '1px solid var(--border)' }}>
        <p style={{ fontSize: 11, fontWeight: 500, color: 'var(--navy)', margin: '0 0 8px' }}>
          {selectedEmployeeName ? `Deliberating: ${selectedEmployeeName}` : 'All Deliberations'}
        </p>
        <div style={{ display: 'flex' }}>
          <button style={tabStyle(tab === 'proposals')} onClick={() => setTab('proposals')}>
            Proposals ({proposals.length})
          </button>
          <button style={tabStyle(tab === 'comments')} onClick={() => setTab('comments')}>
            Comments ({comments.length})
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {/* ── Proposals ── */}
        {tab === 'proposals' && (
          <>
            {proposals.length === 0 && (
              <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0 }}>No proposals yet.</p>
            )}
            {proposals.map(p => {
              const voterCount = Object.keys(p.votes).length
              const yesCount   = Object.values(p.votes).filter(v => v === 'yes').length
              const myVote     = p.votes[currentUser.display_name]
              const required   = session.participants.filter(pt => pt.role !== 'Observer')

              return (
                <div key={p.id} style={{
                  border: '1px solid var(--border)', borderRadius: 6,
                  padding: 12, marginBottom: 12,
                  backgroundColor: p.vote_result === 'passed' ? 'rgba(26,140,78,0.04)'
                    : p.vote_result === 'failed' ? 'rgba(100,100,100,0.04)' : 'transparent',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                    <div>
                      <OverrideChip type={p.override_type} />
                      <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--navy)', marginLeft: 8 }}>
                        {p.employee_name}
                      </span>
                    </div>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                      {fmtTime(p.timestamp)} by {p.proposed_by}
                    </span>
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--text-body)', margin: '0 0 8px', lineHeight: 1.5 }}>
                    {p.rationale}
                  </p>

                  {/* Objections */}
                  {p.objections.map((obj, i) => (
                    <div key={i} style={{ paddingLeft: 10, borderLeft: '2px solid #c8982a', marginBottom: 6 }}>
                      <span style={{ fontSize: 10, fontWeight: 600, color: '#c8982a' }}>{obj.objector}</span>
                      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>: {obj.reason}</span>
                    </div>
                  ))}

                  {/* Vote status */}
                  {p.vote_open && (
                    <div style={{ marginBottom: 8, padding: '8px 10px', backgroundColor: 'rgba(0,51,102,0.06)', borderRadius: 4 }}>
                      <p style={{ fontSize: 10, color: 'var(--navy)', margin: '0 0 6px', fontWeight: 600 }}>
                        Vote open — {voterCount}/{required.length} voted · {yesCount} Yes
                      </p>
                      {!myVote && !isObserver && (
                        <div style={{ display: 'flex', gap: 6 }}>
                          <button style={btnPrimary} onClick={() => vote(p.id, 'yes')}>Yes</button>
                          <button style={btnBase} onClick={() => vote(p.id, 'no')}>No</button>
                        </div>
                      )}
                      {myVote && <span style={{ fontSize: 10, color: '#1a8c4e' }}>You voted: {myVote}</span>}
                    </div>
                  )}
                  {p.vote_result && (
                    <div style={{ fontSize: 10, fontWeight: 600, color: p.vote_result === 'passed' ? '#1a8c4e' : '#888', marginBottom: 6 }}>
                      Vote {p.vote_result} · {yesCount}Y / {Object.keys(p.votes).length - yesCount}N
                      {p.applied && ' · Applied'}
                    </div>
                  )}

                  {/* Actions */}
                  {!isFinalized && !p.vote_result && (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {!p.vote_open && !isObserver && (
                        <>
                          {/* Objection input */}
                          <div style={{ display: 'flex', gap: 4, flex: 1 }}>
                            <input
                              style={{ flex: 1, ...{ border: '1px solid var(--border)', borderRadius: 4, padding: '3px 8px', fontSize: 10, fontFamily: 'var(--fb)', backgroundColor: 'var(--card-bg)', color: 'var(--text-body)' } }}
                              placeholder="Counter-rationale…"
                              value={objectionText[p.id] ?? ''}
                              onChange={e => setObjectionText(prev => ({ ...prev, [p.id]: e.target.value }))}
                            />
                            <button style={btnBase} onClick={() => submitObjection(p.id)}>Object</button>
                          </div>
                          {isOwner && (
                            <button style={btnGold} onClick={() => openVote(p.id)}>Call Vote</button>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </div>
              )
            })}

            {/* New proposal form */}
            {selectedEmployeeId && !isObserver && !isFinalized && (
              <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                <p style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>
                  New Proposal
                </p>
                <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                  {(['retain', 'exclude'] as const).map(t => (
                    <button key={t} style={{
                      ...btnBase, fontSize: 9,
                      backgroundColor: proposalType === t ? (t === 'retain' ? 'rgba(26,140,78,0.12)' : 'rgba(100,100,100,0.10)') : 'transparent',
                      color: proposalType === t ? (t === 'retain' ? '#1a8c4e' : '#666') : 'var(--text-muted)',
                    }} onClick={() => setProposalType(t)}>
                      {t === 'retain' ? 'Retain' : 'Under Review'}
                    </button>
                  ))}
                </div>
                <textarea
                  style={{
                    width: '100%', border: '1px solid var(--border)', borderRadius: 4,
                    padding: '6px 10px', fontFamily: 'var(--fb)', fontSize: 11,
                    backgroundColor: 'var(--card-bg)', color: 'var(--text-body)',
                    minHeight: 60, resize: 'vertical', boxSizing: 'border-box',
                  }}
                  placeholder="Rationale for this proposal…"
                  value={proposalText}
                  onChange={e => setProposalText(e.target.value)}
                />
                <button style={{ ...btnPrimary, marginTop: 6 }} onClick={submitProposal} disabled={busy}>
                  Submit Proposal
                </button>
              </div>
            )}
          </>
        )}

        {/* ── Comments ── */}
        {tab === 'comments' && (
          <>
            {comments.length === 0 && (
              <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0 }}>No comments yet.</p>
            )}
            {[...comments].reverse().map(c => (
              <div key={c.id} style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                  <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--navy)' }}>{c.author}</span>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                    {c.employee_name} · {fmtTime(c.timestamp)}
                  </span>
                </div>
                <p style={{ fontSize: 11, color: 'var(--text-body)', margin: 0, lineHeight: 1.5 }}>{c.body}</p>
              </div>
            ))}

            {selectedEmployeeId && !isObserver && !isFinalized && (
              <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                <textarea
                  style={{
                    width: '100%', border: '1px solid var(--border)', borderRadius: 4,
                    padding: '6px 10px', fontFamily: 'var(--fb)', fontSize: 11,
                    backgroundColor: 'var(--card-bg)', color: 'var(--text-body)',
                    minHeight: 50, resize: 'vertical', boxSizing: 'border-box',
                  }}
                  placeholder="Add a comment on this employee…"
                  value={commentText}
                  onChange={e => setCommentText(e.target.value)}
                />
                <button style={{ ...btnPrimary, marginTop: 6 }} onClick={submitComment} disabled={busy}>
                  Add Comment
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ── Finalization Panel ────────────────────────────────────────────────────────

function FinalizationPanel({
  session,
  currentUser,
  onRefresh,
}: {
  session:     DecisionSession
  currentUser: typeof PERSONAS[0]
  onRefresh:   () => void
}) {
  const [comment, setComment] = useState('')
  const [busy, setBusy]       = useState(false)

  const required = session.participants.filter(p => p.role !== 'Observer')
  const signedIds = new Set(session.sign_offs.map(s => s.user_id))
  const mySignOff = session.sign_offs.find(s => s.user_id === currentUser.user_id)
  const isObserver = currentUser.role === 'Observer'
  const openConflicts = session.conflicts.filter(c => !c.resolved)

  async function handleSignOff() {
    setBusy(true)
    try {
      await api.decisionRoom.signOff(session.session_id, currentUser.user_id, currentUser.display_name, comment)
      onRefresh()
    } finally { setBusy(false) }
  }

  return (
    <div style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 24 }}>
      <h3 style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16, fontWeight: 500 }}>
        Sign-Off Required
      </h3>

      {openConflicts.length > 0 && (
        <div style={{ padding: '10px 14px', backgroundColor: 'rgba(200,152,42,0.08)', borderRadius: 6, marginBottom: 16, fontSize: 11, color: '#c8982a' }}>
          ⚠ {openConflicts.length} conflict{openConflicts.length !== 1 ? 's' : ''} must be resolved before finalization.
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
        {required.map(p => {
          const signed = signedIds.has(p.user_id)
          const so     = session.sign_offs.find(s => s.user_id === p.user_id)
          return (
            <div key={p.user_id} style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '10px 14px', borderRadius: 6,
              backgroundColor: signed ? 'rgba(26,140,78,0.06)' : 'rgba(0,0,0,0.02)',
              border: `1px solid ${signed ? 'rgba(26,140,78,0.2)' : 'var(--border)'}`,
            }}>
              <span style={{ fontSize: 16 }}>{signed ? '✅' : '⬜'}</span>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-body)' }}>{p.display_name}</span>
                <RoleBadge role={p.role} />
                {so && <p style={{ fontSize: 10, color: 'var(--text-muted)', margin: '2px 0 0' }}>&ldquo;{so.comment}&rdquo;</p>}
              </div>
              {signed && <span style={{ fontSize: 10, color: '#1a8c4e' }}>{fmtDate(so!.timestamp)}</span>}
            </div>
          )
        })}
      </div>

      {session.status === 'Finalized' ? (
        <div style={{ padding: '12px 16px', backgroundColor: 'rgba(0,51,102,0.06)', borderRadius: 6, textAlign: 'center' }}>
          <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--navy)', margin: 0 }}>
            Session Finalized · Decision Record Locked
          </p>
        </div>
      ) : !isObserver && !mySignOff && openConflicts.length === 0 ? (
        <div>
          <textarea
            style={{
              width: '100%', border: '1px solid var(--border)', borderRadius: 4,
              padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 11,
              backgroundColor: 'var(--card-bg)', color: 'var(--text-body)',
              minHeight: 60, resize: 'vertical', boxSizing: 'border-box',
              marginBottom: 10,
            }}
            placeholder="Optional sign-off comment…"
            value={comment}
            onChange={e => setComment(e.target.value)}
          />
          <button style={btnPrimary} onClick={handleSignOff} disabled={busy}>
            {busy ? 'Signing…' : 'Sign Off'}
          </button>
        </div>
      ) : mySignOff ? (
        <p style={{ fontSize: 11, color: '#1a8c4e' }}>You signed off. Waiting for others.</p>
      ) : isObserver ? (
        <p style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>Observers cannot sign off.</p>
      ) : null}
    </div>
  )
}

// ── Session Workspace ─────────────────────────────────────────────────────────

function SessionWorkspace({
  session: initialSession,
  onBack,
  currentUser,
  allEmployees,
}: {
  session:      DecisionSession
  onBack:       () => void
  currentUser:  typeof PERSONAS[0]
  allEmployees: EmployeeRow[]
}) {
  const [session, setSession]   = useState(initialSession)
  const [search,  setSearch]    = useState('')
  const [selEmpId, setSelEmpId] = useState<string | null>(null)
  const [selEmpName, setSelEmpName] = useState<string | null>(null)
  const [tab, setTab]           = useState<'workspace' | 'finalize'>('workspace')
  const [busy, setBusy]         = useState(false)
  const pollRef                 = useRef<ReturnType<typeof setInterval> | null>(null)

  const refresh = useCallback(async () => {
    try {
      const updated = await api.decisionRoom.get(session.session_id)
      setSession(updated)
    } catch { /* ignore */ }
  }, [session.session_id])

  useEffect(() => {
    pollRef.current = setInterval(refresh, 3000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [refresh])

  const isObserver  = currentUser.role === 'Observer'
  const isOwner     = currentUser.role === 'Owner'
  const isFinalized = session.status === 'Finalized'

  const filtered = allEmployees.filter(e =>
    e.full_name.toLowerCase().includes(search.toLowerCase()) ||
    e.department.toLowerCase().includes(search.toLowerCase())
  )

  async function advanceStatus(next: DecisionSession['status']) {
    setBusy(true)
    try {
      const updated = await api.decisionRoom.updateStatus(session.session_id, next, currentUser.display_name)
      setSession(updated)
    } finally { setBusy(false) }
  }

  const statusFlow: Record<string, DecisionSession['status']> = {
    'Draft':   'Active',
    'Active':  'Under Review',
    'Under Review': 'Finalized',
  }
  const nextStatus = statusFlow[session.status]
  const canAdvance = isOwner && !isFinalized && !!nextStatus

  const tabStyle = (active: boolean): React.CSSProperties => ({
    background: 'none', border: 'none', cursor: 'pointer',
    fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '1.5px',
    textTransform: 'uppercase', padding: '8px 16px',
    borderBottom: active ? '2px solid var(--navy)' : '2px solid transparent',
    color: active ? 'var(--navy)' : 'var(--text-muted)',
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Session header */}
      <div style={{
        backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)',
        borderRadius: 8, padding: '14px 20px', marginBottom: 16,
        display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap',
      }}>
        <button style={{ ...btnBase, fontSize: 9 }} onClick={onBack}>← Sessions</button>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <h2 style={{ fontFamily: 'var(--fd)', fontSize: 18, fontWeight: 300, color: 'var(--navy)', margin: 0 }}>
              {session.name}
            </h2>
            <StatusBadge status={session.status} />
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            <span>Scenario {session.scenario.toUpperCase()} · {session.size}</span>
            <span>Budget target: {session.budget_pct}%</span>
            <span>{session.participants.length} participants</span>
            <span>{session.overrides.length} overrides</span>
            {session.conflicts.filter(c => !c.resolved).length > 0 && (
              <span style={{ color: '#c8982a' }}>
                ⚠ {session.conflicts.filter(c => !c.resolved).length} conflicts
              </span>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {canAdvance && (
            <button style={btnGold} onClick={() => advanceStatus(nextStatus!)} disabled={busy}>
              {busy ? '…' : `→ ${nextStatus}`}
            </button>
          )}
        </div>
      </div>

      {/* Tab bar */}
      <div style={{ borderBottom: '1px solid var(--border)', display: 'flex', gap: 0, marginBottom: 16 }}>
        <button style={tabStyle(tab === 'workspace')} onClick={() => setTab('workspace')}>
          Workspace
        </button>
        <button style={tabStyle(tab === 'finalize')} onClick={() => setTab('finalize')}>
          Sign-Off {session.sign_offs.length > 0 ? `(${session.sign_offs.length})` : ''}
        </button>
      </div>

      {tab === 'workspace' && (
        <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr 320px', gap: 14, flex: 1, minHeight: 0 }}>
          {/* Left: participants + activity */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0, overflowY: 'auto' }}>
            <ParticipantsPanel session={session} currentUser={currentUser} />
            <ActivityFeed session={session} />
          </div>

          {/* Center: employee workspace */}
          <div style={{ display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
            <ConflictBanner
              conflicts={session.conflicts}
              session={session}
              currentUser={currentUser}
              onRefresh={refresh}
            />
            <div style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--border)', display: 'flex', gap: 8 }}>
                <input
                  style={{
                    flex: 1, border: '1px solid var(--border)', borderRadius: 4,
                    padding: '5px 10px', fontFamily: 'var(--fb)', fontSize: 11,
                    backgroundColor: 'var(--card-bg)', color: 'var(--text-body)',
                  }}
                  placeholder="Search employees…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                />
                {!isObserver && !isFinalized && (
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', alignSelf: 'center', whiteSpace: 'nowrap' }}>
                    Click to deliberate
                  </span>
                )}
              </div>
              <div style={{ maxHeight: 520, overflowY: 'auto' }}>
                {filtered.slice(0, 50).map(emp => (
                  <EmployeeWorkspaceRow
                    key={emp.employee_id}
                    emp={emp}
                    session={session}
                    currentUser={currentUser}
                    isObserver={isObserver}
                    onRefresh={refresh}
                    onSelectForDeliberation={(id, name) => { setSelEmpId(id); setSelEmpName(name) }}
                    selectedId={selEmpId}
                  />
                ))}
                {filtered.length === 0 && (
                  <p style={{ padding: 16, fontSize: 11, color: 'var(--text-muted)' }}>No employees found.</p>
                )}
              </div>
            </div>
          </div>

          {/* Right: deliberation */}
          <div style={{ overflowY: 'auto' }}>
            <DeliberationPanel
              session={session}
              currentUser={currentUser}
              selectedEmployeeId={selEmpId}
              selectedEmployeeName={selEmpName}
              onRefresh={refresh}
            />
          </div>
        </div>
      )}

      {tab === 'finalize' && (
        <div style={{ maxWidth: 600 }}>
          <FinalizationPanel session={session} currentUser={currentUser} onRefresh={refresh} />

          {isFinalized && (
            <div style={{ marginTop: 20, backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
              <h3 style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 14, fontWeight: 500 }}>
                Decision Record Summary
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
                {[
                  ['Retain Overrides', session.overrides.filter(o => o.override_type === 'retain').length],
                  ['Review Overrides', session.overrides.filter(o => o.override_type === 'exclude').length],
                  ['Proposals Passed', session.proposals.filter(p => p.vote_result === 'passed').length],
                  ['Total Comments',   session.comments.length],
                  ['Votes Cast',       Object.values(session.proposals.reduce((acc, p) => ({ ...acc, ...p.votes }), {})).length],
                  ['Sign-offs',        session.sign_offs.length],
                ].map(([label, val]) => (
                  <div key={label as string} style={{ textAlign: 'center', padding: '10px 0' }}>
                    <p style={{ fontFamily: 'var(--fd)', fontSize: 24, fontWeight: 300, color: 'var(--navy)', margin: '0 0 4px' }}>
                      {val as number}
                    </p>
                    <p style={{ fontSize: 10, color: 'var(--text-muted)', margin: 0, fontFamily: 'var(--fb)', letterSpacing: '1px', textTransform: 'uppercase' }}>
                      {label as string}
                    </p>
                  </div>
                ))}
              </div>
              <p style={{ fontSize: 10, color: 'var(--text-muted)', fontStyle: 'italic', margin: 0 }}>
                This record is immutable. All overrides, deliberations, votes, and sign-offs have been preserved for compliance review.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function DecisionRoomPage() {
  const { scenario, size } = useDemoStore()
  const [sessions,     setSessions]     = useState<DecisionSession[]>([])
  const [activeSession, setActiveSession] = useState<DecisionSession | null>(null)
  const [employees,    setEmployees]    = useState<EmployeeRow[]>([])
  const [currentUser,  setCurrentUser]  = useState(PERSONAS[0])
  const [loading,      setLoading]      = useState(true)
  const [showCreate,   setShowCreate]   = useState(false)

  async function loadSessions() {
    try {
      const list = await api.decisionRoom.list()
      setSessions(list)
    } finally { setLoading(false) }
  }

  async function loadEmployees() {
    try {
      const dash = await api.dashboard.data(scenario, size)
      setEmployees(dash.employee_table)
    } catch { /* ignore */ }
  }

  useEffect(() => { loadSessions(); loadEmployees() }, [scenario, size])

  async function handleSeed() {
    setLoading(true)
    const s = await api.decisionRoom.seed(scenario, size)
    setSessions(prev => {
      const exists = prev.find(x => x.session_id === s.session_id)
      return exists ? prev.map(x => x.session_id === s.session_id ? s : x) : [s, ...prev]
    })
    // Auto-join as selected persona
    await api.decisionRoom.join(s.session_id, {
      user_id:      currentUser.user_id,
      display_name: currentUser.display_name,
      role:         currentUser.role,
    })
    const updated = await api.decisionRoom.get(s.session_id)
    setActiveSession(updated)
    setLoading(false)
  }

  async function handleSelect(id: string) {
    // Join the session as current persona
    await api.decisionRoom.join(id, {
      user_id:      currentUser.user_id,
      display_name: currentUser.display_name,
      role:         currentUser.role,
    })
    const updated = await api.decisionRoom.get(id)
    setActiveSession(updated)
  }

  async function handleCreated(s: DecisionSession) {
    setSessions(prev => [s, ...prev])
    setShowCreate(false)
    setActiveSession(s)
  }

  function handleBack() {
    setActiveSession(null)
    loadSessions()
  }

  return (
    <div style={{ padding: '28px 40px', maxWidth: 1440, margin: '0 auto', minHeight: '80vh' }}>
      {/* Persona switcher — always visible */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        marginBottom: 20,
        padding: '8px 14px',
        backgroundColor: 'rgba(0,51,102,0.04)',
        border: '1px solid var(--border)',
        borderRadius: 6,
      }}>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
          Simulating as
        </span>
        <div style={{ display: 'flex', gap: 6 }}>
          {PERSONAS.map(p => (
            <button
              key={p.user_id}
              onClick={() => setCurrentUser(p)}
              style={{
                ...btnBase,
                fontSize: 9,
                backgroundColor: currentUser.user_id === p.user_id ? 'var(--navy)' : 'transparent',
                color:           currentUser.user_id === p.user_id ? '#fff' : 'var(--text-muted)',
                border:          `1px solid ${currentUser.user_id === p.user_id ? 'var(--navy)' : 'var(--border)'}`,
              }}
            >
              {p.display_name}
            </button>
          ))}
        </div>
        <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 4 }}>
          · Switch personas to simulate multiple participants collaborating
        </span>
      </div>

      {activeSession ? (
        <SessionWorkspace
          session={activeSession}
          onBack={handleBack}
          currentUser={currentUser}
          allEmployees={employees}
        />
      ) : (
        <SessionListView
          sessions={sessions}
          onSelect={handleSelect}
          onSeed={handleSeed}
          onCreateNew={() => setShowCreate(true)}
          loading={loading}
        />
      )}

      {showCreate && (
        <CreateSessionDialog
          scenario={scenario}
          size={size}
          onCreated={handleCreated}
          onCancel={() => setShowCreate(false)}
        />
      )}
    </div>
  )
}
