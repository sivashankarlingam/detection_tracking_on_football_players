from django.shortcuts import render


from django.shortcuts import render


def index(request):
    return render(request, 'index.html', {})

def AdminLogin(request):
    return render(request, 'AdminLogin.html', {})

def UserLogin(request):
    return render(request, 'UserLogin.html', {})


def adminhome(request):
    try:
        from users.models import UserRegistrationModel, VideoAnalysis
        total_videos = VideoAnalysis.objects.count()
        active_users = UserRegistrationModel.objects.filter(status='activated').count()
    except Exception as e:
        total_videos = 0
        active_users = 0
        print("Error fetching metrics:", str(e))
        
    context = {
        'total_videos': total_videos,
        'active_users': active_users
    }
    return render(request, 'admins/AdminHome.html', context)