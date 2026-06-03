"""认证安全策略 + 口令哈希单测 —— 纯逻辑,无 DB/IO,CI 可跑。"""
from app.auth.passwords import hash_password, verify_password
from app.auth.security import (
    MAX_PASSWORD_LEN,
    lock_state,
    next_locked_until,
    password_error,
    username_error,
)


# ---------- username_error ----------
def test_username_valid_ascii():
    assert username_error("alice") is None


def test_username_valid_chinese():
    assert username_error("李哲") is None


def test_username_valid_demo_hyphen():
    # 演示账号 demo-001 同时充当 user_id,连字符必须放行
    assert username_error("demo-001") is None


def test_username_empty_or_blank():
    assert username_error("") is not None
    assert username_error("   ") is not None


def test_username_illegal_char():
    assert username_error("bad name!") is not None  # 空格 + 叹号


def test_username_too_long():
    assert username_error("x" * 65) is not None


# ---------- password_error ----------
def test_password_too_short():
    assert password_error("12345") is not None


def test_password_min_ok():
    assert password_error("123456") is None


def test_password_too_long():
    assert password_error("x" * (MAX_PASSWORD_LEN + 1)) is not None


# ---------- lock_state ----------
def test_lock_state_none_not_locked():
    assert lock_state(None, 1000).locked is False


def test_lock_state_past_not_locked():
    assert lock_state(900, 1000).locked is False


def test_lock_state_future_locked():
    ls = lock_state(1100, 1000)
    assert ls.locked is True
    assert ls.retry_after_seconds == 100


def test_retry_after_minutes_ceil():
    # 61 秒应向上取整为 2 分钟(「请 N 分钟后再试」更符合直觉)
    assert lock_state(1061, 1000).retry_after_minutes == 2


# ---------- next_locked_until ----------
def test_next_locked_below_threshold():
    assert next_locked_until(4, 5, 15, 1000) is None


def test_next_locked_at_threshold():
    assert next_locked_until(5, 5, 15, 1000) == 1000 + 15 * 60


# ---------- passwords roundtrip ----------
def test_hash_verify_roundtrip():
    h = hash_password("s3cret-pw")
    assert verify_password("s3cret-pw", h) is True
    assert verify_password("wrong", h) is False


def test_hash_is_salted():
    # 同口令两次哈希应不同(随机盐),杜绝彩虹表
    assert hash_password("same") != hash_password("same")


def test_verify_empty_hash_false():
    assert verify_password("anything", "") is False


def test_verify_corrupted_hash_false():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_long_password_not_truncated():
    # bcrypt 原生只取前 72 字节会静默截断;预散列后超长口令仍能稳定区分
    base = "x" * 100
    h = hash_password(base + "A")
    assert verify_password(base + "A", h) is True
    assert verify_password(base + "B", h) is False
