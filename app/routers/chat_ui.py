"""Sirve la interfaz de chat de prueba."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["UI"])

_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>DAGMA — Chat de prueba</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #e5ddd5;
      height: 100dvh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }

    .wrapper {
      width: 100%;
      max-width: 480px;
      height: 100dvh;
      display: flex;
      flex-direction: column;
      background: #fff;
      box-shadow: 0 0 40px rgba(0,0,0,.2);
    }

    /* ── Header ── */
    .header {
      background: #128c7e;
      color: #fff;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .avatar {
      width: 40px; height: 40px;
      background: #075e54;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-size: 20px;
    }
    .header-info h1 { font-size: 16px; font-weight: 600; }
    .header-info p  { font-size: 12px; opacity: .8; }
    .btn-new {
      margin-left: auto;
      background: rgba(255,255,255,.15);
      border: none;
      color: #fff;
      padding: 6px 12px;
      border-radius: 20px;
      cursor: pointer;
      font-size: 12px;
      white-space: nowrap;
    }
    .btn-new:hover { background: rgba(255,255,255,.25); }

    /* ── Messages ── */
    .messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      background: #e5ddd5;
    }

    .bubble {
      max-width: 80%;
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 14px;
      line-height: 1.5;
      word-break: break-word;
      white-space: pre-wrap;
      position: relative;
    }
    .bubble.bot {
      background: #fff;
      align-self: flex-start;
      border-top-left-radius: 2px;
      box-shadow: 0 1px 2px rgba(0,0,0,.1);
    }
    .bubble.user {
      background: #dcf8c6;
      align-self: flex-end;
      border-top-right-radius: 2px;
      box-shadow: 0 1px 2px rgba(0,0,0,.1);
    }
    .bubble .time {
      font-size: 10px;
      color: #999;
      text-align: right;
      margin-top: 4px;
    }
    .bubble.reporte {
      background: #e8f5e9;
      border-left: 3px solid #4caf50;
    }
    .bubble.error {
      background: #fff3e0;
      border-left: 3px solid #ff9800;
    }

    .typing {
      align-self: flex-start;
      background: #fff;
      border-radius: 8px;
      border-top-left-radius: 2px;
      padding: 10px 16px;
      box-shadow: 0 1px 2px rgba(0,0,0,.1);
      display: none;
    }
    .typing span {
      display: inline-block;
      width: 7px; height: 7px;
      background: #999;
      border-radius: 50%;
      margin: 0 2px;
      animation: bounce .9s infinite;
    }
    .typing span:nth-child(2) { animation-delay: .15s; }
    .typing span:nth-child(3) { animation-delay: .3s; }
    @keyframes bounce {
      0%,60%,100% { transform: translateY(0); }
      30% { transform: translateY(-6px); }
    }

    /* ── Badge de reporte ── */
    .badge {
      display: inline-block;
      background: #128c7e;
      color: #fff;
      font-size: 11px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 12px;
      margin-bottom: 4px;
    }

    /* ── Input ── */
    .input-bar {
      background: #f0f0f0;
      padding: 8px 10px;
      display: flex;
      gap: 8px;
      align-items: flex-end;
    }
    textarea {
      flex: 1;
      border: none;
      border-radius: 20px;
      padding: 10px 16px;
      font-size: 14px;
      resize: none;
      max-height: 100px;
      outline: none;
      font-family: inherit;
      line-height: 1.4;
    }
    .btn-send {
      width: 44px; height: 44px;
      background: #128c7e;
      border: none;
      border-radius: 50%;
      color: #fff;
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
    }
    .btn-send:disabled { background: #ccc; cursor: default; }
    .btn-send svg { width: 22px; height: 22px; }

    .session-bar {
      background: #fff9c4;
      font-size: 11px;
      text-align: center;
      padding: 4px;
      color: #666;
      display: none;
    }
  </style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <div class="avatar">🌿</div>
    <div class="header-info">
      <h1>DAGMA Emergencias</h1>
      <p>Asistente ambiental · Cali</p>
    </div>
    <button class="btn-new" onclick="newChat()">+ Nueva sesión</button>
  </div>

  <div class="session-bar" id="sessionBar"></div>

  <div class="messages" id="messages">
    <div class="bubble bot">
      Hola 👋 Soy el asistente de emergencias ambientales del <strong>DAGMA Cali</strong>.<br><br>
      Cuéntame qué está pasando. Atendemos:<br>
      🌳 Árboles caídos<br>
      🦜 Rescate de animales silvestres<br>
      🪓 Tala ilegal de árboles<br>
      💧 Contaminación de fuentes hídricas
      <div class="time">ahora</div>
    </div>
    <div class="typing" id="typing"><span></span><span></span><span></span></div>
  </div>

  <div class="input-bar">
    <textarea id="input" rows="1" placeholder="Escribe tu reporte…"
      onkeydown="handleKey(event)" oninput="autoResize(this)"></textarea>
    <button class="btn-send" id="sendBtn" onclick="send()">
      <svg viewBox="0 0 24 24" fill="currentColor">
        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
      </svg>
    </button>
  </div>
</div>

<script>
  let sessionId = null;
  let sending = false;

  const messagesEl = document.getElementById('messages');
  const inputEl    = document.getElementById('input');
  const sendBtn    = document.getElementById('sendBtn');
  const typingEl   = document.getElementById('typing');
  const sessionBar = document.getElementById('sessionBar');

  function now() {
    return new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
  }

  function scrollBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addBubble(text, role, extra) {
    typingEl.style.display = 'none';
    const div = document.createElement('div');
    div.className = 'bubble ' + role + (extra?.reporte ? ' reporte' : '');

    let html = '';
    if (extra?.reporte) {
      html += `<div class="badge">Reporte #${extra.reporte}</div><br>`;
    }
    // Bold *text* → <strong>
    const safe = text
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/\\*(.*?)\\*/g, '<strong>$1</strong>');
    html += safe;
    html += `<div class="time">${now()}</div>`;
    div.innerHTML = html;

    messagesEl.insertBefore(div, typingEl);
    scrollBottom();
  }

  function showTyping() {
    messagesEl.appendChild(typingEl);
    typingEl.style.display = 'block';
    scrollBottom();
  }

  function newChat() {
    sessionId = null;
    messagesEl.innerHTML = '';
    messagesEl.appendChild(typingEl);
    typingEl.style.display = 'none';
    sessionBar.style.display = 'none';
    addBubble(
      'Hola 👋 Soy el asistente de emergencias ambientales del *DAGMA Cali*.\\n\\n' +
      'Cuéntame qué está pasando. Atendemos:\\n' +
      '🌳 Árboles caídos\\n🦜 Rescate de animales silvestres\\n' +
      '🪓 Tala ilegal de árboles\\n💧 Contaminación de fuentes hídricas',
      'bot'
    );
  }

  async function send() {
    const text = inputEl.value.trim();
    if (!text || sending) return;

    sending = true;
    sendBtn.disabled = true;
    inputEl.value = '';
    autoResize(inputEl);

    addBubble(text, 'user');
    showTyping();

    try {
      const body = { message: text };
      if (sessionId) body.session_id = sessionId;

      const res = await fetch('/test/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();

      sessionId = data.session_id;
      sessionBar.style.display = 'block';
      sessionBar.textContent = 'Sesión: ' + sessionId.slice(0, 8) + '…';

      addBubble(data.reply, 'bot', data.reporte_id ? { reporte: data.reporte_id } : null);
    } catch (err) {
      addBubble('⚠️ Error al conectar con el servidor. Revisá la conexión.', 'bot error');
      console.error(err);
    } finally {
      sending = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 100) + 'px';
  }

  inputEl.focus();
</script>
</body>
</html>"""


@router.get("/chat", response_class=HTMLResponse)
async def chat_ui():
    """Interfaz de chat de prueba para el bot DAGMA."""
    return HTMLResponse(content=_HTML)
