"""Tezlik cheklovchi va yuboruvchi (Redis: fakeredis, Telegram: soxta sessiya)."""

import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from aiogram.methods import SendMessage

from ilmbot.integrations.rate_limiter import RateLimiter
from ilmbot.integrations.telegram_sender import SendResult, TelegramSender
from tests.bot_harness import make_bot


class FakeTime:
    """Soxta soat: `sleep` vaqtni oldinga suradi."""

    def __init__(self, now: float = 1000.05):
        self.now = now
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def method() -> SendMessage:
    return SendMessage(chat_id=1, text="x")


async def test_limiter_allows_the_window_quota_then_waits_for_the_next_window(redis):
    time = FakeTime()
    limiter = RateLimiter(redis, per_second=10, clock=time.clock, sleep=time.sleep)  # oynada 2 ta

    await limiter.acquire()
    await limiter.acquire()
    assert time.sleeps == []

    await limiter.acquire()  # uchinchisi keyingi oynagacha kutadi

    assert len(time.sleeps) == 1
    assert 0 < time.sleeps[0] <= 0.2 + 0.01


async def test_limit_is_shared_between_limiters_using_the_same_redis(redis):
    """Bot va worker bir xil kalitdan foydalansa, umumiy limit saqlanadi."""
    time = FakeTime()
    first = RateLimiter(redis, per_second=5, clock=time.clock, sleep=time.sleep)  # oynada 1 ta
    second = RateLimiter(redis, per_second=5, clock=time.clock, sleep=time.sleep)

    await first.acquire()
    await second.acquire()

    assert len(time.sleeps) == 1


async def test_throughput_never_exceeds_the_configured_rate(redis):
    time = FakeTime()
    limiter = RateLimiter(redis, per_second=25, clock=time.clock, sleep=time.sleep)
    start = time.now

    for _ in range(250):
        await limiter.acquire()

    elapsed = time.now - start
    assert 9.0 < elapsed < 10.5  # 250 xabar / 25 s ~ 10 soniya


def make_sender(redis, time: FakeTime | None = None):
    time = time or FakeTime()
    limiter = RateLimiter(redis, per_second=10_000, clock=time.clock, sleep=time.sleep)
    return TelegramSender(limiter, sleep=time.sleep), time, make_bot()


async def test_successful_send(redis):
    sender, _, bot = make_sender(redis)

    result = await sender.send_text(bot, 42, "salom")

    assert result is SendResult.SENT
    assert [(r.chat_id, r.text) for r in bot.session.requests] == [(42, "salom")]


async def test_blocked_user_is_reported_without_retrying(redis):
    sender, _, bot = make_sender(redis)
    bot.session.fail_when(
        lambda m: isinstance(m, SendMessage),
        TelegramForbiddenError(method(), "Forbidden: bot was blocked by the user"),
    )

    assert await sender.send_text(bot, 42, "salom") is SendResult.BLOCKED
    assert bot.session.requests == []


async def test_flood_control_waits_then_retries(redis):
    sender, time, bot = make_sender(redis)
    bot.session.fail_when(
        lambda m: isinstance(m, SendMessage),
        TelegramRetryAfter(method(), "Too Many Requests", retry_after=3),
    )

    result = await sender.send_text(bot, 42, "salom")

    assert result is SendResult.SENT
    assert 3.5 in time.sleeps


async def test_bad_request_fails_without_retrying(redis):
    sender, _, bot = make_sender(redis)
    bot.session.fail_when(
        lambda m: isinstance(m, SendMessage), TelegramBadRequest(method(), "Bad Request: chat not found")
    )

    assert await sender.send_text(bot, 42, "salom") is SendResult.FAILED


@pytest.mark.parametrize("failures", [1, 2])
async def test_network_errors_are_retried(redis, failures):
    sender, _, bot = make_sender(redis)
    for _ in range(failures):
        bot.session.fail_when(lambda m: isinstance(m, SendMessage), TelegramNetworkError(method(), "timeout"))

    assert await sender.send_text(bot, 42, "salom") is SendResult.SENT


async def test_persistent_network_errors_give_up(redis):
    sender, _, bot = make_sender(redis)
    for _ in range(3):
        bot.session.fail_when(lambda m: isinstance(m, SendMessage), TelegramNetworkError(method(), "timeout"))

    assert await sender.send_text(bot, 42, "salom") is SendResult.FAILED
