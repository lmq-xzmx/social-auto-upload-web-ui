# -*- coding: utf-8 -*-
"""把 cookiesFile/ 下已有的 cdp_*.json cookie 注册进 user_info 账号表。

背景
----
SAU 的 data/cookiesFile/ 里有一批从真浏览器导出（CDP）的登录 cookie
（知乎/微博/B站/公众号…），但 user_info 表里可能只注册了少数账号。
GEO-Flow 的账号同步（POST /api/v1/accounts/sync-from-sau）是从 user_info
读全表的 —— 没注册 = 平台根本进不了 Cookie 诊断链路。

filePath 为什么用平台名（zhihu.json）而不是 cdp_zhihu.json
---------------------------------------------------------
GEO-Flow 拼 cookie 路径是 <CookieDir>/<filePath>，它的 CookieDir 默认是
SAU 的 backend/cookiesFile —— 那个目录里放的是**平台名软链**：
    backend/cookiesFile/zhihu.json -> data/cookiesFile/cdp_zhihu.json
cdp_*.json 这个原始名只存在于 data/cookiesFile 里，用它注册的话
GEO-Flow 拼出来的路径直接失效。

幂等：按 (type, filePath) 判重，已存在就跳过。
用法：python3 scripts/register_cdp_accounts.py [--dry-run]
"""
import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "db" / "database.db"
COOKIE_DIR = ROOT / "backend" / "cookiesFile"  # GEO-Flow 拼路径用的那个目录
BACKEND_DIR = ROOT / "backend"

# type 取 SAU 的 PLATFORM_MAP（app.py:221）：
# 1=小红书 2=视频号 3=抖音 4=快手 5=B站 6=百家号 11=微博 14=知乎 17=微信公众号
#
# 这里只放平台编号和文件名的映射 —— **昵称/头像运行时现抓**。
# 账号昵称和头像是个人信息，写死在脚本里等于跟着 git 仓库 forever 地传下去；
# 而不同机器上的账号本来也不同，写死反而是错的。
ACCOUNTS = [
    # (type, filePath, 平台实现类路径)
    (14, "zhihu.json", "impl.zhihu.platform:ZhihuPlatform"),
    (11, "weibo.json", "impl.weibo.platform:WeiboPlatform"),
    (5, "bilibili.json", "impl.bilibili.platform:BilibiliPlatform"),
    (17, "weixin_gzh.json", "impl.weixin_gzh.platform:WeixinGzhPlatform"),
]

# 抓不到昵称时的占位名（前端仍能看出是哪个平台的账号）
PLATFORM_LABEL = {
    14: "知乎账号",
    11: "微博账号",
    5: "B站账号",
    17: "公众号账号",
}


def fetch_identity(platform_type, file_name, class_path):
    """从 cookie 现抓昵称与头像；抓不到就返回占位值。

    会真开一次浏览器访问平台页面（几秒到几十秒），
    拿的是账号当前真实昵称 —— 比写死一份旧的准。
    """
    placeholder = (PLATFORM_LABEL.get(platform_type, "账号"), "")
    try:
        sys.path.insert(0, str(BACKEND_DIR))
        mod_name, cls_name = class_path.split(":")
        mod = __import__(mod_name, fromlist=[cls_name])
        cls = getattr(mod, cls_name)
        platform = cls()

        async def _run():
            return await platform.sync_profile(file_name)

        result = asyncio.run(asyncio.wait_for(_run(), timeout=120))
        name = (result.get("name") or "").strip()
        avatar = (result.get("avatar") or "").strip()
        if name:
            return name, avatar
        print(f"  抓到的昵称为空，用占位名: {PLATFORM_LABEL.get(platform_type)}")
        return placeholder
    except Exception as exc:
        print(f"  抓昵称失败({type(exc).__name__})，用占位名: {exc}")
        return placeholder


def main(dry_run=False, fetch=True):
    if not DB.exists():
        print(f"找不到账号库: {DB}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()

    # 清掉用 cdp_* 文件名注册的旧记录（那条路径 GEO-Flow 拼不出来）
    cur.execute("DELETE FROM user_info WHERE filePath LIKE 'cdp_%.json'")
    if cur.rowcount and not dry_run:
        print(f"清理了 {cur.rowcount} 条用 cdp_* 文件名注册的记录")

    for t, fp, class_path in ACCOUNTS:
        cookie_file = COOKIE_DIR / fp
        if not cookie_file.exists():
            print(f"跳过 {fp}: {cookie_file} 不存在")
            continue
        row = cur.execute(
            "SELECT id FROM user_info WHERE type = ? AND filePath = ?", (t, fp)
        ).fetchone()
        if row:
            print(f"跳过 {fp}: 已存在 (id={row[0]})")
            continue

        name, avatar = ("", "")
        if fetch:
            print(f"抓取 {fp} 的账号昵称…")
            name, avatar = fetch_identity(t, fp, class_path)
        else:
            name = PLATFORM_LABEL.get(t, "账号")

        if dry_run:
            print(f"[dry-run] 将新增 type={t} {fp} -> {name}")
            continue
        cur.execute(
            "INSERT INTO user_info (type, filePath, userName, status, avatar, fans, likes, follows, stats) "
            "VALUES (?, ?, ?, 1, ?, 0, 0, 0, '[]')",
            (t, fp, name or PLATFORM_LABEL.get(t, "账号"), avatar),
        )
        print(f"新增 type={t} {fp} -> {name} (id={cur.lastrowid})")

    if not dry_run:
        conn.commit()
    print("--- user_info 全表 ---")
    for r in cur.execute("SELECT id, type, filePath, userName, status FROM user_info ORDER BY id"):
        print(" ", r)
    conn.close()
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只看会做什么，不写库")
    ap.add_argument("--no-fetch", action="store_true",
                    help="不抓昵称（快，但账号显示为平台占位名）")
    args = ap.parse_args()
    sys.exit(main(args.dry_run, fetch=not args.no_fetch))
