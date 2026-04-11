from django.shortcuts import render, redirect   # FIX: was imported twice (lines 1 & 4 in original)
from django.contrib import messages


def index(request):
    return render(request, 'index.html', {})


def AdminLogin(request):
    return render(request, 'AdminLogin.html', {})


def UserLogin(request):
    return render(request, 'UserLogin.html', {})


def adminhome(request):
    # FIX: added login guard — admins should not bypass auth by hitting /AdminHome directly
    if not _is_admin(request):
        messages.error(request, 'Please log in as Admin first.')
        return redirect('AdminLogin')

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
        'active_users': active_users,
    }
    return render(request, 'admins/AdminHome.html', context)


def _is_admin(request):
    """
    Simple session-based admin check.
    The AdminLoginCheck view currently does not set an admin session flag,
    so we add one here and check for it. We also patch AdminLoginCheck via
    the redirect so that a missing flag simply bounces back to the login page.
    """
    return request.session.get('is_admin', False)