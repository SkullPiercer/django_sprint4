from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView
)

from .forms import PostForm, CommentForm, ProfileChangeForm
from .models import Post, Category, User, Comment


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileChangeForm
    template_name = 'blog/user.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        slug = self.object.username
        return reverse('blog:profile', kwargs={'username': slug})


class PostUpdateView(UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

    def handle_no_permission(self):
        post_id = self.kwargs.get('post_id')
        return HttpResponseRedirect(
            reverse('blog:post_detail', kwargs={'post_id': post_id})
        )

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.pk})


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'
    success_url = reverse_lazy('blog:index')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm(instance=self.get_object())
        return context

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author\
            or self.request.user.is_superuser

    def handle_no_permission(self):
        post_id = self.kwargs.get('post_id')
        return HttpResponseRedirect(
            reverse('blog:post_detail', kwargs={'post_id': post_id})
        )


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile', kwargs={'username': self.request.user.username}
        )


class ProfileListView(ListView):
    model = Post
    template_name = 'blog/profile.html'
    slug_url_kwarg = 'username'
    slug_field = 'username'
    paginate_by = 10
    ordering = ['-pub_date']

    def get_queryset(self):

        user = get_object_or_404(
            User,
            username=self.kwargs.get(self.slug_url_kwarg)
        )
        queryset = super().get_queryset().filter(author=user)
        if self.request.user != user:
            now = timezone.now()
            queryset = queryset.filter(
                is_published=True,
                pub_date__lte=now,
                category__is_published=True
            )
        else:
            queryset = queryset.filter(
                Q(category__is_published=True) | Q(category__isnull=True) | Q(category__is_published=False))
        annotated_queryset = queryset.annotate(comment_count=Count('comment'))
        return annotated_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = get_object_or_404(
            User,
            username=self.kwargs.get(self.slug_url_kwarg))
        return context


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        now = timezone.now()
        if (not obj.is_published and self.request.user != obj.author) or (
                not obj.category.is_published and self.request.user != obj.author) or (
                not obj.pub_date <= now and self.request.user != obj.author
        ):
            raise Http404("Страница не найдена")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comment.all()
        return context


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        return get_object_or_404(Post, pk=self.kwargs['post_id'])

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = self.get_object()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.kwargs['post_id']})


class CommentUpdateView(UserPassesTestMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm(instance=self.get_object())
        return context

    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.post.pk})


class CommentDeleteView(UserPassesTestMixin, DeleteView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.post.pk})

    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author


class PostListView(ListView):
    model = Post
    ordering = ['-pub_date']
    paginate_by = 10
    template_name = 'blog/index.html'

    def get_queryset(self):
        now = timezone.now()
        queryset = super().get_queryset().filter(
            author__isnull=False,
            pub_date__lte=now,
            is_published=True,
            category__is_published=True
        )
        annotated_queryset = queryset.annotate(comment_count=Count('comment'))
        return annotated_queryset


class CategoryListView(ListView):
    model = Post
    paginate_by = 10
    template_name = 'blog/category.html'
    ordering = ['-pub_date']

    def get_queryset(self):
        category_slug = self.kwargs.get('category_slug')
        category = get_object_or_404(Category, slug=category_slug)
        queryset = super().get_queryset().filter(
            category=category,
            is_published=True,
            author__isnull=False,
            pub_date__lte=timezone.now()
        ).annotate(comment_count=Count('comment'))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_slug = self.kwargs.get('category_slug')
        category = get_object_or_404(Category, slug=category_slug)
        context['category'] = category
        return context

    def dispatch(self, request, *args, **kwargs):
        category_slug = self.kwargs.get('category_slug')
        category = get_object_or_404(Category, slug=category_slug)
        if not category.is_published:
            raise Http404
        return super().dispatch(request, *args, **kwargs)
