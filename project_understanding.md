# 🏟️ Football Player Detection & Tracking — Complete Project Understanding

---

## 📌 What is This Project?

This is an **AI-powered web application** built with **Django (Python)** that:
1. Accepts a **football match video** uploaded by a user
2. Runs **YOLOv8** (a deep learning object detection model) to automatically detect **players** and the **ball** in every frame
3. Tracks each player and the ball across frames using **ByteTrack**
4. Calculates **real-world statistics**: speed (km/h), distance covered (meters), ball possession (%)
5. Overlays all this information onto the video and shows a **live mini tactical radar map**
6. Saves the annotated output video and a statistics JSON to **Cloudinary** (cloud storage)
7. Displays the results back to the user with **interactive charts** (speed, distance, possession)

---

## 🗂️ Folder & File Structure — Explained One by One

```
working_project_deployed/
│
├── Football_Player_Detection_and_Tracking/   ← Django Project Config Package
│   ├── settings.py                           ← All project configurations
│   ├── urls.py                               ← Master URL routing table
│   ├── views.py                              ← Landing page & admin home views
│   ├── wsgi.py                               ← Production server entry point
│   └── asgi.py                               ← Async server entry point
│
├── users/                                    ← Main App (all user-facing features)
│   ├── models.py                             ← Database table definitions
│   ├── views.py                              ← All user logic (login, upload, result)
│   ├── ai_pipeline.py                        ← 🧠 Core AI engine (YOLOv8 + tracking)
│   ├── tasks.py                              ← Background video processing thread
│   ├── admin.py                              ← Django admin panel registration
│   ├── apps.py                               ← App configuration
│   └── templates/
│       ├── users/
│       │   ├── dashboard.html                ← User home / past analyses
│       │   ├── upload.html                   ← Video upload + live webcam page
│       │   └── result.html                   ← Analysis result with charts
│       ├── admins/
│       │   ├── AdminHome.html                ← Admin dashboard
│       │   ├── adminbase.html                ← Admin navbar/layout base
│       │   └── viewregisterusers.html        ← Admin: manage all users
│       ├── base.html                         ← Site-wide HTML base template
│       ├── index.html                        ← Landing/welcome page
│       ├── UserLogin.html                    ← User login page
│       ├── UserRegistrations.html            ← User registration page
│       └── AdminLogin.html                   ← Admin login page
│
├── admins/                                   ← Admin App (admin management)
│   ├── models.py                             ← (empty — uses users/models.py)
│   ├── views.py                              ← Admin login, activate/delete/edit users
│   ├── admin.py                              ← Django admin registration
│   └── apps.py                              ← App configuration
│
├── static/                                   ← Frontend CSS & images
│   ├── css/
│   │   └── glassmorphism.css                 ← All styling (glass UI design)
│   ├── images/                               ← Logo & hero images
│   └── img/                                  ← Additional images
│
├── media/                                    ← Uploaded files (local temp only)
│   ├── profiles/                             ← User profile photos
│   └── videos/                               ← Uploaded input videos (temp)
│
├── manage.py                                 ← Django management command tool
├── requirements.txt                          ← Python package dependencies
├── Dockerfile                                ← Container build instructions (HuggingFace)
├── db.sqlite3                                ← Local SQLite database
├── yolov8m.pt                                ← 🤖 Pre-trained YOLOv8 Medium model weights
├── .gitignore                                ← Files excluded from Git
├── .dockerignore                             ← Files excluded from Docker build
└── README.md                                 ← Basic project description
```

---

## 🔑 Key Files — Deep Explanation

---

### 1. `Football_Player_Detection_and_Tracking/settings.py`
**The brain of Django configuration.** Every critical setting lives here.

