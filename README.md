# kx-combo

K线组合信号监控（combo）发版仓库。

- `_pkg_combo.tar.bz2` — 线上任务拉取的发版包（地址永久固定，git push 覆盖更新）
- 源码 5 文件与包内一致，便于 diff 与回滚

发版：本地 `bash publish.sh` → git push 覆盖 `_pkg_combo.tar.bz2`，线上地址不变。
