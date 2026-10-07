// Shared UI configuration: domains and recommendation methods.
// Method keys match the backend: "hybrid" | "cf" | "content".

export const DOMAINS = {
  movies: {
    key: "movies",
    path: "/movies",
    navLabel: "Movies & TV",
    cardTag: "Movies & TV",
    title: "Movie Recommendations",
    subtitle:
      "Pick a movie or TV show you love and see which titles the models surface next.",
    searchLabel: "Search for a movie or TV show",
    searchPlaceholder: "Search for a movie or TV show...",
    itemNoun: "title",
    examples: ["batman", "the godfather", "star wars"],
  },
  games: {
    key: "games",
    path: "/games",
    navLabel: "Video Games",
    cardTag: "Video Games",
    title: "Game Recommendations",
    subtitle:
      "Pick a game you enjoy and discover similar titles ranked by the models.",
    searchLabel: "Search for a video game",
    searchPlaceholder: "Search for a video game...",
    itemNoun: "game",
    examples: ["zelda", "minecraft", "super mario"],
  },
};

export const DOMAIN_LIST = [DOMAINS.movies, DOMAINS.games];

export const METHODS = [
  {
    key: "hybrid",
    label: "Hybrid",
    short: "Hybrid RRF",
    description:
      "Fuses collaborative and content rankings with weighted Reciprocal Rank Fusion.",
  },
  {
    key: "cf",
    label: "Collaborative Filtering",
    short: "Collaborative",
    description:
      "Finds items that the same users rated similarly (item-based, cosine similarity).",
  },
  {
    key: "content",
    label: "Content-Based",
    short: "Content-Based",
    description:
      "Compares titles, descriptions and categories using TF-IDF similarity.",
  },
];

export const METHOD_BY_KEY = Object.fromEntries(METHODS.map((m) => [m.key, m]));

// Scores mean different things per method, so each gets its own label.
// None of them are probabilities.
export const SCORE_META = {
  content: {
    label: "Similarity",
    digits: 3,
    hint: "TF-IDF cosine similarity between item texts (0 to 1).",
  },
  cf: {
    label: "Similarity",
    digits: 3,
    hint: "Cosine similarity between item rating patterns (0 to 1).",
  },
  hybrid: {
    label: "RRF score",
    digits: 4,
    hint: "Weighted Reciprocal Rank Fusion score. A rank-based value, not a probability.",
  },
};
