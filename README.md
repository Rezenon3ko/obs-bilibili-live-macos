# obs-bilibili-live-macos

macOS 专用的 B 站直播 OBS 脚本，轻量、单账号，只针对 Python 3.11 和 OBS Studio 32。

## 功能

- B 站扫码登录，本地保存账号 Cookie
- 登录后拉取直播间状态、标题和分区
- 修改并保存直播标题、直播分区
- 一键开始直播：自动获取推流地址、写入 OBS、启动推流
- 开播时如需要人脸认证，自动弹出认证二维码；认证成功后自动继续开播
- 一键结束直播：同时停止 OBS 推流和 B 站直播

## 环境要求

- macOS
- Python 3.11
- OBS Studio 32

Python 依赖：

```text
requests
qrcode[pil]
```

## 安装依赖

在项目目录执行：

```bash
python3 -m pip install -r requirements.txt
```

## 在 OBS 中加载

1. 打开 OBS
2. 菜单栏选择 `工具` -> `脚本`
3. 点击 `+`，选择本项目的 `bilibili_live_macos.py`
4. 脚本加载后，在属性面板中操作

## 使用流程

1. 点击“二维码登录”，用 B 站 App 扫码并确认
2. 登录成功后点击“更新账号信息”，刷新账号和直播间状态
3. 修改“直播标题”或“直播分区”，点击对应保存按钮
4. 点击“开始直播”一键开播
5. 点击“结束直播”一键关播

## 数据与日志

运行数据保存在：

```text
./data/
```

日志文件：

```text
./data/logs/bilibili_live_mac.log
```

## 许可证

MIT License，见 `LICENSE`。
