import { useRef, useState } from 'react';
import { saveSession, submitPassword, signup as createAccount } from '../services/api';

export default function AuthPage({ onContinue, sessionNotice = '' }) {
  const [mode, setMode] = useState('login');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const signup = mode === 'signup';
  const [notice, setNotice] = useState(sessionNotice);
  const [pending, setPending] = useState(false);
  const busy = useRef(false);
  function switchMode() {
    if (busy.current) return;
    setNotice('');
    setMode(signup ? 'login' : 'signup');
    setShowPassword(false);
    setError('');
  }

  async function submit(event) {
    event.preventDefault();
    if (busy.current) return;
    const data = new FormData(event.currentTarget);
    const name = String(data.get('name') || '').trim();
    const email = String(data.get('email') || '').trim();
    if (signup && !name) return setError('Please enter your name.');
    if (signup && data.get('password') !== data.get('confirmPassword')) {
      return setError('Your passwords don’t match. Please try again.');
    }
    const password = String(data.get('password') || '');

    busy.current = true;
    setPending(true);
    setError('');
    setNotice('');
    try {
      const result = signup 
        ? await createAccount(name, email, password)
        : await submitPassword(email, password);

        if (result.requires_confirmation) {
          setNotice(result.message);
          return;
        }
      saveSession(result);
      onContinue(result.user);
    } catch (error) {
      setError(error.message);
    } finally {
      busy.current = false;
      setPending(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-story" aria-label="About Document chat">
        <a className="auth-brand" href="#" onClick={(event) => { event.preventDefault(); if (busy.current) return; setMode('login'); setError(''); setNotice(''); setShowPassword(false); }}><span className="brand-mark" aria-hidden="true">D</span>Document chat</a>
        <div className="auth-story-content">
          <span className="auth-eyebrow">YOUR KNOWLEDGE, CONNECTED</span>
          <h1>Good questions.<br />Clear answers.</h1>
          <p>Turn your documents into a conversation. Find what you need, with the sources to back it up.</p>
          <div className="auth-preview" aria-hidden="true">
            <div className="preview-file"><span>▤</span> Employee handbook <span>MD</span></div>
            <div className="preview-question">What’s our remote work policy?</div>
            <div className="preview-answer"><span className="preview-dot" />Answers grounded in your documents.</div>
            <div className="preview-lines"><span /><span /><span /></div>
            <span className="preview-source">↗ Source included</span>
          </div>
        </div>
        <p className="auth-story-footer">Less searching. More understanding.</p>
      </section>
      <section className="auth-form-panel" aria-labelledby="auth-title">
        <div className="auth-form-container">
          <span className="auth-eyebrow">LET’S GET STARTED</span>
          <h2 id="auth-title">{signup ? 'Create your account' : 'Welcome back'}</h2>
          <p className="auth-subtitle">{signup ? 'A new home for your documents and ideas.' : 'Your documents. Your questions. Pick up here.'}</p>
          <form key={mode} aria-busy={pending} onSubmit={submit} className="auth-form" onChange={() => setError('')}>
            {signup && <label htmlFor="auth-name">Full name<input id="auth-name" name="name" autoComplete="name" placeholder="Alex Morgan" required maxLength={80} /></label>}
            <label htmlFor="auth-email">Email address<input id="auth-email" name="email" type="email" autoComplete="email" placeholder="you@example.com" required /></label>
            <label htmlFor="auth-password">Password<span className="password-field"><input id="auth-password" name="password" type={showPassword ? 'text' : 'password'} autoComplete={signup ? 'new-password' : 'current-password'} placeholder={signup ? 'Create a password' : 'Enter your password'} required minLength={signup ? 8 : undefined} aria-describedby={signup ? 'password-hint' : undefined} /><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>{showPassword ? 'Hide' : 'Show'}</button></span></label>
            {signup && <><p id="password-hint" className="password-hint">Use at least 8 characters.</p><label htmlFor="auth-confirm">Confirm password<input id="auth-confirm" name="confirmPassword" type={showPassword ? 'text' : 'password'} autoComplete="new-password" placeholder="Re-enter your password" required /></label></>}
            {error && <p className="auth-error" role="alert">{error}</p>}
            {notice && <p role="status">{notice}</p>}
            <button className="auth-submit" type="submit" disabled={pending}>{pending ? 'Please wait…' : signup ? 'Create account' : 'Log in'}<span aria-hidden="true">→</span></button>
          </form>
          <p className="auth-switch">{signup ? 'Already have an account?' : 'New to Document chat?'} <button type="button" disabled={pending} onClick={switchMode}>{signup ? 'Log in' : 'Sign up'}</button></p>
          <p className="auth-note">Your documents and answers are connected to your account.</p>
        </div>
      </section>
    </main>
  );
}
