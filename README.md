# 协议上号管理后台 (Flask + Vue)

A web admin panel for the WeChat protocol server. Backend uses Flask, frontend uses
Vue 3 + Vite. The layout (login page, sidebar, 协议上号/老号登录 pages) matches
the layout of the original `snlie.com/login` admin, while the 协议上号 login flow
has been reworked to follow the new port-check / start-process / start-wechat /
QR-code / polling pipeline.

## Flow overview

### 协议上号 (new account)

1. **Check port** — `POST {{mgr}}/Get_PortOccupiedInfo` with `{ "CheckPort": <port> }`
2. **Start protocol process** — `POST {{mgr}}/StartObjectProcess` with `{ "StartPort": <port> }`
3. **Start WeChat** — `POST {{mgr}}/StartWechat` with the user-supplied
   `StartPort` / `RDV` / `CallBackURL` / proxy fields. The response contains
   `session_id` and `start_port`, which are needed for all subsequent calls.
4. **Get QR code** — `POST {{host}}:{{port}}/getloginqrcode` with `{ "session_id": <sid> }`
5. **Poll login state** — `POST {{host}}:{{port}}/checkloginqrcode` with
   `{ "session_id": <sid>, "uuid": <uuid> }` every few seconds. States:
   - `polling` / `0` → waiting for scan
   - `scanned` / `1` → user scanned, waiting for phone confirmation
   - `logged_in` / `2` → success. The `user_name` (wxid) is persisted into
     `rdv_wxid_mapping.json` (scoped by `server_ip:mgr_port`) so the next time
     that RDV is selected in 老号登录, the wxid auto-fills.

### 老号登录 (existing account)

Steps 1–3 are identical to 协议上号, except the `StartWechat` payload is sent
without `CallBackURL` and without proxy.

4. **Push login URL** — `POST {{host}}:{{port}}/pushloginurl` with
   `{ "session_id": <sid>, "wxid": <wxid> }`. The response contains a `uuid`.
5. **Poll login state** — same `/checkloginqrcode` endpoint as 协议上号.
6. On success, no further call is needed.

## Project layout

```
D:\xweixin\前端
├── backend\                # Flask API
│   ├── app.py
│   ├── requirements.txt
│   ├── rdv_wxid_mapping.json
│   └── 启动后端.bat
├── frontend\               # Vue 3 + Vite
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── public\
│   └── src\
│       ├── main.js
│       ├── App.vue
│       ├── router\
│       ├── stores\auth.js
│       ├── layouts\MainLayout.vue
│       ├── views\
│       │   ├── LoginView.vue
│       │   ├── ShanghaoView.vue     # 协议上号
│       │   └── OldLoginView.vue     # 老号登录
│       ├── utils\api.js
│       └── styles\main.scss
├── 启动前端.bat
├── 启动后端.bat             (在 backend\ 下)
├── 启动全部.bat             # 启动前后端
└── 构建并启动.bat           # 构建前端后由 Flask 单端口 8000 服务
```

## Default credentials

- Username: `admin`
- Password: `admin`

You can change them in `backend/app.py` (`ADMIN_USER` / `ADMIN_PASS`).

## How to run

### Development (recommended while iterating)

Two terminals, or just double-click `启动全部.bat`:

```bat
:: Terminal 1 (or 启动后端.bat)
cd backend
pip install -r requirements.txt
python app.py
:: -> http://localhost:8000  (API only)

:: Terminal 2 (or 启动前端.bat)
cd frontend
npm install
npm run dev
:: -> http://localhost:5173  (Vue dev server, proxies /api -> :8000)
```

Open **http://localhost:5173** in your browser. The Vite dev server proxies all
`/api/*` calls to Flask on port 8000, so cookies and CORS Just Work.

### Production-style single-port deploy

```bat
构建并启动.bat
```

This runs `npm run build` in `frontend\` and then starts Flask, which serves
both the API **and** the built Vue app on **http://localhost:8000**.

## Environment variables

| Variable          | Default                     | Description                              |
|-------------------|-----------------------------|------------------------------------------|
| `FLASK_SECRET_KEY`| `change-me-...`             | Session signing key. **Set this in prod.** |
| `PORT`            | `8000`                      | Port Flask listens on.                   |

## Notes

- `rdv_wxid_mapping.json` is created automatically the first time a mapping is
  saved. It is scoped by `server_ip:mgr_port` so multiple servers can coexist
  without trampling each other.
- The `proxy` block of a saved mapping is preserved so a previously-used
  account can be re-launched with the same proxy on 老号登录 / 协议上号.
- The Vue dev server has hot module reload, so editing a `.vue` file under
  `frontend/src/` will refresh the page in the browser automatically.
