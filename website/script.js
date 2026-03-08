/**
 * Sai AI Voice Assistant – Demo Website Scripts
 * ───────────────────────────────────────────────
 * Drives the interactive terminal demo on the landing page.
 */

"use strict";

// ── Demo conversation script ────────────────────────────────────
const DEMO_SCRIPT = [
  { delay: 600,  type: "system", text: "Wake word engine started. Listening for 'Hey Sai'…" },
  { delay: 1400, type: "user",   text: "Hey Sai" },
  { delay: 900,  type: "sai",    text: "Yes, how can I help?" },
  { delay: 1200, type: "user",   text: "Open Chrome" },
  { delay: 800,  type: "sai",    text: "Opening Chrome." },
  { delay: 1600, type: "user",   text: "Hey Sai, search for machine learning tutorials" },
  { delay: 700,  type: "sai",    text: "Searching the web for: machine learning tutorials" },
  { delay: 1800, type: "user",   text: "Sai, remind me to study AI at 7 PM" },
  { delay: 800,  type: "sai",    text: "Reminder set: study AI at 7:00 PM." },
  { delay: 2000, type: "user",   text: "Remember my favourite language is Python" },
  { delay: 700,  type: "sai",    text: "Got it! I'll remember that your favourite language is Python." },
  { delay: 1500, type: "user",   text: "What language do I like?" },
  { delay: 700,  type: "sai",    text: "You like Python." },
  { delay: 1800, type: "user",   text: "Send message to John saying I will be late" },
  { delay: 900,  type: "sai",    text: "Message sent to John: 'I will be late'." },
  { delay: 1600, type: "user",   text: "Hey Sai, what's the weather in Hyderabad?" },
  { delay: 1100, type: "sai",    text: "Weather in Hyderabad: Partly cloudy. Temperature: 32°C, Wind speed: 14 km/h." },
  { delay: 1500, type: "user",   text: "Tell me a joke" },
  { delay: 600,  type: "sai",    text: "Why do programmers prefer dark mode? Because light attracts bugs!" },
  { delay: 2000, type: "system", text: "Demo complete. Start Sai AI on your machine to experience the full assistant." },
];

// ── State ───────────────────────────────────────────────────────
let _demoTimeouts = [];
let _demoRunning  = false;

// ── DOM helpers ─────────────────────────────────────────────────
function getTerminalBody() {
  return document.getElementById("terminal-body");
}

function appendLine(type, text) {
  const body = getTerminalBody();
  if (!body) return;

  const p = document.createElement("p");

  if (type === "system") {
    p.className = "system-msg";
    p.textContent = "[SYSTEM] " + text;
  } else if (type === "user") {
    p.className = "user-line";
    p.textContent = "🎤 You: " + text;
  } else if (type === "sai") {
    p.className = "sai-line";
    p.textContent = text;  // ::before pseudo-element adds the "Sai AI:" prefix
  }

  body.appendChild(p);
  body.scrollTop = body.scrollHeight;
}

// ── Demo runner ─────────────────────────────────────────────────
function runDemo() {
  if (_demoRunning) return;
  _demoRunning = true;

  document.getElementById("demo-btn").disabled = true;

  let cumulative = 0;

  DEMO_SCRIPT.forEach((step) => {
    cumulative += step.delay;
    const t = setTimeout(() => {
      appendLine(step.type, step.text);
      // Re-enable the run button when the last step fires
      if (step === DEMO_SCRIPT[DEMO_SCRIPT.length - 1]) {
        _demoRunning = false;
        const btn = document.getElementById("demo-btn");
        if (btn) btn.disabled = false;
      }
    }, cumulative);
    _demoTimeouts.push(t);
  });
}

function resetDemo() {
  // Cancel pending timeouts
  _demoTimeouts.forEach(clearTimeout);
  _demoTimeouts = [];
  _demoRunning  = false;

  const body = getTerminalBody();
  if (body) {
    body.innerHTML = '<p class="system-msg">[SYSTEM] Sai AI started. Say a wake word or type a command.</p>';
  }

  const btn = document.getElementById("demo-btn");
  if (btn) btn.disabled = false;
}

// ── Smooth-scroll nav links ──────────────────────────────────────
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (e) => {
      const target = document.querySelector(link.getAttribute("href"));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });
}

// ── Copy-code blocks ─────────────────────────────────────────────
function initCopyButtons() {
  document.querySelectorAll("pre").forEach((pre) => {
    const btn = document.createElement("button");
    btn.textContent = "Copy";
    btn.className   = "copy-btn";
    btn.style.cssText =
      "position:absolute;top:8px;right:10px;padding:4px 10px;" +
      "border-radius:6px;border:1px solid rgba(255,255,255,0.2);" +
      "background:rgba(255,255,255,0.05);color:#ccc;font-size:0.78rem;" +
      "cursor:pointer;transition:background 0.2s;";

    btn.addEventListener("click", () => {
      const code = pre.querySelector("code");
      const text = code ? code.textContent : pre.textContent;
      navigator.clipboard.writeText(text).then(() => {
        btn.textContent = "Copied!";
        setTimeout(() => { btn.textContent = "Copy"; }, 1800);
      });
    });

    pre.style.position = "relative";
    pre.appendChild(btn);
  });
}

// ── Intersection observer for card animations ─────────────────────
function initScrollAnimations() {
  if (!("IntersectionObserver" in window)) return;

  const style = document.createElement("style");
  style.textContent = `
    .feature-card, .install-step, .arch-box {
      opacity: 0;
      transform: translateY(24px);
      transition: opacity 0.5s ease, transform 0.5s ease;
    }
    .feature-card.visible, .install-step.visible, .arch-box.visible {
      opacity: 1;
      transform: translateY(0);
    }
  `;
  document.head.appendChild(style);

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );

  document.querySelectorAll(".feature-card, .install-step, .arch-box").forEach((el) => {
    observer.observe(el);
  });
}

// ── Init ─────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const demoBtn  = document.getElementById("demo-btn");
  const resetBtn = document.getElementById("reset-btn");

  if (demoBtn)  demoBtn.addEventListener("click", runDemo);
  if (resetBtn) resetBtn.addEventListener("click", resetDemo);

  initSmoothScroll();
  initCopyButtons();
  initScrollAnimations();
});
