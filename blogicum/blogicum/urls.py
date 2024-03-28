from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.contrib.auth.forms import UserCreationForm
from django.views.generic.edit import CreateView
from django.conf.urls.static import static
from django.conf import settings


handler404 = 'core.views.page_not_found'
CSRF_FAILURE_VIEW = 'core.views.csrf_failure'
handler500 = 'core.views.server_issues'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('blog.urls', namespace='blog')),
    path('posts/', include('blog.urls', namespace='blog_posts')),
    path('category/', include('blog.urls', namespace='blog_category')),
    path('pages/', include('pages.urls', namespace='pages')),
    path('profile/', include('blog.urls', namespace='blog')),
    path('auth/', include('django.contrib.auth.urls')),
    path(
        'auth/registration/',
        CreateView.as_view(
            template_name='registration/registration_form.html',
            form_class=UserCreationForm,
            success_url=reverse_lazy('blog:index')
        ),
        name='registration',
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
