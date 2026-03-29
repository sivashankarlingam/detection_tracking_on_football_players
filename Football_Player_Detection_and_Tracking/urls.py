"""
URL configuration for Football_Player_Detection_and_Tracking project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
# from django.urls import path
# from users import views
# from django.conf import settings
# from django.conf.urls.static import static
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', views.upload_video, name='upload_video'),
#     path('result/', views.result, name='result'),

# ]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


from django.contrib import admin
from django.urls import path
from users import views as usr
from django.conf import settings
from django.conf.urls.static import static
from admins import views as admins
from users import views as uv
from Football_Player_Detection_and_Tracking import views as mainView
from django.views.generic import TemplateView

urlpatterns = [
    path('sw.js', TemplateView.as_view(template_name='sw.js', content_type='application/javascript'), name='sw.js'),
    path('admin/', admin.site.urls),
    path("", mainView.index, name="index"),
    path("index", mainView.index, name="index"),
    path("Adminlogin", mainView.AdminLogin, name="AdminLogin"),
    path("UserLogin", mainView.UserLogin, name="UserLogin"),
    path('AdminHome', mainView.adminhome, name='AdminHome'),
  
    # admin views
    path('force_migrate/', admins.force_migrate, name='force_migrate'),
    path("AdminLogincheck", admins.AdminLoginCheck, name="AdminLoginCheck"),
    path('userDetails', admins.RegisterUsersView, name='RegisterUsersView'),
    path('ActivUsers/', admins.ActivaUsers, name='activate_users'),
    path('DeleteUsers/', admins.DeleteUsers, name='delete_users'),
    path('EditUsers/', admins.EditUsers, name='edit_users'),
    
    #userurls
    path('UserRegisterForm',uv.UserRegisterActions,name='UserRegisterForm'),
    path("UserLoginCheck/", usr.UserLoginCheck, name="UserLoginCheck"),
    path("UserHome/", usr.UserHome, name="UserHome"),
    path('prediction/', usr.upload_video, name='prediction'),
    path('delete_video/<int:analysis_id>/', usr.delete_video, name='delete_video'),
    path('live_feed/', usr.live_webcam_feed, name='live_webcam_feed'),
    path("index/", usr.index, name="index"),
    path('api/status/<int:analysis_id>/', usr.check_status, name='check_status'),
    path('result/<int:analysis_id>/', usr.result, name='result'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
