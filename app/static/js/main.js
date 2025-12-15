// custom scripts here

const initPasswordToggles = () => {
  document.querySelectorAll("[data-toggle-password]").forEach((wrapper) => {
    const input = wrapper.querySelector("[data-password-target]");
    const toggle = wrapper.querySelector("[data-toggle-password-button]");
    if (!input || !toggle) return;

    toggle.addEventListener("click", () => {
      const isCurrentlyHidden = input.type === "password";
      input.type = isCurrentlyHidden ? "text" : "password";
      toggle.setAttribute("aria-pressed", String(isCurrentlyHidden));

      const showIcon = toggle.querySelector("[data-icon-show]");
      const hideIcon = toggle.querySelector("[data-icon-hide]");
      if (showIcon && hideIcon) {
        showIcon.classList.toggle("d-none", isCurrentlyHidden);
        hideIcon.classList.toggle("d-none", !isCurrentlyHidden);
      }
    });
  });
};

const initProductImagePreview = () => {
  const urlInput = document.querySelector("[data-product-gallery-url]");
  const fileInput = document.querySelector("[data-product-gallery-files]");
  const previewContainer = document.querySelector("[data-product-image-preview-card]");
  const previewImage = previewContainer?.querySelector("[data-product-image-preview]");
  const placeholder = previewContainer?.querySelector("[data-product-image-placeholder]");
  if (!previewContainer || !previewImage) return;

  const initialSrc = previewImage.dataset.initialSrc || "";

  const togglePreviewDisplay = (hasImage) => {
    previewImage.classList.toggle("d-none", !hasImage);
    if (placeholder) {
      placeholder.classList.toggle("d-none", hasImage);
    }
  };

  const showPreview = (src) => {
    if (!src) {
      resetPreview();
      return;
    }
    previewImage.src = src;
    togglePreviewDisplay(true);
  };

  const resetPreview = () => {
    if (initialSrc) {
      previewImage.src = initialSrc;
      togglePreviewDisplay(true);
    } else {
      previewImage.removeAttribute("src");
      togglePreviewDisplay(false);
    }
  };

  const updateFromInputs = () => {
    const file = fileInput?.files && fileInput.files.length ? fileInput.files[0] : null;
    if (file) {
      if (!file.type || !file.type.startsWith("image/")) {
        resetPreview();
        return;
      }
      const reader = new FileReader();
      reader.onload = (event) => {
        const result = typeof event.target?.result === "string" ? event.target.result : "";
        showPreview(result);
      };
      reader.readAsDataURL(file);
      return;
    }

    const rawUrls = urlInput?.value || "";
    const firstUrl = rawUrls
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean)[0];
    if (firstUrl) {
      showPreview(firstUrl);
      return;
    }

    resetPreview();
  };

  urlInput?.addEventListener("input", () => {
    if (fileInput?.files?.length) {
      return;
    }
    updateFromInputs();
  });

  fileInput?.addEventListener("change", () => {
    updateFromInputs();
  });

  updateFromInputs();
};

const initScripts = () => {
  initPasswordToggles();
  initProductImagePreview();
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initScripts);
} else {
  initScripts();
}
