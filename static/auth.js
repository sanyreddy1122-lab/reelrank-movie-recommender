const form = document.querySelector('#auth-form');
const nameField = document.querySelector('#name-field');
const nameInput = document.querySelector('#display-name');
const emailInput = document.querySelector('#email');
const passwordInput = document.querySelector('#password');
const errorMessage = document.querySelector('#auth-error');
const submitButton = document.querySelector('.auth-submit');
const authPanel = document.querySelector('.auth-panel');
const demoFillButton = document.querySelector('#demo-fill');
const demoCredentials = document.querySelector('.demo-credentials');
let mode = 'login';

function setMode(nextMode) {
  mode = nextMode;
  const registering = mode === 'register';
  authPanel.classList.toggle('is-register', registering);
  demoFillButton.hidden = registering;
  demoCredentials.hidden = registering;
  nameField.hidden = !registering;
  nameInput.required = registering;
  passwordInput.minLength = registering ? 10 : 1;
  passwordInput.placeholder = registering ? 'At least 10 characters' : 'Your password';
  passwordInput.autocomplete = registering ? 'new-password' : 'current-password';
  document.querySelector('#auth-title').textContent = registering ? 'Make it yours.' : 'Welcome back.';
  document.querySelector('#auth-subtitle').textContent = registering
    ? 'Create an account to keep your movie taste in sync.'
    : 'Sign in to your ReelRank account.';
  document.querySelector('#submit-label').textContent = registering ? 'Create account' : 'Sign in';
  document.querySelector('#login-tab').classList.toggle('active', !registering);
  document.querySelector('#register-tab').classList.toggle('active', registering);
  document.querySelector('#login-tab').setAttribute('aria-selected', String(!registering));
  document.querySelector('#register-tab').setAttribute('aria-selected', String(registering));
  errorMessage.textContent = '';
}

document.querySelector('#login-tab').addEventListener('click', () => setMode('login'));
document.querySelector('#register-tab').addEventListener('click', () => setMode('register'));
demoFillButton.addEventListener('click', () => {
  emailInput.value = 'demo@example.com';
  passwordInput.value = 'ReelRankDemo2026!';
  emailInput.dispatchEvent(new Event('input', { bubbles: true }));
  passwordInput.dispatchEvent(new Event('input', { bubbles: true }));
  emailInput.focus();
  demoFillButton.setAttribute('aria-label', 'Demo account details filled in. Submit the form to sign in.');
  document.querySelector('#submit-label').textContent = 'Sign in to demo';
});
document.querySelector('#password-toggle').addEventListener('click', (event) => {
  const reveal = passwordInput.type === 'password';
  passwordInput.type = reveal ? 'text' : 'password';
  event.currentTarget.textContent = reveal ? 'Hide' : 'Show';
  event.currentTarget.setAttribute('aria-label', reveal ? 'Hide password' : 'Show password');
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  errorMessage.textContent = '';
  if (!form.reportValidity()) return;
  if (mode === 'register' && passwordInput.value.length < 10) {
    errorMessage.textContent = 'Choose a password with at least 10 characters.';
    passwordInput.focus();
    return;
  }
  if (mode === 'register' && !nameInput.value.trim()) {
    errorMessage.textContent = 'Add your name to create an account.';
    nameInput.focus();
    return;
  }

  const registering = mode === 'register';
  const payload = {
    email: emailInput.value.trim(),
    password: passwordInput.value,
  };
  if (registering) {
    payload.display_name = nameInput.value.trim();
    payload.legacy_user_id = localStorage.getItem('reelrank-user-id') || undefined;
  }
  submitButton.disabled = true;
  document.querySelector('#submit-label').textContent = registering ? 'Creating your account…' : 'Signing you in…';
  try {
    const response = await fetch(registering ? '/api/auth/register' : '/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) {
      const detail = typeof result.detail === 'string' ? result.detail : result.detail?.[0]?.msg;
      throw new Error(detail || 'We could not sign you in. Please try again.');
    }
    localStorage.removeItem('reelrank-user-id');
    localStorage.removeItem('reelrank-liked');
    localStorage.removeItem('reelrank-likes-migrated');
    window.location.replace('/');
  } catch (error) {
    errorMessage.textContent = error.message || 'Could not reach ReelRank. Check your connection and retry.';
    submitButton.disabled = false;
    document.querySelector('#submit-label').textContent = registering ? 'Create account' : 'Sign in';
  }
});
