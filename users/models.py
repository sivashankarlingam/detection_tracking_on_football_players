from django.db import models
from cloudinary_storage.storage import VideoMediaCloudinaryStorage
class UserRegistrationModel(models.Model):
    name = models.CharField(max_length=100)
    loginid = models.CharField(unique=True, max_length=100)
    password = models.CharField(max_length=100)
    mobile = models.CharField(unique=True, max_length=10)  # Adjusted max_length to 10 for mobile numbers
    email = models.EmailField(unique=True, max_length=100)  # Use EmailField for better validation
    locality = models.CharField(max_length=100)
    address = models.TextField(max_length=1000)  # Use TextField for longer addresses
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    status = models.CharField(max_length=100, default='waiting')
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return self.loginid

    class Meta:
        db_table = 'user_registrations'


class VideoAnalysis(models.Model):
    user = models.ForeignKey(UserRegistrationModel, on_delete=models.CASCADE)
    input_video = models.FileField(upload_to='videos/input/', storage=VideoMediaCloudinaryStorage())
    output_video = models.FileField(upload_to='videos/output/', storage=VideoMediaCloudinaryStorage(), blank=True, null=True)
    status = models.CharField(max_length=50, default='Pending') # Pending, Processing, Completed, Failed
    progress = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.name} - {self.status}"
    
    class Meta:
        db_table = 'video_analysis'
