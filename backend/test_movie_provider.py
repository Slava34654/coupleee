import pytest

from movie_provider import MovieProviderError, TMDBMovieProvider


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class Session:
    def __init__(self):
        self.calls = []

    def get(self, url, params, headers, timeout):
        self.calls.append((url, params, headers, timeout))
        english = params["language"] == "en-US"
        return Response({
            "total_pages": 1,
            "results": [{
                "id": 42,
                "title": "Test Movie" if english else "Тестовый фильм",
                "original_title": "Test Movie",
                "overview": "Overview" if english else "Описание",
                "release_date": "2025-03-10",
                "poster_path": "/poster.jpg",
                "genre_ids": [18, 878],
                "vote_average": 8.26,
            }],
        })


def test_tmdb_catalog_is_online_transformed_and_memory_cached(monkeypatch):
    monkeypatch.setenv("TMDB_API_KEY", "test-key")
    session = Session()
    provider = TMDBMovieProvider(session=session)

    first = provider.catalog("science-fiction")
    second = provider.catalog("science-fiction")

    assert first is second
    assert len(session.calls) == 2
    assert session.calls[0][1]["with_genres"] == 878
    assert session.calls[0][1]["api_key"] == "test-key"
    assert first == [{
        "id": 42,
        "title": "Тестовый фильм",
        "title_en": "Test Movie",
        "overview": "Описание",
        "overview_en": "Overview",
        "release_year": 2025,
        "poster_url": "/movies/poster/poster.jpg",
        "genres": ["драма", "фантастика"],
        "runtime_min": None,
        "rating": 8.3,
        "rating_source": "TMDB",
    }]


def test_tmdb_catalog_requires_credentials(monkeypatch):
    monkeypatch.delenv("TMDB_API_KEY", raising=False)
    monkeypatch.delenv("TMDB_BEARER_TOKEN", raising=False)
    provider = TMDBMovieProvider(session=Session())

    with pytest.raises(MovieProviderError, match="TMDB_API_KEY"):
        provider.catalog("drama")


def test_genre_options_use_horror_and_hide_removed_categories(monkeypatch):
    monkeypatch.setenv("TMDB_API_KEY", "test-key")
    keys = {item["key"] for item in TMDBMovieProvider().genre_options()}

    assert "horror" in keys
    assert not {"thriller", "animation", "family", "music", "fantasy"} & keys
