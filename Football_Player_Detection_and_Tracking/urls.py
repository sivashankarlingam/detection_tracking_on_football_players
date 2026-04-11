"""
URL configuration for Football_Player_Detection_and_Tracking project.
"""

from django.contrib import admin
from django.urls import path
from users import views as usr          # single import alias — no duplicate 'uv'
from django.conf import settings
from django.conf.urls.static import static
from admins import views as admins
from Football_Player_Detection_and_Tracking import views as mainView


urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Landing / auth ──────────────────────────────────────────────────────
    path('',          mainView.index,      name='index'),
    path('index',     mainView.index,      name='index_page'),   # FIX: was also 'index' → conflict removed
    path('Adminlogin',mainView.AdminLogin, name='AdminLogin'),
    path('UserLogin', mainView.UserLogin,  name='UserLogin'),
    path('AdminHome', mainView.adminhome,  name='AdminHome'),

    # ── Admin views ─────────────────────────────────────────────────────────
    path('AdminLogincheck', admins.AdminLoginCheck,   name='AdminLoginCheck'),
    path('userDetails',     admins.RegisterUsersView, name='RegisterUsersView'),
    path('ActivUsers/',     admins.ActivaUsers,       name='activate_users'),
    path('DeleteUsers/',    admins.DeleteUsers,        name='delete_users'),
    path('EditUsers/',      admins.EditUsers,          name='edit_users'),

    # ── User views ──────────────────────────────────────────────────────────
    path('UserRegisterForm',            usr.UserRegisterActions, name='UserRegisterForm'),
    path('UserLoginCheck/',             usr.UserLoginCheck,      name='UserLoginCheck'),
    path('UserHome/',                   usr.UserHome,            name='UserHome'),
    path('prediction/',                 usr.upload_video,        name='prediction'),
    path('delete_video/<int:analysis_id>/', usr.delete_video,   name='delete_video'),
    path('logout/',                     usr.logout_view,         name='logout'),   # FIX: proper session-clearing logout

    # ── API endpoints ───────────────────────────────────────────────────────
    path('live_feed/',                          usr.live_webcam_feed,   name='live_webcam_feed'),
    path('api/status/<int:analysis_id>/',       usr.check_status,       name='check_status'),
    path('api/process_live_frame/',             usr.process_live_frame, name='process_live_frame'),  # FIX: was missing → live-cam JS 404
    path('result/<int:analysis_id>/',           usr.result,             name='result'),
    path('sw.js',                               usr.sw_js,              name='sw.js'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