| Setting | What it does |
|---|---|
| `SECRET_KEY` | A secret cryptographic key Django uses to sign cookies and sessions |
| `DEBUG = True` | Shows detailed error pages. Should be `False` in production |
| `ALLOWED_HOSTS` | Which domain names can access this app (includes `*` = everyone) |
| `INSTALLED_APPS` | Lists all active Django apps: `users`, `admins`, `cloudinary` etc. |
| `MIDDLEWARE` | Request processing pipeline (security, sessions, CSRF protection) |
| `DATABASES` | Uses `dj_database_url` to read the database URL from an environment variable. Falls back to local `db.sqlite3` |
| `CLOUDINARY_STORAGE` | API credentials for Cloudinary (cloud media storage for videos & images) |
| `DEFAULT_FILE_STORAGE` | All file uploads go to Cloudinary, not local disk |
| `STATIC_URL` | URL prefix for CSS/JS files |
| `STATICFILES_STORAGE` | WhiteNoise compresses static files for fast serving |
| `SESSION_COOKIE_SAMESITE = 'None'` | Required for the app to work inside HuggingFace Spaces iframe |
| `TIME_ZONE = 'Asia/Kolkata'` | All timestamps shown in IST |

---

### 2. `Football_Player_Detection_and_Tracking/urls.py`
**The traffic controller.** Every URL a user can visit is mapped here to a specific Python function.

```
URL Path                    → View Function              → Purpose
──────────────────────────────────────────────────────────────────
/                           → mainView.index             Landing page
/UserLogin                  → mainView.UserLogin          Show login form
/UserRegisterForm           → usr.UserRegisterActions     Handle registration
/UserLoginCheck/            → usr.UserLoginCheck          Verify login credentials
/UserHome/                  → usr.UserHome                User dashboard
/prediction/                → usr.upload_video            Upload + process video
/result/<id>/               → usr.result                  Show analysis results
/api/status/<id>/           → usr.check_status            Polling: is video ready?
/api/process_live_frame/    → usr.process_live_frame      Live webcam AI inference
/Adminlogin                 → mainView.AdminLogin          Show admin login form
/AdminLogincheck            → admins.AdminLoginCheck       Verify admin credentials
/AdminHome                  → mainView.adminhome           Admin dashboard
/userDetails                → admins.RegisterUsersView     View all registered users
/ActivUsers/                → admins.ActivaUsers           Activate a user account
/DeleteUsers/               → admins.DeleteUsers           Delete a user account
/EditUsers/                 → admins.EditUsers             Edit user details
/logout/                    → usr.logout_view              Logout and clear session
```

---

### 3. `users/models.py`
**The database blueprint.** Defines two database tables:

#### Table 1: `UserRegistrationModel` (table name: `user_registrations`)
Stores every person who registers on the site.

| Column | Type | Description |
|---|---|---|
| `name` | CharField | Full name of the user |
| `loginid` | CharField (unique) | Username for login |
| `password` | CharField | Hashed password (not plain text!) |
| `mobile` | CharField (unique) | 10-digit mobile number |
| `email` | EmailField (unique) | Email address |
| `locality` | CharField | Area/locality |
| `address` | TextField | Full address |
| `city` | CharField | City |
| `state` | CharField | State |
| `status` | CharField | `'waiting'` (default) or `'activated'` |
| `profile_image` | ImageField | Uploaded to Cloudinary |

> **Important**: A user with `status='waiting'` **cannot** log in. Admin must activate them first.

#### Table 2: `VideoAnalysis` (table name: `video_analysis`)
Stores one record per video upload/analysis session.

| Column | Type | Description |
|---|---|---|
| `user` | ForeignKey | Which user uploaded this video |
| `input_video` | FileField | Original uploaded video (Cloudinary) |
| `output_video` | FileField | AI-annotated output video (Cloudinary) |
| `status` | CharField | `Pending` → `Processing` → `Completed` / `Failed` |
| `progress` | IntegerField | 0–100 percentage for progress bar |
| `created_at` | DateTimeField | When the upload happened |
| `updated_at` | DateTimeField | Last status update time |

---

### 4. `users/views.py`
**The user-facing logic engine.** Every function here handles a specific web request.

#### `index(request)` — Landing Page
Simply renders the `index.html` welcome page.

