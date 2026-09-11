(function () {
  "use strict";

  var titlesEl = document.getElementById("titles-data");
  var titles = titlesEl ? JSON.parse(titlesEl.textContent) : [];
  var titlesLower = titles.map(function (t) { return t.toLowerCase(); });
  var MAX_RESULTS = 10;
  var DEBOUNCE_MS = 150;

  function filterTitles(query) {
    var q = query.toLowerCase();
    var matches = [];
    for (var i = 0; i < titles.length && matches.length < MAX_RESULTS; i++) {
      if (titlesLower[i].indexOf(q) !== -1) {
        matches.push(titles[i]);
      }
    }
    return matches;
  }

  function Autocomplete(input) {
    this.input = input;
    this.activeIndex = -1;
    this.options = [];
    this.debounceTimer = null;

    this.list = document.createElement("ul");
    this.list.className = "autocomplete-list";
    this.list.setAttribute("role", "listbox");
    this.list.id = input.id + "-listbox";
    this.list.hidden = true;
    input.insertAdjacentElement("afterend", this.list);
    input.parentElement.style.position = "relative";

    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-controls", this.list.id);
    input.setAttribute("autocomplete", "off");

    input.addEventListener("input", this.onInput.bind(this));
    input.addEventListener("keydown", this.onKeyDown.bind(this));
    input.addEventListener("blur", this.onBlur.bind(this));
  }

  Autocomplete.prototype.onInput = function () {
    var value = this.input.value;
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(function () {
      if (!value) {
        this.close();
        return;
      }
      this.setResults(filterTitles(value));
    }.bind(this), DEBOUNCE_MS);
  };

  Autocomplete.prototype.setResults = function (matches) {
    this.list.innerHTML = "";
    this.options = [];
    this.activeIndex = -1;

    if (matches.length === 0) {
      this.close();
      return;
    }

    matches.forEach(function (title, i) {
      var li = document.createElement("li");
      li.className = "autocomplete-option";
      li.setAttribute("role", "option");
      li.id = this.list.id + "-opt-" + i;
      li.setAttribute("aria-selected", "false");
      li.textContent = title;
      li.addEventListener("mousedown", function (e) {
        e.preventDefault();
        this.selectOption(li);
      }.bind(this));
      this.list.appendChild(li);
      this.options.push(li);
    }.bind(this));

    this.open();
  };

  Autocomplete.prototype.open = function () {
    this.list.hidden = false;
    this.input.setAttribute("aria-expanded", "true");
  };

  Autocomplete.prototype.close = function () {
    this.list.hidden = true;
    this.list.innerHTML = "";
    this.options = [];
    this.activeIndex = -1;
    this.input.setAttribute("aria-expanded", "false");
    this.input.removeAttribute("aria-activedescendant");
  };

  Autocomplete.prototype.moveActive = function (delta) {
    if (this.options.length === 0) {
      return;
    }
    var next = this.activeIndex + delta;
    next = Math.max(0, Math.min(this.options.length - 1, next));
    this.setActive(next);
  };

  Autocomplete.prototype.setActive = function (index) {
    if (this.activeIndex >= 0 && this.options[this.activeIndex]) {
      this.options[this.activeIndex].setAttribute("aria-selected", "false");
    }
    this.activeIndex = index;
    var option = this.options[index];
    if (option) {
      option.setAttribute("aria-selected", "true");
      this.input.setAttribute("aria-activedescendant", option.id);
      option.scrollIntoView({ block: "nearest" });
    }
  };

  Autocomplete.prototype.selectOption = function (li) {
    this.input.value = li.textContent;
    this.close();
  };

  Autocomplete.prototype.selectActive = function () {
    if (this.activeIndex >= 0 && this.options[this.activeIndex]) {
      this.selectOption(this.options[this.activeIndex]);
      return true;
    }
    return false;
  };

  Autocomplete.prototype.onKeyDown = function (e) {
    if (this.list.hidden) {
      return;
    }
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        this.moveActive(1);
        break;
      case "ArrowUp":
        e.preventDefault();
        this.moveActive(-1);
        break;
      case "Enter":
        if (this.selectActive()) {
          e.preventDefault();
        }
        break;
      case "Escape":
        this.close();
        break;
    }
  };

  Autocomplete.prototype.onBlur = function () {
    setTimeout(this.close.bind(this), 100);
  };

  document.querySelectorAll("input[data-autocomplete]").forEach(function (el) {
    new Autocomplete(el);
  });

  var form = document.getElementById("form");
  var submitBtn = document.getElementById("submit");
  var spinner = document.getElementById("loading");

  if (form) {
    form.addEventListener("submit", function () {
      submitBtn.disabled = true;
      submitBtn.setAttribute("aria-busy", "true");
      submitBtn.value = "Searching…";
      spinner.style.display = "inline-block";
    });
  }
})();
