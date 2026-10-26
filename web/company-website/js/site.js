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
  toggle.textContent = "Menu";
  document.body.classList.remove("nav-open");
};

if (toggle && nav) {
  toggle.addEventListener("click", () => {
    const open = !nav.classList.contains("is-open");
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = open ? "Close" : "Menu";
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
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const name = form.elements.name.value.trim();
    const organization = form.elements.organization.value.trim();
    const email = form.elements.email.value.trim();
    const message = form.elements.message.value.trim();
    const body = [
      `Name: ${name}`,
      organization ? `Organization: ${organization}` : null,
      `Email: ${email}`,
      "",
      message,
    ]
      .filter((line) => line !== null)
      .join("\n");
    const href = `mailto:hello@novainsight.com?subject=${encodeURIComponent("A note for Nova Insight")}&body=${encodeURIComponent(body)}`;
    const status = form.querySelector("[data-form-status]");
    if (status) {
      status.textContent = "Opening your email app with this note. If nothing opens, write to hello@novainsight.com.";
    }
    window.location.href = href;
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
