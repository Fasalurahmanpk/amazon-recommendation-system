import { useEffect, useId, useRef, useState } from "react";
import { DOMAINS } from "../constants";
import { searchItems } from "../services/recommendationApi";
import useDebouncedValue from "../hooks/useDebouncedValue";
import { AlertIcon, SearchIcon } from "./icons";

const MIN_CHARS = 2;

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Wrap query words found in `title` with <mark> for visual feedback.
function Highlighted({ title, query }) {
  const tokens = query.split(/\s+/).filter(Boolean).map(escapeRegExp);
  if (!tokens.length) return title;
  const pattern = new RegExp(`(${tokens.join("|")})`, "ig");
  const matcher = new RegExp(`^(${tokens.join("|")})$`, "i");
  return title
    .split(pattern)
    .map((part, index) =>
      matcher.test(part) ? <mark key={index}>{part}</mark> : part
    );
}

function formatMeta(item) {
  const parts = [];
  if (item.num_ratings) parts.push(`${item.num_ratings.toLocaleString()} ratings`);
  if (typeof item.price === "number") parts.push(`$${item.price.toFixed(2)}`);
  return parts.join(" · ");
}

export default function SearchBar({ domain, onSelect }) {
  const config = DOMAINS[domain];
  const listboxId = useId();
  const wrapperRef = useRef(null);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const trimmed = query.trim();
  const debounced = useDebouncedValue(trimmed, 350);
  const isTyping = trimmed.length >= MIN_CHARS && trimmed !== debounced;
  const isLoading = status === "loading" || isTyping;

  // Fetch suggestions for the debounced query; cancel stale requests.
  useEffect(() => {
    if (debounced.length < MIN_CHARS) {
      setResults([]);
      setStatus("idle");
      setError(null);
      return undefined;
    }
    const controller = new AbortController();
    setStatus("loading");
    setError(null);
    searchItems(domain, debounced, { signal: controller.signal })
      .then((data) => {
        setResults(data.results);
        setStatus("done");
        setActiveIndex(-1);
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        setResults([]);
        setError(err);
        setStatus("error");
      });
    return () => controller.abort();
  }, [debounced, domain]);

  // Close the dropdown when clicking outside.
  useEffect(() => {
    function onPointerDown(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  function choose(item) {
    setOpen(false);
    setQuery("");
    setResults([]);
    setStatus("idle");
    onSelect(item);
  }

  function onKeyDown(event) {
    if (event.key === "Escape") {
      setOpen(false);
      return;
    }
    if (!results.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((index) => (index + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => (index <= 0 ? results.length - 1 : index - 1));
    } else if (event.key === "Enter" && open && activeIndex >= 0) {
      event.preventDefault();
      choose(results[activeIndex]);
    }
  }

  const showPanel = open && trimmed.length >= MIN_CHARS;
  const showEmpty = showPanel && status === "done" && !isTyping && results.length === 0;

  return (
    <div className="search" ref={wrapperRef}>
      <label className="field-label" htmlFor={`${listboxId}-input`}>
        {config.searchLabel}
      </label>
      <div className="search__box">
        <SearchIcon className="search__icon" />
        <input
          id={`${listboxId}-input`}
          type="text"
          className="search__input"
          placeholder={config.searchPlaceholder}
          value={query}
          autoComplete="off"
          spellCheck="false"
          role="combobox"
          aria-expanded={showPanel}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={
            activeIndex >= 0 ? `${listboxId}-opt-${activeIndex}` : undefined
          }
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
        />
        {isLoading && <span className="spinner" aria-label="Searching" />}
      </div>

      {showPanel && (
        <div className="suggestions" id={listboxId} role="listbox">
          {isLoading && results.length === 0 && (
            <p className="suggestions__note">Searching...</p>
          )}

          {status === "error" && !isTyping && (
            <p className="suggestions__note suggestions__note--error">
              <AlertIcon /> {error && error.message}
            </p>
          )}

          {showEmpty && (
            <p className="suggestions__note">
              No matches for “{debounced}”. Try fewer or different words.
            </p>
          )}

          {results.map((item, index) => (
            <button
              type="button"
              key={item.item_id}
              id={`${listboxId}-opt-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              className={`suggestion ${index === activeIndex ? "is-active" : ""}`}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => choose(item)}
            >
              <span className="suggestion__title">
                <Highlighted title={item.product_title} query={debounced} />
              </span>
              <span className="suggestion__meta">{formatMeta(item)}</span>
            </button>
          ))}
        </div>
      )}

      {trimmed.length === 0 && (
        <p className="search__hint">
          Try:{" "}
          {config.examples.map((example) => (
            <button
              type="button"
              key={example}
              className="link-chip"
              onClick={() => {
                setQuery(example);
                setOpen(true);
              }}
            >
              {example}
            </button>
          ))}
        </p>
      )}
      {trimmed.length > 0 && trimmed.length < MIN_CHARS && (
        <p className="search__hint">Type at least {MIN_CHARS} characters.</p>
      )}
    </div>
  );
}
