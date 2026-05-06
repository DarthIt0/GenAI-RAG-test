const chatEl = document.getElementById('chat');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('send');
const statusEl = document.getElementById('status');

function append(role, text) {
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.innerHTML = `<strong>${role}:</strong> ${text.replace(/\n/g, '<br>')}`;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function sendMessage() {
  const msg = inputEl.value.trim();
  if (!msg) return;

  append("User", msg);
  inputEl.value = "";
  sendBtn.disabled = true;
  statusEl.textContent = "Thinking...";

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: msg })
  });

  const data = await res.json();
  append("Assistant", data.answer);

  sendBtn.disabled = false;
  statusEl.textContent = "";
}

sendBtn.onclick = sendMessage;
inputEl.onkeydown = e => { if (e.key === "Enter") sendMessage(); };

