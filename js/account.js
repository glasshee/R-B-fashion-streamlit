const accountForm = document.querySelector('#accountForm');
const accountStatus = document.querySelector('#accountStatus');
const accountNameField = document.querySelector('#accountNameField');
const accountNameInput = document.querySelector('#accountName');
const accountPasswordInput = document.querySelector('#accountPassword');
const accountSubmit = document.querySelector('#accountSubmit');
const accountModeToggle = document.querySelector('#accountModeToggle');
const accountHeading = document.querySelector('#accountHeading');
const accountIntro = document.querySelector('#accountIntro');
const googleButton = document.querySelector('#googleButton');
const googleSetupStatus = document.querySelector('#googleSetupStatus');
const accountStorageKey = 'rb-account';
const apiUrl = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000/api' : '/api';
let accountMode = 'register';
let isAuthenticating = false;
let googleNonce = '';

let hasStoredAccount = false;
try {
  hasStoredAccount = Boolean(JSON.parse(localStorage.getItem(accountStorageKey) || 'null'));
} catch {
  localStorage.removeItem(accountStorageKey);
}

if (hasStoredAccount) {
  window.location.href = 'index.html';
}

accountModeToggle.addEventListener('click', () => {
  accountMode = accountMode === 'register' ? 'login' : 'register';
  const isRegistering = accountMode === 'register';
  accountNameField.hidden = !isRegistering;
  accountNameInput.required = isRegistering;
  accountPasswordInput.autocomplete = isRegistering ? 'new-password' : 'current-password';
  accountSubmit.textContent = isRegistering ? 'Create account with email' : 'Sign in with email';
  accountHeading.textContent = isRegistering ? 'Create your account' : 'Welcome back';
  accountIntro.textContent = isRegistering
    ? 'Create an account to save your bag and order details.'
    : 'Sign in to continue to your R&B Fashion account.';
  accountModeToggle.textContent = isRegistering
    ? 'Already have an account? Sign in'
    : 'New to R&B Fashion? Create an account';
  accountStatus.textContent = '';
});

function makeNonce() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

function showAccountError(message) {
  accountStatus.style.color = '#a12620';
  accountStatus.textContent = message;
}

function finishSignIn(result) {
  localStorage.setItem(accountStorageKey, JSON.stringify({ ...result.user, token: result.token }));
  accountStatus.style.color = '#28643b';
  accountStatus.textContent = `Welcome, ${result.user.name}. Opening R&B Fashion...`;
  setTimeout(() => { window.location.href = 'index.html'; }, 450);
}

async function setupGoogleSignIn() {
  try {
    const configResponse = await fetch(`${apiUrl}/auth/google/config`);
    const config = await configResponse.json();
    if (!configResponse.ok) throw new Error(config.error || 'Could not load Google sign-in settings.');
    if (!config.clientId) {
      googleSetupStatus.textContent = 'Google sign-in is not set up yet. You can still continue with email.';
      googleSetupStatus.hidden = false;
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onerror = () => {
      googleSetupStatus.textContent = 'Google sign-in could not load. You can continue with email.';
      googleSetupStatus.hidden = false;
    };
    script.onload = () => {
      googleNonce = makeNonce();
      window.google.accounts.id.initialize({
        client_id: config.clientId,
        nonce: googleNonce,
        callback: async ({ credential }) => {
          if (isAuthenticating) return;
          isAuthenticating = true;
          accountStatus.textContent = 'Verifying your Google account...';
          try {
            const response = await fetch(`${apiUrl}/auth/google`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ credential, nonce: googleNonce })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Google sign-in failed.');
            finishSignIn(result);
          } catch (error) {
            showAccountError(error.message.includes('fetch')
              ? 'Could not reach the sign-in service. Please try again.'
              : error.message);
          } finally {
            isAuthenticating = false;
          }
        }
      });
      window.google.accounts.id.renderButton(googleButton, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'continue_with',
        shape: 'rectangular',
        width: Math.min(360, Math.floor(googleButton.getBoundingClientRect().width))
      });
    };
    document.head.appendChild(script);
  } catch {
    googleSetupStatus.textContent = 'Google sign-in is unavailable. You can continue with email.';
    googleSetupStatus.hidden = false;
  }
}

accountForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (isAuthenticating) return;
  const formData = new FormData(accountForm);
  const registering = accountMode === 'register';
  const payload = {
    email: formData.get('email').trim(),
    password: formData.get('password')
  };
  if (registering) payload.name = formData.get('name').trim();

  isAuthenticating = true;
  accountSubmit.disabled = true;
  accountStatus.textContent = 'Please wait...';
  try {
    const response = await fetch(`${apiUrl}${registering ? '/accounts' : '/auth/login'}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || (registering ? 'Account creation failed' : 'Sign in failed'));
    finishSignIn(result);
  } catch (error) {
    showAccountError(error.message.includes('fetch')
      ? 'Sign-in service unavailable. Open this page through the running website and try again.'
      : error.message);
  } finally {
    isAuthenticating = false;
    accountSubmit.disabled = false;
  }
});

setupGoogleSignIn();
