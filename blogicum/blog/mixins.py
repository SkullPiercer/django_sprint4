from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from .forms import CommentForm
from .models import Post, Comment


class CommentMixin:
    model = Comment
    form_class = CommentForm
    pk_url_kwarg = 'comment_id'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:post_detail', kwargs={'post_id': self.object.post.pk}
        )


class PostMixin:
    model = Post

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class QuerySetMixin:
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            author__isnull=False,
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True
        )
        return queryset.annotate(comment_count=Count('comment'))
