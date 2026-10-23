import os
import threading
import time
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class MovieProviderError(RuntimeError):
    pass


class TMDBMovieProvider:
    API_URL = "https://api.themoviedb.org/3"
    IMAGE_URL = "/movies/poster/"
    GENRES = {
        "all": ("Все фильмы", "All movies", None),
        "drama": ("Драма", "Drama", 18),
        "romance": ("Мелодрама", "Romance", 10749),
        "comedy": ("Комедия", "Comedy", 35),
        "action": ("Боевик", "Action", 28),
        "science-fiction": ("Фантастика", "Science fiction", 878),
        "horror": ("Ужасы", "Horror", 27),
        "adventure": ("Приключения", "Adventure", 12),
        "crime": ("Криминал", "Crime", 80),
        "mystery": ("Детектив", "Mystery", 9648),
    }
    GENRE_NAMES = {
        value[2]: value[0].lower()
        for value in GENRES.values()
        if value[2] is not None
    }

    def __init__(self, session=None):
        self.api_key = os.environ.get("TMDB_API_KEY", "").strip()
        self.bearer_token = os.environ.get("TMDB_BEARER_TOKEN", "").strip()
        self.pages = max(1, min(int(os.environ.get("TMDB_CATALOG_PAGES", "5")), 10))
        self.cache_ttl = max(60, int(os.environ.get("TMDB_CACHE_TTL", "900")))
        self.session = session
        self._cache = {}
        self._lock = threading.Lock()

    def genre_options(self):
        return [
            {
                "key": key,
                "title": title,
                "title_en": title_en,
                "movie_count": 0,
            }
            for key, (title, title_en, _) in self.GENRES.items()
        ]

    def catalog(self, genre_key):
        if genre_key not in self.GENRES:
            raise MovieProviderError("Неизвестный жанр фильма")
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(genre_key)
            if cached and now - cached[0] < self.cache_ttl:
                return cached[1]

        ru_results = self._discover(genre_key, "ru-RU")
        en_results = {
            movie["id"]: movie for movie in self._discover(genre_key, "en-US")
        }
        movies = [
            self._movie(movie, en_results.get(movie["id"], {}))
            for movie in ru_results
            if movie.get("id") and movie.get("title") and movie.get("poster_path")
        ]
        if not movies:
            raise MovieProviderError("TMDB не вернул фильмы для выбранного жанра")
        with self._lock:
            self._cache[genre_key] = (now, movies)
        return movies

    def _discover(self, genre_key, language):
        if not self.api_key and not self.bearer_token:
            raise MovieProviderError(
                "Онлайн-каталог не настроен: добавьте TMDB_API_KEY или TMDB_BEARER_TOKEN"
            )
        genre_id = self.GENRES[genre_key][2]
        headers = {}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        results = []
        for page in range(1, self.pages + 1):
            params = {
                "language": language,
                "page": page,
                "include_adult": "false",
                "include_video": "false",
                "sort_by": "popularity.desc",
                "vote_count.gte": 100,
            }
            if self.api_key:
                params["api_key"] = self.api_key
            if genre_id is not None:
                params["with_genres"] = genre_id
            try:
                if self.session is not None:
                    response = self.session.get(
                        f"{self.API_URL}/discover/movie",
                        params=params,
                        headers=headers,
                        timeout=12,
                    )
                    response.raise_for_status()
                    payload = response.json()
                else:
                    url = f"{self.API_URL}/discover/movie?{urlencode(params)}"
                    request = Request(url, headers=headers)
                    with urlopen(request, timeout=12) as response:
                        payload = json.loads(response.read().decode("utf-8"))
            except (HTTPError, URLError, OSError, ValueError) as error:
                raise MovieProviderError(f"Не удалось загрузить фильмы из TMDB: {error}") from error
            results.extend(payload.get("results") or [])
            if page >= int(payload.get("total_pages") or page):
                break
        return results

    def _movie(self, ru, en):
        release_date = ru.get("release_date") or en.get("release_date") or ""
        genre_ids = ru.get("genre_ids") or en.get("genre_ids") or []
        return {
            "id": int(ru["id"]),
            "title": ru.get("title") or en.get("title") or "",
            "title_en": en.get("title") or ru.get("original_title") or "",
            "overview": ru.get("overview") or "",
            "overview_en": en.get("overview") or "",
            "release_year": int(release_date[:4]) if release_date[:4].isdigit() else None,
            "poster_url": self.IMAGE_URL + ru["poster_path"].lstrip("/"),
            "genres": [self.GENRE_NAMES[g] for g in genre_ids if g in self.GENRE_NAMES],
            "runtime_min": None,
            "rating": round(float(ru.get("vote_average") or 0), 1),
            "rating_source": "TMDB",
        }
