from django.contrib import admin
from .models import Place,Rating

# Register your models here.
@admin.register(Place)
class placeAdmin(admin.ModelAdmin):
    list_display=('id','title','categories','image','placeweather')

@admin.register(Rating)
class ratingAdmin(admin.ModelAdmin):
    list_display=('user','place','rating','rated_date')

