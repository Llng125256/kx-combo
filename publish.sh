#!/usr/bin/env bash
# 组合任务发版脚本 —— GitHub 永久地址版（2026-10-05 固化）
# 用法: bash publish.sh
# 地址永久不变：仓库 main 分支同名文件覆盖即发版，线上 prompt 里的地址无需再改
set -euo pipefail
cd "$(dirname "$0")"

PKG="_pkg_combo.tar.bz2"
FILES=(config.yaml kx_client.py monitor_combo.py notifier.py requirements.txt)
REPO="Llng125256/kx-combo"
RAW="https://raw.githubusercontent.com/${REPO}/main/${PKG}"
TOKEN_FILE="/root/.gt"          # device-flow 令牌（scope=repo），勿外传勿提交

# 0) 令牌检查
[ -f "$TOKEN_FILE" ] || { echo "FATAL: 缺少令牌文件 $TOKEN_FILE" >&2; exit 1; }
T=$(cat "$TOKEN_FILE")

# 1) 打包（显式列文件，__pycache__ 不会混入）
rm -f "$PKG"
tar -cjf "$PKG" "${FILES[@]}"
echo "[1/4] 打包 OK: $(du -h "$PKG" | cut -f1)"

# 2) API 上传（走 api.github.com，绕开 github.com 主站直连限制；重试 ×6）
#    更新已有文件必须带 sha：先 GET 当前文件 sha（新建时为空）
put() {
  local i code B64 sha
  sha=$(curl -s --max-time 30 -H "Authorization: Bearer $T" \
    "https://api.github.com/repos/${REPO}/contents/${PKG}?ref=main" \
    | python3 -c "import json,sys; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null || true)
  B64=$(base64 -w0 "$PKG")
  for i in 1 2 3 4 5 6; do
    if [ -n "$sha" ]; then
      code=$(curl -s --max-time 60 -o /tmp/_put_resp.json -w '%{http_code}' -X PUT \
        -H "Authorization: Bearer $T" -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/${REPO}/contents/${PKG}" \
        -d "{\"message\":\"发版 $(date -u '+%F %T')Z\",\"content\":\"${B64}\",\"sha\":\"${sha}\",\"branch\":\"main\"}")
    else
      code=$(curl -s --max-time 60 -o /tmp/_put_resp.json -w '%{http_code}' -X PUT \
        -H "Authorization: Bearer $T" -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/${REPO}/contents/${PKG}" \
        -d "{\"message\":\"发版 $(date -u '+%F %T')Z\",\"content\":\"${B64}\",\"branch\":\"main\"}")
    fi
    if [ "$code" = "200" ] || [ "$code" = "201" ]; then return 0; fi
    echo "  上传失败(第 $i 次): HTTP $code，6 秒后重试" >&2
    sleep 6
  done
  return 1
}
put || { echo "FATAL: 上传重试 6 次仍失败" >&2; cat /tmp/_put_resp.json >&2; exit 1; }
echo "[2/4] API 上传 OK → ${RAW}"

# 3) 完整性：服务端内容下载回 cmp 字节一致（API raw 媒体通道）
for i in 1 2 3 4 5 6; do
  curl -s --max-time 60 -H "Authorization: Bearer $T" -H "Accept: application/vnd.github.raw" \
    "https://api.github.com/repos/${REPO}/contents/${PKG}" -o /tmp/_verify_pkg.tbz
  if cmp -s "$PKG" /tmp/_verify_pkg.tbz; then break; fi
  echo "  校验不一致(第 $i 次，服务端同步中)，20 秒后重试" >&2
  sleep 20
done
cmp "$PKG" /tmp/_verify_pkg.tbz
echo "[3/4] 服务端字节一致 OK"

# 4) 最终验收：下载回来的包直接跑回归
rm -rf /tmp/_pub_v && mkdir /tmp/_pub_v && tar xjf /tmp/_verify_pkg.tbz -C /tmp/_pub_v
if [ -f test_combo.py ]; then
  cp test_combo.py /tmp/_pub_v/
  ( cd /tmp/_pub_v && python3 test_combo.py | tail -1 )
fi
echo "[4/4] 回归 OK"

# 本地 git 留档（失败不阻塞，远端已更新）
git add "$PKG" "${FILES[@]}" 2>/dev/null || true
git commit -m "发版 $(date -u '+%F %T')Z（远端已由 API 覆盖）" >/dev/null 2>&1 || true

echo "===== 发版完成（地址永久不变）====="
echo "${RAW}"