#### `UserRegisterActions(request)` — Registration
- Reads all form fields (`name`, `loginid`, `email`, `password`, etc.)
- Hashes the password using `make_password()` (so it's never stored as plain text)
- Saves a new `UserRegistrationModel` row with `status='waiting'`
- If duplicate email/loginid/mobile → shows error message

#### `UserLoginCheck(request)` — Login
- Fetches the user from DB by `loginid`
- Uses `check_password()` to verify the hashed password
- If password matches AND `status == 'activated'` → sets session variables and redirects to `/prediction/`
- If `status == 'waiting'` → shows "Account not activated" error
- If wrong credentials → shows "Invalid Login" error

#### `logout_view(request)` — Logout
- Calls `request.session.flush()` to **wipe all session data** completely
- Redirects to home page

#### `UserHome(request)` — Dashboard
- Checks if user is logged in (session has `'id'` key)
- Fetches all `VideoAnalysis` records for this user (ordered newest first)
- Renders `dashboard.html` with the list of past analyses

#### `upload_video(request)` — Upload Page & Processing Trigger
- **GET request**: Shows the `upload.html` page
- **POST request** (file upload):
  1. Saves the video to local disk using `FileSystemStorage`
  2. Creates a `VideoAnalysis` DB record with `status='Pending'`
  3. Calls `trigger_video_processing(analysis.id)` to start AI in background
  4. Returns JSON `{'status': 'processing', 'analysis_id': ...}` to the browser

#### `check_status(request, analysis_id)` — Status Polling API
- Browser polls this every few seconds via JavaScript
- Returns JSON `{'status': ..., 'progress': ..., 'redirect_url': ...}`
- When `status == 'Completed'` → provides the URL to the result page

#### `result(request, analysis_id)` — Result Page
- Fetches the `VideoAnalysis` record
- Checks user **owns** this analysis (security check!)
- Fetches the metrics JSON from Cloudinary
- Processes metrics: top 5 speeds, top 5 distances, possession breakdown
- Passes all data as JSON strings to `result.html` for Chart.js to draw graphs

#### `process_live_frame(request)` — Live Webcam AI
- Receives a **base64-encoded JPEG** image from the browser
- Decodes it → runs YOLOv8 inference → draws bounding boxes
- Returns an **annotated base64 JPEG** back to the browser
- Browser displays it in real-time — creating a live AI overlay effect

---

### 5. `users/ai_pipeline.py` — 🧠 THE CORE AI ENGINE

This is the most important file. It contains the `FootballTracker` class.

#### `initialize_model()`
Loads the `yolov8m.pt` weights file into memory. This is a **34 MB pre-trained neural network** that knows how to detect 80 types of objects. For this project, we only care about:
- **Class 0** = Person (football player)
- **Class 32** = Sports ball

#### `process_video(input_path, output_path, callback)`
This is the main pipeline. Here is what happens **frame by frame**:

**Step 1 — Open Video**
```
OpenCV opens the input video → reads width, height, FPS, total frames
Creates an output VideoWriter to write the annotated frames
```

**Step 2 — Homography Setup**
```
A Homography Matrix (H_matrix) transforms pixel coordinates into
real-world meters on a standard football pitch (105m × 68m).
This allows calculating TRUE speed in km/h and distance in meters.
```

**Step 3 — Kalman Filter for Ball Tracking**
```
A Kalman Filter predicts the ball's position even when it is 
temporarily hidden (occluded by a player or off-screen).
It uses physics-based motion prediction for up to 30 frames.
```

**Step 4 — For Each Frame:**
```python
results = model.track(frame, persist=True, classes=[0, 32], tracker="bytetrack.yaml")
```
- `persist=True` → Track IDs are remembered across frames (same player = same ID)
- `tracker="bytetrack.yaml"` → Uses ByteTrack algorithm for robust multi-object tracking
- `classes=[0, 32]` → Only detect people and balls

**For each detected player (class 0):**
- Calculate center position `(cx, cy)`
- Transform to real-world meters using `H_matrix`
- Append to `player_tracks[track_id]`
- Calculate **speed** from last 5 positions over time → convert to km/h (capped at 38 km/h)
- Calculate **cumulative distance** covered
- Assign to **Team A** (left side) or **Team B** (right side) heuristically

**For the ball (class 32):**
- Update Kalman Filter with measurement
- Calculate ball speed (capped at 150 km/h)
- Track `ball_tracks` list for speed calculation

**Step 5 — Draw Visual Overlays on Frame**
```
• Green bounding box + "ID: X  25.3 km/h" label for each player
• Red bounding box + "Ball" label for the ball
• Yellow ellipse + "Ball (Est)" for Kalman-predicted ball position
• Mini 2D tactical radar map in the bottom-right corner of the frame
  - Shows all players as colored dots (red=Team B, blue=Team A)
  - Shows ball as cyan dot
```

**Step 6 — Possession Logic**
```
Every frame: find which player is closest to the ball (within 150 pixels).
Assign that player's team as "in possession".
Count total frames for Team A, Team B, and Contested.
```

**Step 7 — Save Output & Metrics**
```
Write annotated frame to output video.
After all frames: save metrics as JSON:
{
  "max_ball_speed": 87.3,
  "possession": {"Team A": 1200, "Team B": 980, "Contested": 320},
  "player_speeds": {"1": 29.4, "3": 27.1, ...},
  "player_distances": {"1": 312.5, "3": 298.2, ...}
}
```

---

### 6. `users/tasks.py` — Background Processing Thread

When a video is uploaded, **we cannot process it in the same web request** (it would time out after 30 seconds). So we use Python `threading`.

#### `trigger_video_processing(analysis_id)`
```python
thread = threading.Thread(target=process_video_task, args=(analysis_id,))
thread.daemon = True
thread.start()
```
Spawns a **background daemon thread** that runs independently. The web request returns immediately.

#### `process_video_task(analysis_id)` — Full pipeline:
```
1. Set status = 'Processing' in DB
2. Find the local input video file
3. Create a temp output path in /tmp/ 
4. Run FootballTracker.process_video() → produces annotated video + metrics JSON
5. Re-encode video with FFmpeg → H.264 format (browser-compatible)
6. Upload INPUT video to Cloudinary (folder: videos/input/)
7. Upload OUTPUT video to Cloudinary (folder: videos/output/)
8. Upload metrics JSON to Cloudinary (folder: videos/metrics/)
9. Set status = 'Completed', progress = 100 in DB
10. Delete all local temp files (saves disk space)
```

---

### 7. `admins/views.py` — Admin Management

#### `AdminLoginCheck(request)` — Admin Login
- Hardcoded credentials: `loginid = 'admin'`, `pswd = 'admin'`
- Sets `request.session['is_admin'] = True` on success
- Redirects to `AdminHome`

#### `RegisterUsersView(request)` — View All Users
- Fetches all `UserRegistrationModel` objects from DB
- Renders the user management table

#### `ActivaUsers(request)` — Activate a User
- Takes `uid` (user ID) from GET parameters
- Updates that user's `status` from `'waiting'` → `'activated'`
- Now that user can log in

#### `DeleteUsers(request)` — Delete a User
- Takes `uid` from GET parameters
- Permanently deletes the user record from DB

#### `EditUsers(request)` — Edit User Details
- Takes updated fields from POST form
- Fetches user by `uid` and updates fields
- Saves the updated record

---

### 8. `yolov8m.pt` — The AI Model Weights File
- **34 MB** pre-trained neural network (YOLOv8 Medium variant)
- Trained by Ultralytics on the COCO dataset (80 object categories)
- Contains millions of learned parameters that define how the model sees objects
- **We do NOT train this** — we use it as-is (Transfer Learning / Inference only)
- Loaded once at app startup to avoid repeated disk reads

---

### 9. `Dockerfile` — Deployment Container
Tells the server (HuggingFace Spaces) how to build and run the app:
```dockerfile
FROM python:3.9-slim                  # Start with minimal Python image
apt-get install ffmpeg libgl1 ...     # Install system libraries OpenCV needs
pip install -r requirements.txt       # Install all Python packages
EXPOSE 7860                           # Open port 7860
CMD python manage.py migrate          # Create DB tables
    && collectstatic                  # Gather all CSS/JS files
    && gunicorn ... --bind 0.0.0.0:7860  # Start production web server
```

---

### 10. `requirements.txt` — Python Dependencies

| Package | Purpose |
|---|---|
| `Django>=4.2` | The web framework |
| `gunicorn` | Production WSGI web server |
| `whitenoise` | Serves static files efficiently |
| `dj-database-url` | Reads DB config from environment variable |
| `psycopg2-binary` | PostgreSQL database driver |
| `ultralytics==8.1.0` | YOLOv8 object detection library |
| `opencv-python-headless` | Video reading, writing, and drawing (no GUI needed) |
| `numpy` | Numerical arrays used by OpenCV and YOLO |
| `Pillow` | Image processing (profile picture uploads) |
| `lapx` | LAPJV algorithm — used by ByteTrack for optimal assignment |
| `torch, torchvision, torchaudio` | PyTorch deep learning framework (runs YOLO) |
| `django-cloudinary-storage` | Connects Django's file storage to Cloudinary |
| `cloudinary` | Cloudinary SDK for uploading files |

---

## 🔄 Complete Project Flow — Step by Step

```
┌────────────────────────────────────────────────────────┐
│                    USER JOURNEY                        │
└────────────────────────────────────────────────────────┘

1. VISIT SITE (/)
   Browser → index.html → Welcome landing page shown

2. REGISTER (/UserRegisterForm)
   User fills form → POST → UserRegisterActions()
   → Password hashed → Saved to DB with status='waiting'
   → "Registration successful!" message shown

3. ADMIN ACTIVATES ACCOUNT
   Admin logs in → /AdminLogincheck → session set
   → /userDetails → sees all users
   → Clicks "Activate" → /ActivUsers/?uid=X
   → status updated to 'activated' in DB

4. USER LOGS IN (/UserLoginCheck/)
   POST: loginid + password
   → check_password() verifies hash
   → status=='activated'? Yes → session created
   → Redirect to /prediction/ (upload page)

5. UPLOAD VIDEO (/prediction/ POST)
   User selects .mp4 file → POST
   → Saved locally (FileSystemStorage)
   → VideoAnalysis record created (status='Pending')
   → trigger_video_processing(id) → new thread spawned
   → JSON response: {status:'processing', analysis_id: X}

6. POLLING (/api/status/X/ every 2 seconds)
   JavaScript polls this endpoint
   → Returns progress % and status
   → Progress bar animates on screen
   → When status=='Completed' → redirect to /result/X/

7. AI PROCESSING (background thread)
   FootballTracker.process_video() runs:
   ├── Frame 1: YOLO detects players + ball
   ├── ByteTrack assigns persistent IDs
   ├── Kalman Filter handles ball occlusion
   ├── Homography transforms pixels → meters
   ├── Speed/Distance calculated per player
   ├── Possession tracked per frame
   ├── Bounding boxes + labels drawn on frame
   ├── Radar mini-map drawn on frame
   └── Frame written to output video
   → Output video re-encoded to H.264 via FFmpeg
   → Input + Output videos uploaded to Cloudinary
   → Metrics JSON uploaded to Cloudinary
   → DB: status='Completed', progress=100

8. RESULT PAGE (/result/X/)
   → Fetch VideoAnalysis from DB
   → Fetch metrics JSON from Cloudinary URL
   → Extract: top speeds, distances, possession
   → Render result.html with:
      • Annotated output video player
      • Original input video player
      • Bar chart: Top 5 player speeds
      • Bar chart: Top 5 distances
      • Pie chart: Ball possession %
      • Max ball speed displayed

9. LOGOUT (/logout/)
   → session.flush() → all session data wiped
   → Redirect to home page
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  BROWSER (Client)                    │
│  HTML + CSS (glassmorphism.css) + JavaScript        │
│  Chart.js for graphs | Fetch API for polling        │
└─────────────┬───────────────────┬───────────────────┘
              │ HTTP Requests     │ WebSocket / Polling
              ▼                   ▼
┌─────────────────────────────────────────────────────┐
│              DJANGO WEB SERVER (Gunicorn)            │
│                                                     │
│  urls.py → routes requests to correct view          │
│                                                     │
│  ┌─────────────────┐  ┌──────────────────────────┐ │
│  │  users/views.py │  │  admins/views.py          │ │
│  │  - Registration │  │  - Admin login            │ │
│  │  - Login/Logout │  │  - Activate/Delete users  │ │
│  │  - Upload video │  │  - Edit user details      │ │
│  │  - Result page  │  └──────────────────────────┘ │
│  │  - Live webcam  │                                │
│  └────────┬────────┘                                │
│           │ triggers                                 │
│           ▼                                         │
│  ┌────────────────────────────────────────────────┐ │
│  │  users/tasks.py  (Background Thread)           │ │
│  │  process_video_task()                          │ │
│  │  → calls ai_pipeline.py → FootballTracker      │ │
│  └─────────────────┬──────────────────────────────┘ │
└────────────────────┼────────────────────────────────┘
                     │
         ┌───────────▼───────────────┐
         │     AI PIPELINE           │
         │  ai_pipeline.py           │
         │  ┌────────────────────┐   │
         │  │ YOLOv8m (yolov8m.pt│   │
         │  │ Detection: person  │   │
         │  │ + sports ball)     │   │
         │  └────────────────────┘   │
         │  ┌────────────────────┐   │
         │  │ ByteTrack           │   │
         │  │ (multi-object ID   │   │
         │  │  persistence)      │   │
         │  └────────────────────┘   │
         │  ┌────────────────────┐   │
         │  │ Kalman Filter      │   │
         │  │ (ball prediction)  │   │
         │  └────────────────────┘   │
         │  ┌────────────────────┐   │
         │  │ Homography Matrix  │   │
         │  │ (pixels → meters)  │   │
         │  └────────────────────┘   │
         └───────────────────────────┘
                     │
         ┌───────────▼───────────────┐
         │   CLOUDINARY (Cloud)      │
         │   • Input video           │
         │   • Output video          │
         │   • Metrics JSON          │
         └───────────────────────────┘
                     │
         ┌───────────▼───────────────┐
         │   DATABASE (PostgreSQL    │
         │   on Neon / SQLite local) │
         │   • UserRegistrationModel │
         │   • VideoAnalysis         │
         └───────────────────────────┘
```

---

## 🤖 AI/ML Concepts Used — Explained Simply

### YOLOv8 (You Only Look Once)
- A **Convolutional Neural Network** that looks at the entire frame at once
- Divides the image into a grid and predicts bounding boxes + class labels
- "Medium" variant = balance of speed and accuracy
- We use **COCO classes 0 (person) and 32 (sports ball)** only

### ByteTrack
- An algorithm that assigns **persistent unique IDs** to objects across frames
- Uses the **IoU (Intersection over Union)** of bounding boxes to match the same person across consecutive frames
- Even if a player is briefly hidden, ByteTrack re-identifies them correctly

### Kalman Filter
- A mathematical predictor for **smooth tracking under uncertainty**
- If the ball is temporarily invisible (blocked by players), the Kalman Filter predicts where it likely is based on its previous velocity
- Displays the estimated position as a yellow "Ball (Est)" marker

### Homography
- A geometric transformation that maps 2D pixel coordinates to real-world field coordinates
- Using 4 known reference points on the pitch (penalty box corners), it calculates a transformation matrix (H)
- Applied to player positions to get real distance in meters → then speed in km/h

---

## 👥 User Roles

| Role | Default Credentials | Can Do |
|---|---|---|
| **Admin** | loginid: `admin`, password: `admin` | View all users, Activate/Delete/Edit users, see site statistics |
| **User** | Registered by themselves | Upload video, view analysis results, delete their own videos |

> A newly registered user **CANNOT log in** until the Admin activates their account. This is the `status='waiting'` → `status='activated'` flow.

---

## 📊 Output Metrics Explained

After processing a video, these metrics are shown:

| Metric | How Calculated |
|---|---|
| **Max Ball Speed** | Fastest observed ball speed across all frames (km/h), capped at 150 |
| **Player Speed** | Speed calculated from position change over 5 frames using Homography |
| **Player Distance** | Cumulative distance covered across all frames (meters) |
| **Possession %** | Fraction of frames where each team was closest to the ball |
| **Top 5 Speeds** | Top 5 players by maximum speed — shown as a bar chart |
| **Top 5 Distances** | Top 5 players by total distance — shown as a bar chart |
| **Possession Pie** | Team A vs Team B vs Contested — shown as a pie chart |

---

## 🔧 How to Run Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Apply database migrations
python manage.py migrate

# 3. Run development server
python manage.py runserver

# 4. Open browser at:
http://127.0.0.1:8000/
```

> **Note**: Cloudinary credentials are already hardcoded in `settings.py`. Videos are uploaded to the cloud automatically.

---

## 🌐 Deployment

The app is deployed on **HuggingFace Spaces** using Docker:
- `Dockerfile` defines the container
- Port `7860` is used (HuggingFace standard)
- Gunicorn serves the Django app in production
- Database: **Neon PostgreSQL** (configured via `DATABASE_URL` environment variable)
- Media storage: **Cloudinary** (so files survive container restarts)
- Static files: Served by **WhiteNoise** directly from Django

