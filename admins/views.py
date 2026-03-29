# Create your views here.
from django.shortcuts import render,redirect
from django.contrib import messages
from users.models import UserRegistrationModel


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
    try:
        data = list(UserRegistrationModel.objects.all())
        return render(request, 'admins/viewregisterusers.html', context={'data': data})
    except Exception as e:
        from django.http import HttpResponse
        import traceback
        return HttpResponse(f"<h1>DEBUG TRACEBACK</h1><pre>{traceback.format_exc()}</pre>")




def ActivaUsers(request):
    if request.method == 'GET':
        user_id = request.GET.get('uid')
        
        if user_id:  # Ensure user_id is not None
            status = 'activated'
            print("Activating user with ID =", user_id)
            UserRegistrationModel.objects.filter(id=user_id).update(status=status)

        # Redirect to the view where users are listed after activation
        return redirect('RegisterUsersView')  # Replace with your actual URL name

def DeleteUsers(request):
    if request.method == 'GET':
        user_id = request.GET.get('uid')
        
        if user_id:
            print("Deleting user with ID =", user_id)
            UserRegistrationModel.objects.filter(id=user_id).delete()
            messages.success(request, 'User deleted successfully!')

        return redirect('RegisterUsersView')

def EditUsers(request):
    if request.method == 'POST':
        user_id = request.POST.get('uid')
        name = request.POST.get('name')
        mobile = request.POST.get('mobile')
        email = request.POST.get('email')
        profile_image = request.FILES.get('profile_image')
        
        if user_id:
            try:
                user = UserRegistrationModel.objects.get(id=user_id)
                user.name = name
                user.mobile = mobile
                user.email = email
                if profile_image:
                    user.profile_image = profile_image
                user.save()
                messages.success(request, 'User edited successfully!')
            except UserRegistrationModel.DoesNotExist:
                messages.error(request, 'User not found.')
            
    return redirect('RegisterUsersView')


