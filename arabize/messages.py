"""What the player reads when something goes wrong: short, calm, and never suggesting the PC is in danger.

The technical detail (HTTP codes, exception text) goes to the log file, not on screen. Translation services are
other companies' servers on the internet: when one is slow or busy the program says so plainly, keeps the game
running, tries the next service and retries by itself.
"""
from __future__ import annotations

import re

# shown on the home page / status line
SERVICE_SLOW = "خدمة الترجمة بطيئة الآن — أجرّب خدمة أخرى تلقائياً، واللعبة تعمل كالمعتاد"
SERVICE_BUSY = "خدمة الترجمة مشغولة لحظياً — سأعيد المحاولة تلقائياً خلال ثوانٍ"
SERVICE_DOWN = "خدمة الترجمة لا تستجيب مؤقتاً — سأعيد المحاولة تلقائياً، ولا يلزمك فعل شيء"
NO_INTERNET = "الاتصال بالإنترنت متقطع — الترجمات المحفوظة تعمل، والجديدة تعود تلقائياً عند عودة الاتصال"
KEY_REJECTED = "مفتاح الخدمة غير مقبول — راجعه من صفحة «المحركات واللغة»، وتعمل المحركات المجانية حتى ذلك"
NO_ENGINE = "لا يوجد محرك ترجمة مفعّل — فعّل Google أو MyMemory من صفحة «المحركات واللغة»"
CAPTURE_HICCUP = "تعذّر أخذ صورة من اللعبة لحظياً — أعيد المحاولة تلقائياً"
RECOVERED = "عاد الاتصال بخدمة الترجمة — الترجمة تعمل"


def _codes(text: str) -> set[int]:
    return {int(c) for c in re.findall(r"HTTP (\d{3})", text or "")}


def translate_failure(errors: dict[str, str] | None, network: bool, internet: bool | None = None) -> tuple[str, str]:
    """(status code, Arabic message) for a line that no engine could translate.

    network: every engine failed to connect. internet: result of a quick reachability check when known
    (False = this PC is offline; True/None = the internet works, the service itself is the problem)."""
    errors = errors or {}
    if not errors:
        return "error", NO_ENGINE
    text = " ".join(errors.values())
    codes = _codes(text)
    if network:
        if internet is False:
            return "offline", NO_INTERNET
        if "timed out" in text.lower() or "timeout" in text.lower():
            return "offline", SERVICE_SLOW
        return "offline", SERVICE_DOWN
    if codes & {401, 403} or "المفتاح مرفوض" in text:
        if len(errors) == 1 or all(("مفتاح" in v or _codes(v) & {401, 403}) for v in errors.values()):
            return "warn", KEY_REJECTED
    if codes & {429}:
        return "warn", SERVICE_BUSY
    if codes & {500, 502, 503, 504, 529}:
        return "warn", SERVICE_DOWN
    return "warn", SERVICE_BUSY


def capture_failure(_exc: BaseException | str | None = None) -> str:
    return CAPTURE_HICCUP


def ocr_failure(detail: str = "") -> str:
    """The text reader could not start (very rare). detail is logged, not shown."""
    return "تعذّر تشغيل قارئ النص — جرّب «محرك القراءة» الآخر من صفحة «المحركات واللغة» (الوضع المتقدم)"


def engine_test_error(err: str) -> str:
    """One line for the engines test table: what it means for the user, not the raw server reply."""
    if not err:
        return ""
    if err == "يحتاج مفتاح API":
        return err
    codes = _codes(err)
    if codes & {401, 403} or "المفتاح" in err:
        return "المفتاح غير مقبول"
    if codes & {429}:
        return "مشغول الآن (حد الاستخدام) — جرّب بعد قليل"
    if codes & {500, 502, 503, 504, 529}:
        return "الخدمة لا تستجيب مؤقتاً"
    if "تعذّر الاتصال" in err:
        return "تعذّر الوصول إلى الخدمة (الإنترنت أو الخدمة نفسها)"
    return "رد غير متوقع من الخدمة"
