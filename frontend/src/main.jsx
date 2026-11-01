import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
function App() {
  const [token, setToken] = useState(localStorage.getItem('playledger_token') || '');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');
  const [wallet, setWallet] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [adminRecipient, setAdminRecipient] = useState('');
  const [adminAmount, setAdminAmount] = useState('');
  const [reconciliation, setReconciliation] = useState(null);

  async function api(path, options = {}) {
    const response = await fetch(`${API}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Token ${token}` } : {}), ...(options.headers || {}) } });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || JSON.stringify(data) || `HTTP ${response.status}`);
    return data;
  }
  async function login(event) {
    event.preventDefault(); setBusy(true); setMessage('');
    try { const result = await api('/auth/login/', { method: 'POST', body: JSON.stringify({ username, password }) }); localStorage.setItem('playledger_token', result.token); setToken(result.token); setMessage('Signed in successfully.'); }
    catch (error) { setMessage(error.message); } finally { setBusy(false); }
  }
  async function register(event) {
    event.preventDefault(); setBusy(true); setMessage('');
    try { const result = await api('/auth/register/', { method: 'POST', body: JSON.stringify({ username, password }) }); localStorage.setItem('playledger_token', result.token); setToken(result.token); setMessage('Account created. Your wallet is ready.'); }
    catch (error) { setMessage(error.message); } finally { setBusy(false); }
  }
  async function refresh() {
    if (!token) return;
    try { const [w, t, me] = await Promise.all([api('/wallet/'), api('/transactions/'), api('/auth/me/')]); setWallet(w); setTransactions(t); setCurrentUser(me); }
    catch (error) { setMessage(error.message); }
  }
  useEffect(() => { refresh(); }, [token]);
  async function transfer(event) {
    event.preventDefault(); setBusy(true); setMessage('');
    try {
      const key = crypto.randomUUID();
      const result = await api('/transfers/', { method: 'POST', headers: { 'Idempotency-Key': key }, body: JSON.stringify({ recipient_id: Number(recipient), amount: Number(amount) }) });
      setMessage(`Transfer posted: ${result.transaction.id}`); setRecipient(''); setAmount(''); await refresh();
    } catch (error) { setMessage(error.message); } finally { setBusy(false); }
  }
  async function issueCredits(event) {
    event.preventDefault(); setBusy(true); setMessage('');
    try { const result = await api('/admin/credits/issue/', { method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify({ recipient_id: Number(adminRecipient), amount: Number(adminAmount), description: 'Admin-issued demo credits' }) }); setMessage(`Credits issued: ${result.transaction.id}`); setAdminRecipient(''); setAdminAmount(''); await refresh(); }
    catch (error) { setMessage(error.message); } finally { setBusy(false); }
  }
  async function runReconciliation() { setBusy(true); setMessage(''); try { const result = await api('/admin/reconciliation/'); setReconciliation(result); setMessage(`Reconciliation: ${result.status}`); } catch (error) { setMessage(error.message); } finally { setBusy(false); } }
  function logout() { localStorage.removeItem('playledger_token'); setToken(''); setWallet(null); setTransactions([]); setCurrentUser(null); setReconciliation(null); setMessage('Signed out.'); }

  return <main className="shell">
    <header className="topbar"><div className="brand-mark">PL</div><div><h1>PlayLedger</h1><p>Virtual credits · Transaction integrity demo</p></div>{token && <button className="secondary logout" onClick={logout}>Sign out</button>}</header>
    {message && <div className="notice" role="status">{message}</div>}
    {!token ? <section className="auth-grid"><div className="hero"><span className="eyebrow">LEARN FINANCIAL BACKENDS</span><h2>Every credit has a traceable story.</h2><p>Explore a demo wallet backed by an append-only, double-entry ledger. Use virtual credits only.</p><div className="feature-line"><span>✓ Atomic transfers</span><span>✓ Auditable history</span><span>✓ Idempotent requests</span></div></div><form className="panel auth-form" onSubmit={login}><h2>Welcome back</h2><p>Sign in or create a demo account.</p><label>Username<input value={username} onChange={e => setUsername(e.target.value)} required autoComplete="username"/></label><label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength="8" autoComplete="current-password"/></label><button disabled={busy}>{busy ? 'Please wait…' : 'Sign in'}</button><button className="secondary" type="button" disabled={busy} onClick={register}>Create account</button><small>Demo note: newly registered wallets start with 0 credits. An administrator must issue demo credits.</small></form></section> : <>
      <section className="summary-grid"><article className="panel balance-card"><span className="eyebrow">AVAILABLE BALANCE</span><div className="balance">{wallet?.available_credits ?? '—'} <small>credits</small></div><p>Integer units · No real monetary value</p></article><article className="panel"><span className="eyebrow">ACCOUNT</span><h3>{wallet?.name || 'Loading wallet…'}</h3><p>Status: <span className="status">{wallet?.status || '—'}</span></p><p>Your user ID (share to receive credits): {wallet?.user_id ?? '—'}</p></article></section>
      <section className="content-grid"><form className="panel" onSubmit={transfer}><span className="eyebrow">PEER-TO-PEER</span><h2>Transfer credits</h2><p>Use the recipient's numeric user ID.</p><label>Recipient user ID<input type="number" min="1" value={recipient} onChange={e => setRecipient(e.target.value)} required/></label><label>Amount (whole credits)<input type="number" min="1" step="1" value={amount} onChange={e => setAmount(e.target.value)} required/></label><button disabled={busy}>{busy ? 'Processing…' : 'Transfer credits'}</button><small>A unique idempotency key is generated for each submit. The server validates funds and locks account rows.</small></form>
      <section className="panel history"><div className="section-heading"><div><span className="eyebrow">AUDIT TRAIL</span><h2>Recent transactions</h2></div><button className="secondary" onClick={refresh}>Refresh</button></div>{transactions.length === 0 ? <div className="empty">No transactions yet. Your transaction history will appear here.</div> : <div className="table-wrap"><table><thead><tr><th>Transaction</th><th>Type</th><th>Date</th><th>Entries</th></tr></thead><tbody>{transactions.map(t => <tr key={t.id}><td><code>{t.id.slice(0, 8)}…</code></td><td><span className="pill">{t.kind}</span></td><td>{new Date(t.created_at).toLocaleString()}</td><td>{t.entries?.map(e => `${e.account_name}: ${e.amount_minor > 0 ? '+' : ''}${e.amount_minor}`).join(' · ')}</td></tr>)}</tbody></table></div>}</section></section>
      {currentUser?.is_staff && <section className="admin-grid"><form className="panel" onSubmit={issueCredits}><span className="eyebrow">STAFF CONTROLS</span><h2>Issue demo credits</h2><p>Restricted to staff accounts. This never moves real money.</p><label>Recipient user ID<input type="number" min="1" value={adminRecipient} onChange={e => setAdminRecipient(e.target.value)} required /></label><label>Credits to issue<input type="number" min="1" step="1" value={adminAmount} onChange={e => setAdminAmount(e.target.value)} required /></label><button disabled={busy}>{busy ? 'Processing…' : 'Issue virtual credits'}</button></form><div className="panel"><span className="eyebrow">INTEGRITY CHECK</span><h2>Ledger reconciliation</h2><p>Checks posted transaction totals and cached balances against ledger entries.</p><button onClick={runReconciliation} disabled={busy}>{busy ? 'Checking…' : 'Run reconciliation'}</button>{reconciliation && <pre className="report">{JSON.stringify(reconciliation, null, 2)}</pre>}</div></section>}
    </>}
    <footer>PlayLedger · Educational software · No real-money functionality</footer>
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);
