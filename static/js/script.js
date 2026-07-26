(function initializeCalculationUI(global) {
  "use strict";

  const OPERATORS = {
    addition: "+",
    subtraction: "−",
    multiplication: "×",
    division: "÷",
  };

  function parseCalculationInputs(rawValue) {
    const parts = String(rawValue)
      .split(",")
      .map((part) => part.trim());

    if (parts.length < 2) {
      return {
        valid: false,
        values: [],
        error: "Enter at least two numbers separated by commas.",
      };
    }

    if (parts.some((part) => part === "")) {
      return {
        valid: false,
        values: [],
        error: "Every input must contain a number.",
      };
    }

    const values = parts.map(Number);
    if (values.some((value) => !Number.isFinite(value))) {
      return {
        valid: false,
        values: [],
        error: "Every input must be a valid number.",
      };
    }

    return { valid: true, values, error: null };
  }

  function validateCalculationInputs(rawValue, operation) {
    const parsed = parseCalculationInputs(rawValue);
    if (!parsed.valid) return parsed;

    if (
      operation === "division" &&
      parsed.values.slice(1).some((value) => value === 0)
    ) {
      return {
        valid: false,
        values: [],
        error: "Division by zero is not allowed.",
      };
    }

    return parsed;
  }

  function calculatePreview(operation, values) {
    switch (operation) {
      case "addition":
        return values.reduce((result, value) => result + value, 0);
      case "subtraction":
        return values.slice(1).reduce(
          (result, value) => result - value,
          values[0],
        );
      case "multiplication":
        return values.reduce((result, value) => result * value, 1);
      case "division":
        return values.slice(1).reduce(
          (result, value) => result / value,
          values[0],
        );
      default:
        throw new Error("Unsupported calculation type.");
    }
  }

  global.CalculationUI = {
    calculatePreview,
    parseCalculationInputs,
    validateCalculationInputs,
  };

  if (typeof document === "undefined") return;

  const token = () => global.localStorage.getItem("access_token");

  function clearSession() {
    const rememberedIdentifier =
      global.localStorage.getItem("remembered_identifier");
    global.localStorage.clear();
    if (rememberedIdentifier) {
      global.localStorage.setItem(
        "remembered_identifier",
        rememberedIdentifier,
      );
    }
  }

  function showAlert(message, type = "error") {
    const alert = document.getElementById("formAlert");
    if (!alert) return;
    alert.textContent = message;
    alert.className = `form-alert ${type}`;
    alert.hidden = false;
    alert.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function clearAlert() {
    const alert = document.getElementById("formAlert");
    if (alert) {
      alert.hidden = true;
      alert.textContent = "";
      alert.className = "form-alert";
    }
  }

  async function authorizedFetch(url, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Authorization", `Bearer ${token()}`);
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) {
      clearSession();
      global.location.replace("/login");
      throw new Error("Your session expired. Please sign in again.");
    }
    return response;
  }

  async function responseError(response, fallback) {
    const body = await response.json().catch(() => ({}));
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail.length) {
      return body.detail[0].msg || fallback;
    }
    return fallback;
  }

  function requireSession() {
    if (!token()) {
      global.location.replace("/login");
      return false;
    }
    return true;
  }

  function configureNavigation() {
    const authLink = document.querySelector("[data-auth-link]");
    if (authLink && token()) {
      authLink.href = "/dashboard";
      authLink.textContent = "Workspace";
    }

    document.querySelectorAll("[data-logout]").forEach((button) => {
      button.addEventListener("click", () => {
        clearSession();
        global.location.assign("/login");
      });
    });

    document.querySelectorAll("[data-password-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const input = document.getElementById(button.dataset.passwordToggle);
        const showPassword = input.type === "password";
        input.type = showPassword ? "text" : "password";
        button.textContent = showPassword ? "Hide" : "Show";
        button.setAttribute(
          "aria-label",
          `${showPassword ? "Hide" : "Show"} password`,
        );
      });
    });
  }

  function configureRegistration() {
    const form = document.getElementById("registrationForm");
    if (!form) return;

    const password = form.elements.password;
    const confirmPassword = form.elements.confirm_password;
    const requirements = {
      length: (value) => value.length >= 8 && value.length <= 72,
      upper: (value) => /[A-Z]/.test(value),
      lower: (value) => /[a-z]/.test(value),
      number: (value) => /\d/.test(value),
      special: (value) => /[^A-Za-z0-9]/.test(value),
    };

    function updateRequirements() {
      Object.entries(requirements).forEach(([name, check]) => {
        document
          .querySelector(`[data-requirement="${name}"]`)
          ?.classList.toggle("met", check(password.value));
      });
    }

    password.addEventListener("input", updateRequirements);
    updateRequirements();

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearAlert();

      const payload = Object.fromEntries(new FormData(form).entries());
      const failedRequirement = Object.values(requirements).some(
        (check) => !check(payload.password),
      );

      if (!form.checkValidity()) {
        showAlert("Complete every field using the requested format.");
        form.reportValidity();
        return;
      }
      if (failedRequirement) {
        showAlert("Password does not meet every security requirement.");
        password.focus();
        return;
      }
      if (payload.password !== payload.confirm_password) {
        showAlert("Passwords do not match.");
        confirmPassword.focus();
        return;
      }

      const submit = form.querySelector('[type="submit"]');
      submit.disabled = true;
      submit.classList.add("loading");

      try {
        const response = await fetch("/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          throw new Error(await responseError(response, "Registration failed."));
        }
        showAlert("Account created. Taking you to sign in…", "success");
        global.setTimeout(() => global.location.assign("/login"), 450);
      } catch (error) {
        showAlert(error.message);
        submit.disabled = false;
        submit.classList.remove("loading");
      }
    });
  }

  function configureLogin() {
    const form = document.getElementById("loginForm");
    if (!form) return;

    const remembered = global.localStorage.getItem("remembered_identifier");
    if (remembered) {
      form.elements.username.value = remembered;
      form.elements.remember.checked = true;
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearAlert();
      if (!form.checkValidity()) {
        showAlert("Enter your username or email and password.");
        form.reportValidity();
        return;
      }

      const submit = form.querySelector('[type="submit"]');
      submit.disabled = true;
      submit.classList.add("loading");
      const payload = {
        identifier: form.elements.username.value.trim(),
        password: form.elements.password.value,
      };

      try {
        const response = await fetch("/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          throw new Error(
            await responseError(response, "Invalid username or password."),
          );
        }

        const session = await response.json();
        global.localStorage.setItem("access_token", session.access_token);
        global.localStorage.setItem("username", session.user.username);
        global.localStorage.setItem("user_id", session.user.id);
        if (form.elements.remember.checked) {
          global.localStorage.setItem(
            "remembered_identifier",
            payload.identifier,
          );
        } else {
          global.localStorage.removeItem("remembered_identifier");
        }

        showAlert("Identity confirmed. Opening workspace…", "success");
        global.setTimeout(() => global.location.assign("/dashboard"), 300);
      } catch (error) {
        showAlert(error.message);
        submit.disabled = false;
        submit.classList.remove("loading");
      }
    });
  }

  function formatNumber(value) {
    if (value === null || value === undefined) return "—";
    return new Intl.NumberFormat(undefined, {
      maximumFractionDigits: 4,
    }).format(value);
  }

  function formatDate(value, includeTime = true) {
    if (!value) return "No activity yet";
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      ...(includeTime ? { timeStyle: "short" } : {}),
    }).format(new Date(value));
  }

  function renderExpression(type, inputs) {
    return inputs.join(` ${OPERATORS[type] || "?"} `);
  }

  async function loadInsights() {
    const panel = document.getElementById("insightsPanel");
    if (!panel) return;

    const response = await authorizedFetch("/insights");
    if (!response.ok) {
      throw new Error(await responseError(response, "Insights unavailable."));
    }
    const insights = await response.json();

    document.querySelector('[data-insight="total"]').textContent =
      insights.total_calculations;
    document.querySelector('[data-insight="average"]').textContent =
      formatNumber(insights.average_result);
    document.querySelector('[data-insight="highest"]').textContent =
      formatNumber(insights.highest_result);
    document.querySelector('[data-insight="latest"]').textContent =
      formatDate(insights.latest_activity);

    const maximum = Math.max(
      1,
      ...Object.values(insights.operation_counts),
    );
    Object.entries(insights.operation_counts).forEach(([operation, count]) => {
      document.querySelector(
        `[data-operation-count="${operation}"]`,
      ).textContent = count;
      const meter = document.querySelector(
        `[data-operation-meter="${operation}"]`,
      );
      meter.style.width = `${(count / maximum) * 100}%`;
    });
    panel.dataset.loaded = "true";
  }

  function renderCalculationRows(calculations) {
    const tableBody = document.getElementById("calculationsTable");
    tableBody.replaceChildren();

    if (!calculations.length) {
      const row = document.createElement("tr");
      row.className = "empty-row";
      row.innerHTML =
        '<td colspan="5">No records yet. Run a calculation to begin your ledger.</td>';
      tableBody.appendChild(row);
      return;
    }

    calculations.forEach((calculation) => {
      const row = document.createElement("tr");
      row.dataset.testid = "calculation-row";
      row.dataset.calculationId = calculation.id;
      row.innerHTML = `
        <td><span class="operation-badge">${calculation.type}</span></td>
        <td class="expression">${renderExpression(calculation.type, calculation.inputs)}</td>
        <td class="result-cell">${formatNumber(calculation.result)}</td>
        <td>${formatDate(calculation.created_at, false)}</td>
        <td>
          <div class="row-actions">
            <a href="/dashboard/view/${calculation.id}" data-action="view">Read</a>
            <a href="/dashboard/edit/${calculation.id}" data-action="edit">Edit</a>
            <button type="button" data-delete-id="${calculation.id}">Delete</button>
          </div>
        </td>
      `;
      tableBody.appendChild(row);
    });

    tableBody.querySelectorAll("[data-delete-id]").forEach((button) => {
      button.addEventListener("click", async () => {
        if (!global.confirm("Delete this calculation permanently?")) return;
        button.disabled = true;
        const response = await authorizedFetch(
          `/calculations/${button.dataset.deleteId}`,
          { method: "DELETE" },
        );
        if (!response.ok) {
          button.disabled = false;
          showAlert(await responseError(response, "Delete failed."));
          return;
        }
        showAlert("Calculation deleted.", "success");
        await Promise.all([loadCalculations(), loadInsights()]);
      });
    });
  }

  async function loadCalculations() {
    const response = await authorizedFetch("/calculations");
    if (!response.ok) {
      throw new Error(await responseError(response, "Ledger unavailable."));
    }
    renderCalculationRows(await response.json());
  }

  function configureDashboard() {
    const form = document.getElementById("calculationForm");
    if (!form) return;
    if (!requireSession()) return;

    const username = global.localStorage.getItem("username") || "calculator";
    const welcome = document.querySelector("[data-workspace-user]");
    if (welcome) welcome.textContent = username;

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearAlert();
      const operation = form.elements.type.value;
      const parsed = validateCalculationInputs(
        form.elements.inputs.value,
        operation,
      );
      if (!parsed.valid) {
        showAlert(parsed.error);
        form.elements.inputs.focus();
        return;
      }

      const submit = form.querySelector('[type="submit"]');
      submit.disabled = true;
      submit.classList.add("loading");
      try {
        const response = await authorizedFetch("/calculations", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type: operation, inputs: parsed.values }),
        });
        if (!response.ok) {
          throw new Error(
            await responseError(response, "Calculation could not be saved."),
          );
        }
        const calculation = await response.json();
        showAlert(
          `Calculation saved. Result: ${formatNumber(calculation.result)}.`,
          "success",
        );
        form.reset();
        await Promise.all([loadCalculations(), loadInsights()]);
      } catch (error) {
        showAlert(error.message);
      } finally {
        submit.disabled = false;
        submit.classList.remove("loading");
      }
    });

    Promise.all([loadCalculations(), loadInsights()]).catch((error) =>
      showAlert(error.message),
    );
  }

  function calculationId() {
    return document.querySelector("[data-calculation-id]")?.dataset
      .calculationId;
  }

  function renderCalculationDetails(calculation) {
    document.querySelector("[data-detail-expression]").textContent =
      renderExpression(calculation.type, calculation.inputs);
    document.querySelector("[data-detail-result]").textContent =
      formatNumber(calculation.result);
    document.querySelector("[data-detail-operation]").textContent =
      calculation.type;
    document.querySelector("[data-detail-created]").textContent = formatDate(
      calculation.created_at,
    );
    document.querySelector("[data-detail-updated]").textContent = formatDate(
      calculation.updated_at,
    );
    document.querySelector("[data-detail-id]").textContent = calculation.id;
    document.querySelector("[data-edit-link]").href =
      `/dashboard/edit/${calculation.id}`;
    document.querySelector("[data-record-loading]")?.remove();
    document.querySelector("[data-record-content]").hidden = false;
  }

  function configureView() {
    const container = document.querySelector('[data-page="view"]');
    if (!container) return;
    if (!requireSession()) return;
    const id = calculationId();

    authorizedFetch(`/calculations/${id}`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(
            await responseError(response, "Calculation not found."),
          );
        }
        renderCalculationDetails(await response.json());
      })
      .catch((error) => showAlert(error.message));

    document.querySelector("[data-delete-record]").addEventListener(
      "click",
      async (event) => {
        if (!global.confirm("Delete this calculation permanently?")) return;
        event.currentTarget.disabled = true;
        const response = await authorizedFetch(`/calculations/${id}`, {
          method: "DELETE",
        });
        if (!response.ok) {
          showAlert(await responseError(response, "Delete failed."));
          event.currentTarget.disabled = false;
          return;
        }
        global.location.assign("/dashboard");
      },
    );
  }

  function updateEditPreview(form) {
    const preview = document.querySelector("[data-edit-preview]");
    const parsed = validateCalculationInputs(
      form.elements.inputs.value,
      form.elements.type.value,
    );
    if (!parsed.valid) {
      preview.textContent = parsed.error;
      preview.classList.add("preview-error");
      return;
    }
    preview.classList.remove("preview-error");
    preview.textContent = `${renderExpression(
      form.elements.type.value,
      parsed.values,
    )} = ${formatNumber(
      calculatePreview(form.elements.type.value, parsed.values),
    )}`;
  }

  function configureEdit() {
    const form = document.getElementById("editCalculationForm");
    if (!form) return;
    if (!requireSession()) return;
    const id = calculationId();

    authorizedFetch(`/calculations/${id}`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(
            await responseError(response, "Calculation not found."),
          );
        }
        const calculation = await response.json();
        form.elements.type.value = calculation.type;
        form.elements.inputs.value = calculation.inputs.join(", ");
        updateEditPreview(form);
        document.querySelector("[data-record-loading]")?.remove();
        form.hidden = false;
      })
      .catch((error) => showAlert(error.message));

    form.elements.inputs.addEventListener("input", () =>
      updateEditPreview(form),
    );

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearAlert();
      const parsed = validateCalculationInputs(
        form.elements.inputs.value,
        form.elements.type.value,
      );
      if (!parsed.valid) {
        showAlert(parsed.error);
        return;
      }

      const submit = form.querySelector('[type="submit"]');
      submit.disabled = true;
      submit.classList.add("loading");
      const response = await authorizedFetch(`/calculations/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ inputs: parsed.values }),
      });
      if (!response.ok) {
        showAlert(await responseError(response, "Update failed."));
        submit.disabled = false;
        submit.classList.remove("loading");
        return;
      }
      global.location.assign(`/dashboard/view/${id}`);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    configureNavigation();
    configureRegistration();
    configureLogin();
    configureDashboard();
    configureView();
    configureEdit();
  });
})(globalThis);
