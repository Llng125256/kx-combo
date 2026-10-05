#!/usr/bin/env bash
# 组合任务发版脚本 —— 手册 §5.1 五步固化版（2026-09-27 用户拍板固化）
# 用法: bash publish.sh
# 产出: 双地址（主/镜像）就绪输出。PUT 换包是单独步骤（§5.2），本脚本不碰任务配置。
set -euo pipefail
cd "$(dirname "$0")"

PKG="_pkg_combo.tar.bz2"
FILES=(config.yaml kx_client.py monitor_combo.py notifier.py requirements.txt)

# 1) 打包（显式列文件，__pycache__ 不会混入）
rm -f "$PKG"
tar -cjf "$PKG" "${FILES[@]}"
echo "[1/5] 打包 OK: $(du -h "$PKG" | cut -f1)"

# 2) 上传（偶发 500/503 → 退避重试 ×6，手册 §5.1 口径）
upload() {
  local i u
  for i in 1 2 3 4 5 6; do
    u=$(curl -s --max-time 90 --data-binary @"$PKG" https://paste.rs/)
    case "$u" in https://paste.rs/*) echo "$u"; return 0;; esac
    echo "  上传失败(第 $i 次): $u，6 秒后重试" >&2
    sleep 6
  done
  return 1
}
U1=$(upload) || { echo "FATAL: 主包上传重试 6 次仍失败" >&2; exit 1; }
U2=$(upload) || { echo "FATAL: 镜像上传重试 6 次仍失败" >&2; exit 1; }
echo "[2/5] 上传 OK: 主 $U1 镜像 $U2"

# 3) URL 200 预检（§5.2 步骤 1 前置）
for u in "$U1" "$U2"; do
  code=$(curl -sI "$u" | head -1)
  [[ "$code" == *"200"* ]] || { echo "FATAL: 预检失败 $u → $code" >&2; exit 1; }
done
echo "[3/5] URL 200 预检 OK"

# 4) 完整性：下载 cmp 字节一致 + 解包逐文件比对
curl -s "$U1" -o /tmp/_pub_a.tbz
curl -s "$U2" -o /tmp/_pub_b.tbz
cmp "$PKG" /tmp/_pub_a.tbz
cmp "$PKG" /tmp/_pub_b.tbz
rm -rf /tmp/_pub_v && mkdir /tmp/_pub_v && tar xjf /tmp/_pub_a.tbz -C /tmp/_pub_v
for f in "${FILES[@]}"; do
  cmp "/tmp/_pub_v/$f" "$f" || { echo "FATAL: 解包比对失败: $f" >&2; exit 1; }
done
echo "[4/5] cmp + 解包逐文件比对 OK"

# 5) 最终验收：下载回来的包跑回归
if [ -f test_combo.py ]; then
  cp test_combo.py /tmp/_pub_v/
  ( cd /tmp/_pub_v && python3 test_combo.py | tail -1 )
fi
echo "===== 发版包就绪（PUT 换包另走 §5.2）====="
echo "主:   $U1"
echo "镜像: $U2"
