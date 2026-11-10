/*
 * Staff movie editor: changes are previewed locally until the form is saved.
 * The Flask endpoint performs authorization, validation and database updates.
 */
(() => {
  "use strict";

  const form = document.querySelector("#movie-edit-form");
  if (!form) return;

  const title = form.querySelector("[data-edit-title]");
  const genre = form.querySelector("[data-edit-genre]");
  const rating = form.querySelector("[data-edit-rating]");
  const poster = form.querySelector("[data-edit-poster]");
  const previewTitle = document.querySelector("[data-preview-title]");
  const previewGenre = document.querySelector("[data-preview-genre]");
  const previewRating = document.querySelector("[data-preview-rating]");
  const previewPoster = document.querySelector("[data-preview-poster]");
  const status = document.querySelector("[data-edit-status]");
  const fileError = document.querySelector("#poster-error");

  const originalPoster = previewPoster.src;
  let previewUrl = null;

  const releasePreview = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
  };

const validateImage = () => {
    const file = poster.files[0];
    let error = "";

    if (file) {
        const allowedExtensions = ["jpg", "jpeg", "png", "webp"];
        const extension = file.name.split(".").pop().toLowerCase();
        const allowedTypes = ["image/jpeg", "image/png", "image/webp"];

        if (!allowedExtensions.includes(extension) ||
            (file.type && !allowedTypes.includes(file.type))) {
            error = "Select a JPG, PNG or WebP image.";
        } else if (file.size > 3 * 1024 * 1024) {
            error = "Poster must be smaller than 3 MB.";
        }
    }

    poster.setCustomValidity(error);
    fileError.hidden = !error;
    fileError.textContent = error;

    return error === "";
};

  const updateText = () => {
    // textContent prevents user-entered HTML from being interpreted as markup.
    previewTitle.textContent = title.value.trim() || "Untitled movie";
    previewGenre.textContent = genre.value.trim() || "Film";
    previewRating.textContent = rating.value.trim() || "Not rated";
    previewPoster.alt = `Poster preview for ${previewTitle.textContent}`;
  };

  const updatePoster = () => {
    releasePreview();
    const file = poster.files?.[0];
    if (validateImage() && file) {
      previewUrl = URL.createObjectURL(file);
      previewPoster.src = previewUrl;
    } else {
      previewPoster.src = originalPoster;
    }
  };

  const markUnsaved = () => {
    status.textContent = "Unsaved changes";
    status.classList.add("is-dirty");
  };

  [title, genre, rating].forEach(input => {
    input.addEventListener("input", () => {
      updateText();
      markUnsaved();
    });
  });

  poster.addEventListener("change", () => {
    updatePoster();
    markUnsaved();
  });

  form.addEventListener("reset", () => {
    // The browser restores the original field values immediately after reset.
    window.setTimeout(() => {
      updateText();
      updatePoster();
      status.textContent = "Not saved";
      status.classList.remove("is-dirty");
    }, 0);
  });

  form.addEventListener("submit", event => {
    if (!validateImage()) {
      event.preventDefault();
      poster.reportValidity();
    }
  });

  window.addEventListener("pagehide", releasePreview);
  updateText();
})();
