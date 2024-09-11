from django.db import models
import json
# Create your models here.

ISNB_API_KEY = '49362_31d07a934c83615557535181e8865d16'
# 9780452262935
# 9781440352928
class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    description = models.CharField(max_length=500, default=None)
    price = models.FloatField(null=True, blank=True)
    image_url = models.CharField(max_length=2100, blank=True)
    book_available = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def get_author(self):
        return self.author
    
    
