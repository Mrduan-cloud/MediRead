"""Tortoise-ORM 数据模型。"""
from __future__ import annotations

from tortoise import fields, models


class ReportModel(models.Model):
    report_id = fields.CharField(pk=True, max_length=64)
    user_id = fields.CharField(max_length=64, index=True)
    hospital = fields.CharField(max_length=128, null=True)
    sampled_at = fields.DatetimeField(null=True)
    source_object_key = fields.CharField(max_length=255)
    parsed_object_key = fields.CharField(max_length=255, null=True)
    indicators = fields.JSONField(default=list)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "report"


class InterpretationModel(models.Model):
    id = fields.IntField(pk=True)
    report_id = fields.CharField(max_length=64, index=True)
    user_id = fields.CharField(max_length=64, index=True)
    payload = fields.JSONField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "interpretation"


class AuditLog(models.Model):
    id = fields.IntField(pk=True)
    request_id = fields.CharField(max_length=64, index=True)
    user_id = fields.CharField(max_length=64, index=True)
    action = fields.CharField(max_length=64)
    payload = fields.JSONField(default=dict)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "audit_log"


class AuthAccount(models.Model):
    """登录凭证 —— 认证关注点独立成表。

    ``username`` 即 user_id(沿用全栈以 user_id 为中心的设计),口令、角色、
    停用、失败锁定等认证状态独立存储,与体检报告(ReportModel.user_id)解耦。
    """

    username = fields.CharField(pk=True, max_length=64)
    password_hash = fields.CharField(max_length=255)
    role = fields.CharField(max_length=16, default="user")  # user | admin
    is_demo = fields.BooleanField(default=False)  # 演示账号:登录页快速体验入口
    is_active = fields.BooleanField(default=True)  # 停用后无法登录
    failed_attempts = fields.IntField(default=0)
    # 锁定截止时间存 UTC 纪元秒(int):整数比较无时区歧义
    locked_until_ts = fields.BigIntField(null=True)
    last_login_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "auth_account"
