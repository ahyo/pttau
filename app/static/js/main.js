// custom scripts here

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-toggle-password]").forEach((wrapper) => {
    const input = wrapper.querySelector("input[type='password'], input[data-password-target]");
    const toggle = wrapper.querySelector("[data-toggle-password-button]");

    if (!input || !toggle) return;

    toggle.addEventListener("click", () => {
      const isHidden = input.type === "password";
      input.type = isHidden ? "text" : "password";
      toggle.setAttribute("aria-pressed", String(isHidden));

      const showIcon = toggle.querySelector("[data-icon-show]");
      const hideIcon = toggle.querySelector("[data-icon-hide]");
      if (showIcon && hideIcon) {
        showIcon.classList.toggle("d-none", isHidden);
        hideIcon.classList.toggle("d-none", !isHidden);
      }
    });
  });
});
