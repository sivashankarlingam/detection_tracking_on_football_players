# Create your views here.
from django.shortcuts import render, redirect
from django.contrib import messages
from users.models import UserRegistrationModel
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import time


# Create your views here.
def AdminLoginCheck(request):
    if request.method == 'POST':
        usrid = request.POST.get('loginid')
        pswd = request.POST.get('pswd')
        print("User ID is = ", usrid)
        if usrid == 'admin' and pswd == 'admin':
            return redirect('AdminHome')

        else:
            messages.success(request, 'Please Check Your Login Details')
    return render(request, 'AdminLogin.html', {})



def RegisterUsersView(request):
    data = UserRegistrationModel.objects.all()
    return render(request, 'admins/viewregisterusers.html', context={'data': data})




@csrf_exempt
def ActivaUsers(request):
    if request.method == 'POST':
        user_id = request.POST.get('uid')
        if user_id:
            try:
                UserRegistrationModel.objects.filter(id=user_id).update(status='activated')
                messages.success(request, 'Member account successfully activated!')
            except Exception as e:
                return HttpResponse(str(e))
    return redirect(f'/userDetails?t={int(time.time())}')

@csrf_exempt
def DeleteUsers(request):
    if request.method == 'POST':
        user_id = request.POST.get('uid')
        if user_id:
            try:
                UserRegistrationModel.objects.filter(id=user_id).delete()
                messages.success(request, 'Member was permanently removed from the system.')
            except Exception as e:
                return HttpResponse(str(e))
    return redirect(f'/userDetails?t={int(time.time())}')

@csrf_exempt
def EditUsers(request):
    if request.method == 'POST':
        user_id = request.POST.get('uid')
        if user_id:
            try:
                user = UserRegistrationModel.objects.get(id=user_id)
                user.name = request.POST.get('name')
                user.mobile = request.POST.get('mobile')
                user.email = request.POST.get('email')
                user.address = request.POST.get('address')
                user.city = request.POST.get('city')
                user.state = request.POST.get('state')
                
                profile_image = request.FILES.get('profile_image')
                if profile_image:
                    user.profile_image = profile_image
                user.save()
                messages.success(request, f'Profile for {user.name} updated successfully.')
            except Exception as e:
                return HttpResponse(str(e))
    return redirect(f'/userDetails?t={int(time.time())}')
