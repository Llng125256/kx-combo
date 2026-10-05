# -*- coding: utf-8 -*-
"""消息推送模块：企业微信群机器人(主) + Server酱(备用)，可单用或同时推送

统一接口: send(title, markdown) -> bool

■ 企业微信群机器人
  企业微信群 -> 设置 -> 群机器人 -> 添加 -> 复制 Webhook -> 填入 config.yaml
■ Server酱（备用，需要时启用）
  https://sct.ftqq.com/ 微信扫码 -> 复制 SendKey（形如 SCTxxxx）-> 填入 config.yaml
"""
from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger("kx.notifier")


# ====================================================================== #
class ServerChan:
    """Server酱 Turbo: POST https://sctapi.ftqq.com/{SENDKEY}.send"""

    API = "https://sctapi.ftqq.com/{}.send"

    def __init__(self, sendkey: str = ""):
        self.sendkey = (sendkey or os.environ.get("KX_SCT_KEY", "")).strip()

    @property
    def configured(self) -> bool:
        return bool(self.sendkey)

    def send(self, title: str, markdown: str) -> bool:
        if not self.configured:
            log.warning("[Server酱] 未配置 SendKey，消息不发送。标题: %s", title)
            return False
        try:
            r = requests.post(
                self.API.format(self.sendkey),
                data={"title": title[:256], "desp": markdown[:32000]},
                timeout=15,
            )
            data = r.json()
            if data.get("code") == 0:
                return True
            log.error("[Server酱] 返回错误: %s", data)
            return False
        except Exception as e:  # noqa: BLE001
            log.error("[Server酱] 推送失败: %s", e)
            return False


# ====================================================================== #
class WeComBot:
    """企业微信群机器人 Webhook"""

    # 单条消息字节上限：手机端显示约2048字节，API上限4096字节，取安全值
    BYTE_LIMIT = 1900

    def __init__(self, webhook: str = ""):
        self.webhook = (webhook or os.environ.get("KX_WECHAT_WEBHOOK", "")).strip()

    @property
    def configured(self) -> bool:
        return bool(self.webhook)

    @staticmethod
    def _split_markdown(content: str, limit: int) -> list[str]:
        """按行边界把 markdown 切成不超过 limit 字节的段（不切断语法）"""
        parts, cur, cur_len = [], [], 0
        for line in content.split("\n"):
            lb = len(line.encode("utf-8")) + 1
            if cur and cur_len + lb > limit:
                parts.append("\n".join(cur))
                cur, cur_len = [], 0
            if lb > limit:  # 单行超限兜底：按字符硬切
                b = line.encode("utf-8")
                while b:
                    parts.append(b[:limit].decode("utf-8", errors="ignore"))
                    b = b[limit:]
                continue
            cur.append(line)
            cur_len += lb
        if cur:
            parts.append("\n".join(cur))
        return parts or [""]

    def send(self, title: str, markdown: str) -> bool:
        """超长自动分段发送，每段带 (n/m) 序号"""
        if not self.configured:
            log.warning("[企业微信] 未配置 webhook，消息不发送。标题: %s", title)
            return False
        content = f"## {title}\n\n{markdown}"
        parts = self._split_markdown(content, self.BYTE_LIMIT)
        ok_all = True
        for i, part in enumerate(parts, 1):
            tag = f"\n\n({i}/{len(parts)})" if len(parts) > 1 else ""
            ok = self._send({"msgtype": "markdown",
                             "markdown": {"content": part + tag}})
            ok_all = ok_all and ok
        return ok_all

    def _send(self, payload: dict) -> bool:
        try:
            r = requests.post(self.webhook, json=payload, timeout=10)
            data = r.json()
            if data.get("errcode") == 0:
                return True
            log.error("[企业微信] 返回错误: %s", data)
            return False
        except Exception as e:  # noqa: BLE001
            log.error("[企业微信] 推送失败: %s", e)
            return False


# ====================================================================== #
def build_notifiers(cfg: dict) -> list:
    """按 config 的 notify 段构建推送渠道列表"""
    notify_cfg = cfg.get("notify", {})
    channels = notify_cfg.get("channels", ["wecom"])
    notifiers: list = []
    for ch in channels:
        if ch == "wecom":
            bot = WeComBot(notify_cfg.get("wecom", {}).get("webhook", ""))
            if bot.configured:
                notifiers.append(("企业微信", bot))
            else:
                log.warning("notify.channels 含 wecom 但未配置 webhook")
        elif ch == "serverchan":
            sc = ServerChan(notify_cfg.get("serverchan", {}).get("sendkey", ""))
            if sc.configured:
                notifiers.append(("Server酱", sc))
            else:
                log.warning("notify.channels 含 serverchan 但未配置 SendKey")
        else:
            log.warning("未知推送渠道: %s", ch)
    if not notifiers:
        log.warning("没有可用的推送渠道！请检查 config.yaml 的 notify 配置")
    return notifiers
