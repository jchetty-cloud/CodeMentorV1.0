/* ── CodeMentor — Tutor Page JS ─────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {

  marked.setOptions({ gfm: true, breaks: true });

  // ── State ─────────────────────────────────────────────────────
  let conversationHistory = [];
  let currentCode = '';
  let currentSessionId = null;
  let detectTimeout = null;
  let detectedLang = 'python';

  // ── DOM refs ──────────────────────────────────────────────────
  const codeInput    = document.getElementById('code-input');
  const contextInput = document.getElementById('context-input');
  const responseArea = document.getElementById('response-area');
  const followupSec  = document.getElementById('followup-section');
  const chatMessages = document.getElementById('chat-messages');
  const followupInp  = document.getElementById('followup-input');
  const sendBtn      = document.getElementById('send-btn');
  const loadingOver  = document.getElementById('loading-overlay');
  const loadingMsg   = document.getElementById('loading-message');
  const clearBtn     = document.getElementById('clear-btn');
  const langBadge    = document.getElementById('lang-badge');
  const langName     = document.getElementById('lang-name');
  const actionBtns   = document.querySelectorAll('.action-btn');

  const LOADING_MSGS = {
    explain: ['Reading your code carefully…', 'Breaking it down step by step…'],
    debug:   ['Hunting for clues…', 'Putting on the detective hat…'],
    improve: ['Looking for improvements…', 'Checking Pythonic style…'],
    concept: ['Finding the key concept…', 'Preparing your lesson…'],
    quiz:    ['Writing quiz questions…', 'Crafting the perfect challenge…'],
    review:  ['Putting on the reviewer hat…', 'Writing structured feedback…'],
  };

  const ACTION_META = {
    explain: { icon: '🔍', label: 'Explanation' },
    debug:   { icon: '🐛', label: 'Debug Help' },
    improve: { icon: '✨', label: 'Improvements' },
    concept: { icon: '📚', label: 'Concept Lesson' },
    quiz:    { icon: '🎯', label: 'Quiz Time' },
    review:  { icon: '📋', label: 'Code Review' },
  };

  const LANG_LABELS = {
    python: 'Python', javascript: 'JavaScript', java: 'Java',
    html: 'HTML', css: 'CSS', cpp: 'C++', csharp: 'C#',
    sql: 'SQL', bash: 'Bash', other: 'Code',
  };

  // ── Language detection ────────────────────────────────────────
  function updateLangBadge(lang) {
    detectedLang = lang;
    if (langName) langName.textContent = LANG_LABELS[lang] || lang;
  }

  function scheduleDetect() {
    clearTimeout(detectTimeout);
    const code = codeInput.value.trim();
    if (!code || code.length < 20) return;
    detectTimeout = setTimeout(async () => {
      try {
        const res = await fetch('/api/detect-language', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code }),
        });
        const data = await res.json();
        if (data.language) updateLangBadge(data.language);
      } catch { /* silently ignore */ }
    }, 900);
  }

  if (codeInput) codeInput.addEventListener('input', scheduleDetect);

  // ── Tab key support in textarea ───────────────────────────────
  if (codeInput) {
    codeInput.addEventListener('keydown', e => {
      if (e.key === 'Tab') {
        e.preventDefault();
        const s = codeInput.selectionStart;
        const end = codeInput.selectionEnd;
        codeInput.value = codeInput.value.substring(0, s) + '    ' + codeInput.value.substring(end);
        codeInput.selectionStart = codeInput.selectionEnd = s + 4;
      }
    });
  }

  // ── Loading helpers ───────────────────────────────────────────
  function showLoading(action) {
    const msgs = LOADING_MSGS[action] || ['Thinking…'];
    if (loadingMsg) loadingMsg.textContent = msgs[Math.floor(Math.random() * msgs.length)];
    if (loadingOver) loadingOver.classList.add('active');
  }

  function hideLoading() {
    if (loadingOver) loadingOver.classList.remove('active');
  }

  // ── Render helpers ────────────────────────────────────────────
  function setActiveAction(key) {
    actionBtns.forEach(b => b.classList.toggle('active', b.dataset.action === key));
  }

  function scrollChat() {
    if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function appendChat(role, text) {
    if (!chatMessages) return;
    const div = document.createElement('div');
    div.className = `chat-message ${role}`;
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    bubble.textContent = text;
    div.appendChild(bubble);
    chatMessages.appendChild(div);
    scrollChat();
  }

  function showError(msg) {
    if (!responseArea) return;
    responseArea.innerHTML = `
      <div class="response-content">
        <p class="error-msg">⚠️ ${msg}</p>
      </div>`;
    if (followupSec) followupSec.style.display = 'none';
  }

  // ── Main tutor request ────────────────────────────────────────
  async function runTutor(action) {
    if (!codeInput || !responseArea) return;
    const code    = codeInput.value.trim();
    const context = contextInput ? contextInput.value.trim() : '';

    if (!code) { shakeEl(codeInput); return; }

    currentCode = code;
    conversationHistory = [];
    currentSessionId = null;

    setActiveAction(action);
    showLoading(action);

    try {
      const res = await fetch('/api/tutor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, action, context, language: detectedLang }),
      });
      const data = await res.json();

      if (data.error) { showError(data.error); return; }

      currentSessionId = data.session_id;
      if (data.language) updateLangBadge(data.language);

      const { icon, label } = ACTION_META[action] || { icon: '🤖', label: action };
      conversationHistory = [
        { role: 'user',      content: `[${label}]\n\`\`\`${detectedLang}\n${code}\n\`\`\`\n\n${context}` },
        { role: 'assistant', content: data.response },
      ];

      responseArea.innerHTML = `
        <div class="response-content">
          <div class="response-badge">${icon} ${label}</div>
          <div id="response-body">${marked.parse(data.response)}</div>
        </div>`;
      responseArea.querySelectorAll('pre code').forEach(b => hljs.highlightElement(b));

      setupFollowup();

    } catch (err) {
      showError('Connection error — is the Flask server running?');
      console.error(err);
    } finally {
      hideLoading();
    }
  }

  // ── Follow-up chat ────────────────────────────────────────────
  function setupFollowup() {
    if (!chatMessages || !followupSec) return;
    chatMessages.innerHTML = '';
    followupSec.style.display = 'block';
    if (followupInp) followupInp.focus();
  }

  async function sendFollowup() {
    if (!followupInp) return;
    const q = followupInp.value.trim();
    if (!q) return;
    followupInp.value = '';
    if (sendBtn) sendBtn.disabled = true;
    appendChat('user', q);
    conversationHistory.push({ role: 'user', content: q });

    try {
      const res = await fetch('/api/followup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          history: conversationHistory.slice(0, -1),
          question: q,
          code: currentCode,
          session_id: currentSessionId,
        }),
      });
      const data = await res.json();
      const reply = data.error ? '⚠️ ' + data.error : data.response;
      appendChat('assistant', reply);
      if (!data.error) conversationHistory.push({ role: 'assistant', content: reply });
    } catch {
      appendChat('assistant', '⚠️ Connection error.');
    } finally {
      if (sendBtn) sendBtn.disabled = false;
      if (followupInp) followupInp.focus();
    }
  }

  // ── Micro-interaction ─────────────────────────────────────────
  function shakeEl(el) {
    el.style.outline = '2px solid red';
    setTimeout(() => { el.style.outline = ''; }, 600);
  }

  // ── Clear button ──────────────────────────────────────────────
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (codeInput)    codeInput.value = '';
      if (contextInput) contextInput.value = '';
      detectedLang = 'python';
      updateLangBadge('python');
      conversationHistory = [];
      currentCode = '';
      currentSessionId = null;
      actionBtns.forEach(b => b.classList.remove('active'));
      if (followupSec) followupSec.style.display = 'none';
      if (responseArea) responseArea.innerHTML = `
        <div class="response-placeholder">
          <p>Paste your code and choose a tutoring mode.</p>
        </div>`;
      if (codeInput) codeInput.focus();
    });
  }

  // ── Event listeners ───────────────────────────────────────────
  actionBtns.forEach(b => b.addEventListener('click', () => runTutor(b.dataset.action)));

  if (sendBtn)      sendBtn.addEventListener('click', sendFollowup);
  if (followupInp)  followupInp.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendFollowup(); }
  });

  // ── Init ──────────────────────────────────────────────────────
  if (codeInput) codeInput.focus();

}); // end DOMContentLoaded