const API = "http://localhost:8000/api/v1";
let token = localStorage.getItem("starlite_token");
let userId = localStorage.getItem("starlite_uid");
let username = localStorage.getItem("starlite_uname");

function show(id) { document.getElementById(id).classList.remove("hidden"); }
function hide(id) { document.getElementById(id).classList.add("hidden"); }

async function doLogin() {
  const u = document.getElementById("username").value;
  const p = document.getElementById("password").value;
  try {
    const res = await fetch(`${API}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u, password: p }),
    });
    if (!res.ok) throw new Error("bad creds");
    const data = await res.json();
    token = data.access_token;
    userId = data.user_id;
    username = u;
    localStorage.setItem("starlite_token", token);
    localStorage.setItem("starlite_uid", userId);
    localStorage.setItem("starlite_uname", username);
    enterBBS();
  } catch (e) {
    document.getElementById("login-msg").textContent = "LOGIN FAILED - check credentials";
  }
}

function logout() {
  localStorage.clear();
  token = null;
  hide("main-screen");
  show("login-screen");
}

async function enterBBS() {
  hide("login-screen");
  show("main-screen");
  document.getElementById("whoami").textContent = `USER: ${username} (id ${userId})`;
  loadMovies();
  loadSnacks();
  loadRentals();
}

async function authFetch(url, opts = {}) {
  opts.headers = Object.assign({}, opts.headers, { Authorization: `Bearer ${token}` });
  return fetch(url, opts);
}

async function loadMovies() {
  const res = await fetch(`${API}/movies`);
  const movies = await res.json();
  const el = document.getElementById("movies");
  el.innerHTML = movies.map(m => `
    <div class="card">
      <b>${m.title}</b> (${m.year})<br>
      ${m.genre} - $${m.rental_price.toFixed(2)} - stock: ${m.stock}
      <button onclick="rentMovie(${m.id})">RENT</button>
    </div>`).join("");
}

async function rentMovie(movieId) {
  const res = await authFetch(`${API}/rentals`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ movie_id: movieId, qty: 1 }),
  });
  const data = await res.json();
  document.getElementById("action-msg").textContent = res.ok
    ? `Rented! Total: $${data.total_price}` : `Error: ${data.detail}`;
  loadRentals();
}

async function loadSnacks() {
  const res = await fetch(`${API}/snacks`);
  const snacks = await res.json();
  const el = document.getElementById("snacks");
  el.innerHTML = snacks.map(s => `
    <div class="card">
      <b>${s.name}</b><br>
      $${s.price.toFixed(2)} - stock: ${s.stock}
      <button onclick="orderSnack(${s.id})">ORDER</button>
    </div>`).join("");
}

async function orderSnack(snackId) {
  const res = await authFetch(`${API}/snacks/order`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ snack_id: snackId, qty: 1 }),
  });
  const data = await res.json();
  document.getElementById("action-msg").textContent = res.ok
    ? `Ordered ${data.snack}! Total: $${data.total_price}` : `Error: ${data.detail}`;
}

async function loadRentals() {
  const res = await authFetch(`${API}/rentals`);
  const rentals = await res.json();
  const el = document.getElementById("rentals");
  el.innerHTML = rentals.length
    ? rentals.map(r => `<div class="card">Movie #${r.movie_id} x${r.qty}</div>`).join("")
    : "<p>No rentals yet.</p>";
}

if (token) { enterBBS(); }
