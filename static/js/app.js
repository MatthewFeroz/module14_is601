"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  setSessionNavigation();
  bindPasswordToggles();

  if (page === "register") setupRegistration();
  if (page === "login") setupLogin();
  if (page === "dashboard") loadDashboard();
});

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const specialPattern = /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/;

function setSessionNavigation() {
  const link = document.querySelector("[data-auth-link]");
  if (link && localStorage.getItem("access_token")) {
    link.textContent = "Workspace";
    link.href = "/dashboard";
  }
}

function bindPasswordToggles() {
  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.passwordToggle);
      const reveal = input.type === "password";
      input.type = reveal ? "text" : "password";
      button.textContent = reveal ? "Hide" : "Show";
      button.setAttribute("aria-label", `${reveal ? "Hide" : "Show"} password`);
    });
  });
}

function showAlert(type, message) {
  const alert = document.getElementById("formAlert");
  alert.className = `form-alert ${type}`;
  alert.textContent = message;
  alert.hidden = false;
  alert.focus({ preventScroll: true });
}

function clearValidation(form) {
  form.querySelectorAll("[aria-invalid]").forEach((input) => {
    input.removeAttribute("aria-invalid");
  });
  form.querySelectorAll(".field-error").forEach((error) => {
    error.textContent = "";
  });
  const alert = document.getElementById("formAlert");
  alert.hidden = true;
}

function setFieldError(inputId, message) {
  const input = document.getElementById(inputId);
  const error = document.querySelector(`[data-error-for="${inputId}"]`);
  input.setAttribute("aria-invalid", "true");
  error.textContent = message;
}

function setLoading(form, isLoading) {
  const button = form.querySelector("[type='submit']");
  button.disabled = isLoading;
  button.classList.toggle("loading", isLoading);
}

async function responseError(response) {
  let data;
  try {
    data = await response.json();
  } catch {
    return "The server returned an unexpected response";
  }
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((item) => item.msg.replace(/^Value error, /, "")).join(". ");
  }
  return "The request could not be completed";
}

function passwordChecks(password) {
  return {
    length: password.length >= 8 && new TextEncoder().encode(password).length <= 72,
    upper: /[A-Z]/.test(password),
    lower: /[a-z]/.test(password),
    number: /\d/.test(password),
    special: specialPattern.test(password),
  };
}

function updatePasswordRequirements(password) {
  const checks = passwordChecks(password);
  Object.entries(checks).forEach(([name, met]) => {
    document.querySelector(`[data-requirement="${name}"]`)?.classList.toggle("met", met);
  });
  return Object.values(checks).every(Boolean);
}

function validateRegistration(data) {
  let valid = true;
  if (!data.first_name) {
    setFieldError("firstName", "Enter your first name.");
    valid = false;
  }
  if (!data.last_name) {
    setFieldError("lastName", "Enter your last name.");
    valid = false;
  }
  if (!emailPattern.test(data.email)) {
    setFieldError("registerEmail", "Enter a valid email address.");
    valid = false;
  }
  if (!/^[A-Za-z0-9_.-]{3,50}$/.test(data.username)) {
    setFieldError("registerUsername", "Use 3–50 allowed characters.");
    valid = false;
  }
  if (!updatePasswordRequirements(data.password)) {
    setFieldError(
      "registerPassword",
      "Use 8–72 characters with uppercase, lowercase, number, and special character.",
    );
    valid = false;
  }
  if (data.password !== data.confirm_password) {
    setFieldError("confirmPassword", "Passwords do not match.");
    valid = false;
  }
  return valid;
}

function setupRegistration() {
  const form = document.getElementById("registrationForm");
  const password = document.getElementById("registerPassword");
  password.addEventListener("input", () => updatePasswordRequirements(password.value));

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearValidation(form);
    const data = Object.fromEntries(new FormData(form).entries());
    Object.keys(data).forEach((key) => {
      if (
        typeof data[key] === "string"
        && key !== "password"
        && key !== "confirm_password"
      ) {
        data[key] = data[key].trim();
      }
    });

    if (!validateRegistration(data)) {
      showAlert("error", "Please correct the highlighted registration fields.");
      return;
    }

    setLoading(form, true);
    try {
      const response = await fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error(await responseError(response));
      showAlert("success", "Registration successful. Redirecting you to sign in…");
      form.reset();
      updatePasswordRequirements("");
      window.setTimeout(() => window.location.assign("/login"), 1200);
    } catch (error) {
      showAlert("error", error.message || "Registration failed");
    } finally {
      setLoading(form, false);
    }
  });
}

function setupLogin() {
  const form = document.getElementById("loginForm");
  const remembered = localStorage.getItem("remembered_identifier");
  if (remembered) {
    form.elements.identifier.value = remembered;
    form.elements.remember.checked = true;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearValidation(form);
    const identifier = form.elements.identifier.value.trim();
    const password = form.elements.password.value;
    let valid = true;

    if (identifier.length < 3) {
      setFieldError("loginIdentifier", "Enter your email or username.");
      valid = false;
    }
    if (password.length < 8) {
      setFieldError("loginPassword", "Enter your password.");
      valid = false;
    }
    if (!valid) {
      showAlert("error", "Enter both login fields.");
      return;
    }

    setLoading(form, true);
    try {
      const response = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier, password }),
      });
      if (!response.ok) throw new Error(await responseError(response));
      const token = await response.json();
      localStorage.setItem("access_token", token.access_token);
      localStorage.setItem("token_type", token.token_type);
      localStorage.setItem("token_expires_at", token.expires_at);
      localStorage.setItem("user", JSON.stringify(token.user));
      if (form.elements.remember.checked) {
        localStorage.setItem("remembered_identifier", identifier);
      } else {
        localStorage.removeItem("remembered_identifier");
      }
      showAlert("success", "Login successful. Opening your secure workspace…");
      window.setTimeout(() => window.location.assign("/dashboard"), 650);
    } catch (error) {
      showAlert("error", error.message || "Invalid credentials");
    } finally {
      setLoading(form, false);
    }
  });
}

async function loadDashboard() {
  const token = localStorage.getItem("access_token");
  if (!token) {
    window.location.replace("/login");
    return;
  }

  const card = document.querySelector("[data-identity-card]");
  try {
    const response = await fetch("/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error("Your session is invalid or has expired");
    const user = await response.json();
    const initials = `${user.first_name[0]}${user.last_name[0]}`.toUpperCase();
    card.innerHTML = `
      <div class="panel-heading"><p>BEARER PROFILE</p><span>AUTHORIZED</span></div>
      <div class="identity-profile">
        <div class="identity-monogram" aria-hidden="true">${initials}</div>
        <div>
          <h2>Welcome, ${escapeHtml(user.first_name)}.</h2>
          <p>@${escapeHtml(user.username)} · ${escapeHtml(user.email)}</p>
          <div class="identity-meta">
            <span>JWT verified</span><span>Account active</span>
          </div>
          <button class="logout-button" type="button" data-logout>Sign out and clear token</button>
        </div>
      </div>`;
    card.querySelector("[data-logout]").addEventListener("click", logout);
  } catch (error) {
    localStorage.removeItem("access_token");
    card.innerHTML = `
      <div class="panel-heading"><p>BEARER PROFILE</p><span>DENIED</span></div>
      <div class="identity-loading">
        <p>${escapeHtml(error.message)}.</p><a href="/login">Return to sign in →</a>
      </div>`;
  }
}

function logout() {
  ["access_token", "token_type", "token_expires_at", "user"].forEach((key) => {
    localStorage.removeItem(key);
  });
  window.location.assign("/login");
}

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value;
  return element.innerHTML;
}
