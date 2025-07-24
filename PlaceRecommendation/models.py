from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Place(models.Model):
    title=models.CharField(max_length=70)
    categories=models.CharField(max_length=70)
    image=models.ImageField(upload_to="place_image")
    placeweather=models.CharField(max_length=70)
    def __str__(self):
        return str(self.pk)

class Rating(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,default=None)
    place=models.ForeignKey(Place,on_delete=models.CASCADE,default=None)
    rating=models.CharField(max_length=70)
    rated_date=models.DateTimeField(auto_now_add=True)
    




