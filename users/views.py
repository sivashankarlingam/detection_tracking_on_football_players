from django.shortcuts import render, redirect   # FIX: removed duplicate import that existed on lines 1 & 4
import os
import json
import base64
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import UserRegistrationModel, VideoAnalysis
from .tasks import trigger_video_processing
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .ai_pipeline import FootballTracker

# Global model initialization for live frames to prevent lag
global_tracker = FootballTracker()
global_tracker.initialize_model()

# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────
def fs_url(path):
    """Return a proper media-relative URL from a FileField value."""
    if not path:
        return ""
    return os.path.join(settings.MEDIA_URL, str(path)).replace('\\', '/')


# ─────────────────────────────────────────────────────────────────────────────
# Public pages
# ─────────────────────────────────────────────────────────────────────────────
def index(request):
    return render(request, "index.html")


def sw_js(request):
    """Dummy service-worker to silence 404s from previously registered workers."""
    return HttpResponse("// Service worker disabled", content_type="application/javascript")


# ─────────────────────────────────────────────────────────────────────────────
# User registration / auth
# ─────────────────────────────────────────────────────────────────────────────
def UserRegisterActions(request):
    if request.method == 'POST':
        try:
            user = UserRegistrationModel(
                name=request.POST.get('name'),
                loginid=request.POST.get('loginid'),
                password=make_password(request.POST.get('password')),
                mobile=request.POST.get('mobile'),
                email=request.POST.get('email'),
                locality=request.POST.get('locality'),
                address=request.POST.get('address'),
                city=request.POST.get('city'),
                state=request.POST.get('state'),
                status='waiting',
                profile_image=request.FILES.get('profile_image')
            )
            user.save()
            messages.success(request, "Registration successful! You can now sign in.")
        except Exception:
            messages.error(request, "Registration failed: This Email, Login ID, or Mobile number is already registered.")
    return render(request, 'UserRegistrations.html')


def UserLoginCheck(request):
    if request.method == "POST":
        loginid = request.POST.get('loginid')
        pswd = request.POST.get('pswd')
        try:
            check = UserRegistrationModel.objects.get(loginid=loginid)
            if check_password(pswd, check.password):
                if check.status == "activated":
                    request.session['id'] = check.id
                    request.session['loggeduser'] = check.name
                    request.session['loginid'] = loginid
                    request.session['email'] = check.email
                    return redirect('UserHome')
                else:
                    messages.error(request, 'Your Account is not activated yet.')
                    return render(request, 'UserLogin.html')
            else:
                messages.error(request, 'Invalid Login id and password')
        except UserRegistrationModel.DoesNotExist:
            messages.error(request, 'Invalid Login id and password')
        except Exception:
            messages.error(request, 'An error occurred during login')
    return render(request, 'UserLogin.html')


def logout_view(request):
    """FIX: properly clears ALL session data — old navbar 'logout' just redirected to index without clearing session."""
    request.session.flush()
    messages.success(request, 'You have been successfully logged out.')
    return redirect('index')


# ─────────────────────────────────────────────────────────────────────────────
# User dashboard
# ─────────────────────────────────────────────────────────────────────────────
def UserHome(request):
    if 'id' not in request.session:
        return redirect('UserLogin')
    try:
        user = UserRegistrationModel.objects.get(id=request.session['id'])
        videos = VideoAnalysis.objects.filter(user=user).order_by('-created_at')
    except Exception:
        user = None
        videos = []
    return render(request, 'users/dashboard.html', {'videos': videos, 'logged_in_user': user})


def delete_video(request, analysis_id):
    if 'id' not in request.session:
        return redirect('UserLogin')
    try:
        user = UserRegistrationModel.objects.get(id=request.session['id'])
        analysis = VideoAnalysis.objects.get(id=analysis_id, user=user)
        if analysis.input_video:  analysis.input_video.delete(save=False)
        if analysis.output_video:
            json_path = analysis.output_video.path.rsplit('.', 1)[0] + "_metrics.json"
            if os.path.exists(json_path):
                os.remove(json_path)
            analysis.output_video.delete(save=False)
        analysis.delete()
        messages.success(request, f"Video #{analysis_id} was successfully deleted.")
    except Exception as e:
        messages.error(request, f"Failed to delete video: {e}")
    return redirect('UserHome')


# ─────────────────────────────────────────────────────────────────────────────
# Video upload & analysis
# ─────────────────────────────────────────────────────────────────────────────
def upload_video(request):
    if 'id' not in request.session:
        return redirect('UserLogin')

    if request.method == 'POST' and request.FILES.get('video'):
    if request.method == 'POST' and request.FILES.get('video'):
        uploaded_file = request.FILES['video']
        user = UserRegistrationModel.objects.get(id=request.session['id'])
        
        # Save directly to model, which will use Cloudinary automatically
        analysis = VideoAnalysis.objects.create(
            user=user,
            input_video=uploaded_file,
            status='Pending',
            progress=0
        )
        trigger_video_processing(analysis.id)
        return JsonResponse({'status': 'processing', 'analysis_id': analysis.id})

    try:
        context_user = UserRegistrationModel.objects.get(id=request.session['id'])
    except Exception:
        context_user = None
    return render(request, 'users/upload.html', {'logged_in_user': context_user})


