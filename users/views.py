from django.shortcuts import render, redirect
import os
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.http import JsonResponse
from .models import UserRegistrationModel, VideoAnalysis
from .tasks import trigger_video_processing
from django.contrib import messages

def upload_video(request):
    # Ensure user is logged in
    if 'id' not in request.session:
        return redirect('UserLogin')
        
    if request.method == 'POST' and request.FILES.get('video'):
        uploaded_file = request.FILES['video']
        fs = FileSystemStorage()
        input_path = fs.save(uploaded_file.name, uploaded_file)
        
        # Create VideoAnalysis record
        user = UserRegistrationModel.objects.get(id=request.session['id'])
        analysis = VideoAnalysis.objects.create(
            user=user,
            input_video=input_path,
            status='Pending',
            progress=0
        )
        
        # Trigger async background processing
        trigger_video_processing(analysis.id)
        
        # Return JSON for AJAX handler in upload.html
        return JsonResponse({
            'status': 'processing',
            'analysis_id': analysis.id
        })
        
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
    import json
    try:
        analysis = VideoAnalysis.objects.get(id=analysis_id)
        
        try:
            context_user = UserRegistrationModel.objects.get(id=request.session.get('id'))
        except Exception:
            context_user = None

        context = {
            'video_url': fs_url(analysis.output_video) if analysis.output_video else '',
            'original_video_url': fs_url(analysis.input_video) if analysis.input_video else '',
            'status': analysis.status,
            'progress': analysis.progress,
            'analysis_id': analysis.id,
            'logged_in_user': context_user
        }
        
        # Load JSON metrics if available
        metrics = {}
        if analysis.output_video:
            json_path = analysis.output_video.path.rsplit('.', 1)[0] + "_metrics.json"
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    metrics = json.load(f)

        # Parse data safely
        speeds = metrics.get('player_speeds', {})
        distances = metrics.get('player_distances', {})
        possession = metrics.get('possession', {"Team A": 1, "Team B": 1, "Contested": 1})
        max_ball_speed = metrics.get('max_ball_speed', 0.0)

        # Sort for top 5
        top_speeds_sorted = sorted(speeds.items(), key=lambda item: item[1], reverse=True)[:5]
        top_dists_sorted = sorted(distances.items(), key=lambda item: item[1], reverse=True)[:5]
        
        context['speed_labels'] = json.dumps([f"Player {k}" for k, v in top_speeds_sorted])
        context['speed_data'] = json.dumps([v for k, v in top_speeds_sorted])
        context['dist_labels'] = json.dumps([f"Player {k}" for k, v in top_dists_sorted])
        context['dist_data'] = json.dumps([v for k, v in top_dists_sorted])
        context['possession_data'] = json.dumps([possession.get("Team A", 0), possession.get("Team B", 0), possession.get("Contested", 0)])
        context['max_ball_speed'] = max_ball_speed
        
    except Exception as e:
        print("Error in result parsing:", e)
        context = {'video_url': '', 'original_video_url': '', 'speed_labels': '[]', 'speed_data': '[]', 'dist_labels': '[]', 'dist_data': '[]', 'possession_data': '[]', 'max_ball_speed': 0}
        
    return render(request, 'users/result.html', context)

def fs_url(path):
    if not path: return ""
    # Standardize path for media URL
    return os.path.join(settings.MEDIA_URL, str(path)).replace('\\', '/')

def UserRegisterActions(request):
    if request.method == 'POST':
        try:
            user = UserRegistrationModel(
                name=request.POST.get('name'),
                loginid=request.POST.get('loginid'),
                password=request.POST.get('password'),
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
        except Exception as e:
            messages.error(request, "Registration failed: This Email, Login ID, or Mobile number is securely tracked and already registered to another account.")
    return render(request, 'UserRegistrations.html') 

def UserLoginCheck(request):
    if request.method == "POST":
        loginid = request.POST.get('loginid')
        pswd = request.POST.get('pswd')
        try:
            check = UserRegistrationModel.objects.get(loginid=loginid, password=pswd)
            if check.status == "activated":
                request.session['id'] = check.id
                request.session['loggeduser'] = check.name
                request.session['loginid'] = loginid
                request.session['email'] = check.email
                return redirect('UserHome')
            else:
                messages.error(request, 'Your Account is not activated yet.')
                return render(request, 'UserLogin.html')
        except Exception:
            messages.error(request, 'Invalid Login id and password')
    return render(request, 'UserLogin.html')

def UserHome(request):
    if 'id' not in request.session:
        return redirect('UserLogin')
    try:
        user = UserRegistrationModel.objects.get(id=request.session['id'])
        videos = VideoAnalysis.objects.filter(user=user).order_by('-created_at')
    except Exception as e:
        user = None
        videos = []
    return render(request, 'users/dashboard.html', {'videos': videos, 'logged_in_user': user})

def delete_video(request, analysis_id):
    if 'id' not in request.session:
        return redirect('UserLogin')
    try:
        user = UserRegistrationModel.objects.get(id=request.session['id'])
        analysis = VideoAnalysis.objects.get(id=analysis_id, user=user)
        
        # Optionally remove physical files from the system
        if analysis.input_video: analysis.input_video.delete(save=False)
        if analysis.output_video: analysis.output_video.delete(save=False)
        
        analysis.delete()
        messages.success(request, f"Video #{analysis_id} was successfully deleted.")
    except Exception as e:
        messages.error(request, f"Failed to delete video: {e}")
        
    return redirect('UserHome')

def index(request):
    return render(request, "index.html")

from django.http import StreamingHttpResponse
def live_webcam_feed(request):
    from .ai_pipeline import FootballTracker
    tracker = FootballTracker()
    return StreamingHttpResponse(tracker.generate_live_frames(), content_type='multipart/x-mixed-replace; boundary=frame')