from django.urls import path
from . import views
urlpatterns = [
    path('sentiment/<str:s>/<int:n>', views.sentiment),
    path('top', views.top_w_l),
    path('ticker', views.ticker),
    path('historical', views.historical)
]
