# api, views.py:
from django.shortcuts import render, redirect


def api_root_view(request):
    #return redirect('api-root')  # api-root is conflicting name here, as drf default router / djoser also uses it.
	return redirect('/api/')  # Direct URL redirect, as it was adding /auth at end for djoser.
