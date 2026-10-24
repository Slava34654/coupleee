from typing import Literal, Optional

from pydantic import BaseModel


# ---------------- модели ----------------
class PairIn(BaseModel):
    name: str
    birth: str = ""  # YYYY-MM-DD, необязательна (приложение может не слать)
    avatar: str = ""  # URL из POST /photos
    since: str = ""  # дата начала отношений YYYY-MM-DD, иначе сегодня


class JoinIn(BaseModel):
    name: str
    code: str
    birth: str = ""
    avatar: str = ""


class AuthRegisterIn(BaseModel):
    email: str
    password: str


class PairSetupIn(BaseModel):
    user_id: int
    name: str
    birth: str = ""
    avatar: str = ""
    since: str = ""
    partner_code: str = ""


class AvatarIn(BaseModel):
    user_id: int
    avatar: str


class AuthLoginIn(BaseModel):
    email: str
    password: str


class DeleteAccountIn(BaseModel):
    user_id: int
    password: str


class MoodIn(BaseModel):
    user_id: int
    mood: str
    note: str = ""


class AnswerIn(BaseModel):
    user_id: int
    text: str


class QuizAnswerIn(BaseModel):
    user_id: int
    qid: int
    option: int


class PackAnswerIn(BaseModel):
    user_id: int
    qid: int
    text: str = ""
    photo: str = ""


class IdeaIn(BaseModel):
    title: str
    category: str = ""
    budget: str = ""


class JournalIn(BaseModel):
    user_id: int
    title: str
    text: str = ""
    photo: str = ""  # URL из POST /photos


class EventIn(BaseModel):
    user_id: int
    title: str
    date: str  # YYYY-MM-DD
    icon: str = "🎉"
    repeat: bool = False


class TogetherIn(BaseModel):
    user_id: int
    date: str


class WishlistIn(BaseModel):
    user_id: int
    title: str
    photo: str = ""


class WishlistDoneIn(BaseModel):
    user_id: int
    done: bool


class LikeIn(BaseModel):
    user_id: int


class WidgetIn(BaseModel):
    user_id: int
    photo: str
    caption: str = ""


class TapIn(BaseModel):
    user_id: int


class LocationIn(BaseModel):
    user_id: int
    lat: float
    lon: float


class ExactWidgetConsentIn(BaseModel):
    user_id: int


class GameActionIn(BaseModel):
    user_id: int
    action: str
    value: Optional[int] = None


class CompanionProposalIn(BaseModel):
    user_id: int
    type: str
    name: str


class CompanionUserIn(BaseModel):
    user_id: int


class CompanionActionIn(BaseModel):
    user_id: int
    action: str
    value: str = ""


class PushTokenIn(BaseModel):
    user_id: int
    token: str
    platform: str = "android"


class MovieSwipeIn(BaseModel):
    user_id: int
    movie_id: int
    direction: str


class MovieUserIn(BaseModel):
    user_id: int


class MovieGenreIn(BaseModel):
    user_id: int
    genre_key: str


class MovieWatchIn(BaseModel):
    user_id: int
    movie_id: int
    watched: bool = True


class CommunityMapPostIn(BaseModel):
    user_id: int
    lat: float
    lon: float
    country_code: str = ""
    photo: str
    comment: str
    public_consent: bool


class CommunityMapUserIn(BaseModel):
    user_id: int


class CommunityMapReportIn(BaseModel):
    user_id: int
    reason: Literal["privacy", "spam", "inappropriate", "other"]


class CommunityMapLikeIn(BaseModel):
    user_id: int
    liked: bool


class CommunityMapCommentIn(BaseModel):
    user_id: int
    text: str


class CommunityMapCommentReportIn(BaseModel):
    user_id: int
    reason: Literal["privacy", "spam", "inappropriate", "other"]
