(function () {
  "use strict";

  var titlesEl = document.getElementById("titles-data");
  var titles = titlesEl ? JSON.parse(titlesEl.textContent) : [];
  var titleStrings = titles.map(function (t) { return t.title; });
  var titlesLower = titleStrings.map(function (t) { return t.toLowerCase(); });
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

  function levenshteinDistance(a, b) {
    var prevRow = [];
    for (var j = 0; j <= b.length; j++) {
      prevRow[j] = j;
    }
    for (var i = 1; i <= a.length; i++) {
      var currRow = [i];
      for (j = 1; j <= b.length; j++) {
        var cost = a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1;
        currRow[j] = Math.min(
          prevRow[j] + 1,
          currRow[j - 1] + 1,
          prevRow[j - 1] + cost
        );
      }
      prevRow = currRow;
    }
    return prevRow[b.length];
  }

  // Compares the query against just the lead of a longer candidate, so a
  // typo'd/truncated prefix of a long title (e.g. "Declaration of
  // Independance") isn't penalized for the rest of that title it never
  // typed, and doesn't lose out to an unrelated short title that happens to
  // be closer in raw length.
  function anchoredDistance(q, candidateLower) {
    var compareTo = candidateLower.length > q.length
      ? candidateLower.slice(0, q.length)
      : candidateLower;
    return levenshteinDistance(q, compareTo);
  }

  function closestTitle(query) {
    var q = query.toLowerCase();
    var candidates = filterTitles(query);
    if (candidates.length === 0) {
      candidates = titles;
    }
    var best = null;
    var bestDist = Infinity;
    for (var i = 0; i < candidates.length; i++) {
      var dist = anchoredDistance(q, candidates[i].title.toLowerCase());
      if (dist < bestDist) {
        bestDist = dist;
        best = candidates[i];
      }
    }
    return best;
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

    matches.forEach(function (item, i) {
      var li = document.createElement("li");
      li.className = "autocomplete-option";
      li.setAttribute("role", "option");
      li.id = this.list.id + "-opt-" + i;
      li.setAttribute("aria-selected", "false");
      li.dataset.title = item.title;

      var titleEl = document.createElement("span");
      titleEl.className = "autocomplete-option__title";
      titleEl.textContent = item.title;
      li.appendChild(titleEl);

      if (item.author) {
        var authorEl = document.createElement("span");
        authorEl.className = "autocomplete-option__author";
        authorEl.textContent = item.author;
        li.appendChild(authorEl);
      }

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
    this.input.value = li.dataset.title;
    this.close();
  };

  Autocomplete.prototype.selectActive = function () {
    var index = this.activeIndex >= 0 ? this.activeIndex : 0;
    if (this.options[index]) {
      this.selectOption(this.options[index]);
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
    setTimeout(function () {
      this.close();
      var value = this.input.value.trim();
      if (!value) {
        return;
      }
      var idx = titlesLower.indexOf(value.toLowerCase());
      if (idx !== -1) {
        this.input.value = titles[idx].title;
        return;
      }
      var match = closestTitle(value);
      if (match) {
        this.input.value = match.title;
      }
    }.bind(this), 100);
  };

  document.querySelectorAll("input[data-autocomplete]").forEach(function (el) {
    new Autocomplete(el);
  });

  (function setRandomPlaceholders() {
    var box1 = document.getElementById("tags");
    var box2 = document.getElementById("tags2");
    if (!box1 || !box2) {
      return;
    }
    var nonEmpty = titleStrings.filter(function (t) { return t; });
    if (nonEmpty.length < 2) {
      return;
    }
    var i = Math.floor(Math.random() * nonEmpty.length);
    var j;
    do {
      j = Math.floor(Math.random() * nonEmpty.length);
    } while (j === i);
    box1.placeholder = nonEmpty[i];
    box2.placeholder = nonEmpty[j];
  })();

  var form = document.getElementById("form");
  var submitBtn = document.getElementById("submit");
  var loadingBar = document.getElementById("loading");

  if (form) {
    form.addEventListener("submit", function () {
      submitBtn.disabled = true;
      submitBtn.setAttribute("aria-busy", "true");
      submitBtn.value = "Searching…";
      loadingBar.style.display = "block";
      loadingBar.removeAttribute("aria-hidden");
    });
  }
})();
