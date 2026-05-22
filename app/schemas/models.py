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
