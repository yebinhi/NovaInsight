document.documentElement.classList.add("js");

const header = document.querySelector("[data-header]");
const toggle = document.querySelector("[data-nav-toggle]");
const nav = document.querySelector("[data-nav]");

const onScroll = () => {
  if (!header) return;
  header.classList.toggle("is-scrolled", window.scrollY > 8);
};

onScroll();
window.addEventListener("scroll", onScroll, { passive: true });

const closeNav = () => {
  if (!nav || !toggle) return;
  nav.classList.remove("is-open");
  toggle.setAttribute("aria-expanded", "false");
  toggle.textContent = window.novaText("nav.menu");
  document.body.classList.remove("nav-open");
};

if (toggle && nav) {
  toggle.addEventListener("click", () => {
    const open = !nav.classList.contains("is-open");
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = window.novaText(open ? "nav.close" : "nav.menu");
    document.body.classList.toggle("nav-open", open);
    if (open) {
      const first = nav.querySelector("a");
      if (first) first.focus();
    }
  });

  nav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", closeNav);
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeNav();
  });
}

const form = document.querySelector("[data-contact-form]");
if (form) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = form.querySelector("[data-form-status]");
    const button = form.querySelector("[type=submit]");
    const payload = {
      name: form.elements.name.value.trim(),
      organization: form.elements.organization.value.trim(),
      email: form.elements.email.value.trim(),
      message: form.elements.message.value.trim(),
    };
    button.disabled = true;
    if (status) status.textContent = "";
    try {
      const response = await fetch("/api/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const known = {
          "Send the note as JSON.": "form.json",
          "That note is too long.": "form.long",
          "Name, email, and a note are required.": "form.required",
          "Enter an email address.": "form.emailInvalid",
          "The note could not be saved.": "form.failed",
        };
        const error = new Error(data.error || "The note could not be saved.");
        error.i18nKey = known[data.error] || known[error.message] || "";
        throw error;
      }
      form.reset();
      if (status) {
        status.dataset.i18n = "form.saved";
        status.textContent = window.novaText("form.saved");
      }
    } catch (error) {
      if (status) {
        const offline = error.message === "Failed to fetch";
        const key = offline ? "form.offline" : error.i18nKey;
        if (key) {
          status.dataset.i18n = key;
          status.textContent = window.novaText(key);
        } else {
          delete status.dataset.i18n;
          status.textContent = error.message;
        }
      }
    } finally {
      button.disabled = false;
    }
  });
}

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const revealNodes = document.querySelectorAll("[data-reveal]");

if (reduceMotion) {
  revealNodes.forEach((node) => node.classList.add("is-inview"));
} else if (revealNodes.length) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-inview");
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.16, rootMargin: "0px 0px -8% 0px" }
  );
  revealNodes.forEach((node) => observer.observe(node));
}