def check_status(request, analysis_id):
    try:
        analysis = VideoAnalysis.objects.get(id=analysis_id)
        return JsonResponse({
            'status': analysis.status,
            'progress': analysis.progress,
            'redirect_url': f'/result/{analysis.id}/' if analysis.status == 'Completed' else None
        })
    except VideoAnalysis.DoesNotExist:
        return JsonResponse({'status': 'Failed', 'progress': 0}, status=404)


def result(request, analysis_id):
    # FIX: auth guard — unauthenticated users cannot view any result page
    if 'id' not in request.session:
        return redirect('UserLogin')

    try:
        analysis = VideoAnalysis.objects.get(id=analysis_id)

        # FIX: ownership check — users can only view their own analyses
        if analysis.user_id != request.session.get('id'):
            messages.error(request, 'You do not have permission to view this analysis.')
            return redirect('UserHome')

        try:
            context_user = UserRegistrationModel.objects.get(id=request.session.get('id'))
        except Exception:
            context_user = None

        context = {
            'video_url':          fs_url(analysis.output_video) if analysis.output_video else '',
            'original_video_url': fs_url(analysis.input_video)  if analysis.input_video  else '',
            'status':      analysis.status,
            'progress':    analysis.progress,
            'analysis_id': analysis.id,
            'logged_in_user': context_user,
        }

        # Load JSON metrics if available
        metrics = {}
        if analysis.output_video:
            json_path = analysis.output_video.path.rsplit('.', 1)[0] + "_metrics.json"
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    metrics = json.load(f)

        speeds      = metrics.get('player_speeds',    {})
        distances   = metrics.get('player_distances', {})
        possession  = metrics.get('possession',       {"Team A": 1, "Team B": 1, "Contested": 1})
        max_ball_speed = metrics.get('max_ball_speed', 0.0)

        top_speeds_sorted = sorted(speeds.items(),    key=lambda x: x[1], reverse=True)[:5]
        top_dists_sorted  = sorted(distances.items(), key=lambda x: x[1], reverse=True)[:5]

        context['speed_labels']    = json.dumps([f"Player {k}" for k, v in top_speeds_sorted])
        context['speed_data']      = json.dumps([v for k, v in top_speeds_sorted])
        context['dist_labels']     = json.dumps([f"Player {k}" for k, v in top_dists_sorted])
        context['dist_data']       = json.dumps([v for k, v in top_dists_sorted])
        context['possession_data'] = json.dumps([
            possession.get("Team A", 0),
            possession.get("Team B", 0),
            possession.get("Contested", 0),
        ])
        context['max_ball_speed'] = max_ball_speed

    except Exception as e:
        print("Error in result parsing:", e)
        context = {
            'video_url': '', 'original_video_url': '',
            'speed_labels': '[]', 'speed_data': '[]',
            'dist_labels': '[]', 'dist_data': '[]',
            'possession_data': '[]', 'max_ball_speed': 0,
        }

    return render(request, 'users/result.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Live webcam views
# ─────────────────────────────────────────────────────────────────────────────
def live_webcam_feed(request):
    """Server-side MJPEG stream from server's own webcam."""
    from .ai_pipeline import FootballTracker
    tracker = FootballTracker()
    return StreamingHttpResponse(
        tracker.generate_live_frames(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


@csrf_exempt
def process_live_frame(request):
    """
    FIX: was completely missing — live-cam JS in upload.html POSTed frames here
    and got a 404 crash every 100 ms.
    Now accepts a base64 JPEG from the browser, runs YOLO inference, and returns
    an annotated base64 JPEG so the frontend can display it in real time.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        import numpy as np
        import cv2
        body       = json.loads(request.body)
        image_data = body.get('image', '')
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        img_bytes = base64.b64decode(image_data)
        np_arr    = np.frombuffer(img_bytes, np.uint8)
        frame     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return JsonResponse({'error': 'Invalid image data'}, status=400)

        # Use the globally initialized tracker to prevent huge lag on every POST
        if global_tracker.model is not None:
            results = global_tracker.model.track(frame, persist=False, classes=[0, 32], verbose=False)
            if results and results[0].boxes:
                clss = results[0].boxes.cls.int().cpu().numpy()
                for box, cls in zip(results[0].boxes.xyxy.cpu().numpy(), clss):
                    x1, y1, x2, y2 = map(int, box)
                    color = (0, 255, 0) if cls == 0 else (0, 0, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = "Player" if cls == 0 else "Ball"
                    cv2.putText(frame, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        encoded   = base64.b64encode(buffer).decode('utf-8')
        return JsonResponse({'image': 'data:image/jpeg;base64,' + encoded})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)