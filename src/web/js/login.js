/**
 * login.js — Handles the login page logic.
 */
import { login } from "./api.js";

// Redirect if already authenticated
if (localStorage.getItem("cinetv_token")) {
  window.location.href = "/portal.html";
}

const form = document.getElementById("login-form");
const errorEl = document.getElementById("login-error");
const submitBtn = document.getElementById("submit-btn");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorEl.textContent = "";
  submitBtn.disabled = true;
  submitBtn.textContent = "Entrando…";

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  try {
    const { access_token } = await login(username, password);
    localStorage.setItem("cinetv_token", access_token);
    window.location.href = "/portal.html";
  } catch (err) {
    errorEl.textContent = err.message || "Error de autenticación";
    submitBtn.disabled = false;
    submitBtn.textContent = "Entrar";
  }
});
