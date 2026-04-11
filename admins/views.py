from django.shortcuts import render, redirect
from django.contrib import messages
from users.models import UserRegistrationModel


def AdminLoginCheck(request):
    if request.method == 'POST':
        usrid = request.POST.get('loginid')
        pswd  = request.POST.get('pswd')
        if usrid == 'admin' and pswd == 'admin':
            request.session['is_admin'] = True   # FIX: set session flag so AdminHome guard works
            return redirect('AdminHome')
        else:
            # FIX: was messages.success (green toast) for a FAILED login — corrected to messages.error
            messages.error(request, 'Invalid credentials. Please check your Login ID and Password.')
    return render(request, 'AdminLogin.html', {})


def RegisterUsersView(request):
    data = UserRegistrationModel.objects.all()
    return render(request, 'admins/viewregisterusers.html', {'data': data})


def ActivaUsers(request):
    if request.method == 'GET':
        user_id = request.GET.get('uid')
        if user_id:
            UserRegistrationModel.objects.filter(id=user_id).update(status='activated')
    return redirect('RegisterUsersView')


def DeleteUsers(request):
    if request.method == 'GET':
        user_id = request.GET.get('uid')
        if user_id:
            UserRegistrationModel.objects.filter(id=user_id).delete()
            messages.success(request, 'User deleted successfully!')
    return redirect('RegisterUsersView')


def EditUsers(request):
    if request.method == 'POST':
        user_id      = request.POST.get('uid')
        name         = request.POST.get('name')
        mobile       = request.POST.get('mobile')
        email        = request.POST.get('email')
        locality     = request.POST.get('locality')
        address      = request.POST.get('address')
        city         = request.POST.get('city')
        state        = request.POST.get('state')
        profile_image = request.FILES.get('profile_image')

        if user_id:
            try:
                user = UserRegistrationModel.objects.get(id=user_id)
                user.name     = name
                user.mobile   = mobile
                user.email    = email
                user.locality = locality
                user.address  = address
                user.city     = city
                user.state    = state
                
                if profile_image:
                    user.profile_image = profile_image
                user.save()
                messages.success(request, 'User updated successfully!')
            except UserRegistrationModel.DoesNotExist:
                messages.error(request, 'User not found.')

    return redirect('RegisterUsersView')
