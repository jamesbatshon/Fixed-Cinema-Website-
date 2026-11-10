/*
 * SCREENLANE INTERACTIONS
 * All monetary values shown here are estimates only. The server always
 * recomputes and validates the final booking total before saving it.
 */
(() => {
  "use strict";

  const menuButton = document.querySelector("[data-mobile-toggle]");
  const nav = document.querySelector("#primary-nav");
  if (menuButton && nav) {
    menuButton.addEventListener("click", () => {
      const open = nav.classList.toggle("is-open");
      menuButton.setAttribute("aria-expanded", String(open));
    });
  }

  document.querySelectorAll("[data-dismiss-alert]").forEach(button => {
    button.addEventListener("click", () => button.closest(".alert")?.remove());
  });

  document.querySelectorAll("[data-print]").forEach(button => {
    button.addEventListener("click", () => window.print());
  });

  document.querySelectorAll("[data-confirm]").forEach(form => {
    form.addEventListener("submit", event => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  const search = document.querySelector("#movie-search");
  const chips = [...document.querySelectorAll("[data-genre]")];
  const cards = [...document.querySelectorAll("[data-movie-card]")];
  const emptyMessage = document.querySelector("#movie-search-empty");
  let activeGenre = "all";
  const filterMovies = () => {
    const text = (search?.value || "").toLocaleLowerCase().trim();
    let count = 0;
    cards.forEach(card => {
      const matches = card.dataset.title.includes(text) &&
        (activeGenre === "all" || card.dataset.genre === activeGenre);
      card.hidden = !matches;
      if (matches) count++;
    });
    if (emptyMessage) emptyMessage.hidden = count !== 0;
  };
  search?.addEventListener("input", filterMovies);
  chips.forEach(chip => chip.addEventListener("click", () => {
    activeGenre = chip.dataset.genre;
    chips.forEach(other => {
      const selected = other === chip;
      other.classList.toggle("is-selected", selected);
      other.setAttribute("aria-pressed", String(selected));
    });
    filterMovies();
  }));

  const packageSelector = document.querySelector("[data-kind-select]");
  const componentSection = document.querySelector("#components-section");
  const priceLabel = document.querySelector("#price-label");
  if (packageSelector && componentSection) {
    const updateKind = () => {
      const isPackage = packageSelector.value === "package";
      componentSection.hidden = !isPackage;
      if (priceLabel) priceLabel.textContent = isPackage ? "Discounted food add-on (€) *" : "Price (€) *";
      componentSection.querySelectorAll("input").forEach(input => {
        if (!input.hasAttribute("data-always-disabled")) input.disabled = !isPackage;
      });
    };
    packageSelector.addEventListener("change", updateKind);
    updateKind();
  }

  const bookingForm = document.querySelector("#booking-form");
  if (bookingForm) {
    const seatInput = document.querySelector("[data-seat-count]");
    const productInputs = [...bookingForm.querySelectorAll("[data-product-price]")];
    const ticketPrice = Number(bookingForm.dataset.ticketPrice);
    const euro = value => new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR" }).format(value);
    const integerValue = input => {
      const value = Number(input.value);
      return Number.isInteger(value) && value >= 0 ? value : 0;
    };
    const warning = document.querySelector("#booking-warning");
    const confirmButton = document.querySelector('button[form="booking-form"]');

    const calculate = () => {
      const seats = integerValue(seatInput);
      const packages = productInputs.filter(input => input.dataset.isPackage === "true")
        .reduce((sum, input) => sum + integerValue(input), 0);
      const regularSeats = Math.max(0, seats - packages);
      const ticketSubtotal = regularSeats * ticketPrice;
      let total = ticketSubtotal;
      const summary = document.querySelector("#extras-summary");
      if (summary) summary.replaceChildren();
      productInputs.forEach(input => {
        const qty = integerValue(input);
        if (!qty) return;
        const price = Number(input.dataset.productPrice) * qty;
        total += price;
        const name = input.closest(".order-option")?.querySelector(".option-copy strong")?.textContent || "Extra";
        const row = document.createElement("div");
        row.className = "summary-row";
        const label = document.createElement("span");
        label.textContent = `${qty} × ${name}`;
        const amount = document.createElement("strong");
        amount.textContent = euro(price);
        row.append(label, amount);
        summary?.append(row);
      });
      const invalid = packages > seats || seats < 1 || seats > Number(seatInput.max);
      if (warning) warning.hidden = !invalid;
      if (confirmButton) confirmButton.disabled = invalid;
      const ticketCount = document.querySelector("#regular-ticket-count");
      if (ticketCount) ticketCount.textContent = String(regularSeats);
      const subtotal = document.querySelector("#ticket-subtotal");
      if (subtotal) subtotal.textContent = euro(ticketSubtotal);
      const grandTotal = document.querySelector("#order-total");
      if (grandTotal) grandTotal.textContent = euro(total);
      return !invalid;
    };
    bookingForm.addEventListener("input", calculate);
    bookingForm.addEventListener("submit", event => {
      if (!calculate()) event.preventDefault();
    });
    calculate();
  }

  document.querySelectorAll("[data-adjust]").forEach(button => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.target);
      if (!input || input.disabled) return;
      const min = Number(input.min || 0);
      const max = Number(input.max || 999);
      const current = Number.isFinite(Number(input.value)) ? Number(input.value) : min;
      input.value = String(Math.max(min, Math.min(max, current + Number(button.dataset.adjust))));
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
  });
})();
