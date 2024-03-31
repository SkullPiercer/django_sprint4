from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView
)

from .forms import PostForm, CommentForm, ProfileChangeForm
from .mixins import CommentMixin, QuerySetMixin
from .models import Post, Category, User

POSTS_ON_PAGE = 10


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


class ProfileListView(ListView):
    model = Post
    template_name = 'blog/profile.html'
    slug_url_kwarg = 'username'
    slug_field = 'username'
    paginate_by = POSTS_ON_PAGE
    ordering = ['-pub_date']

    def get_queryset(self):
        user = get_object_or_404(
            User,
            username=self.kwargs.get(self.slug_url_kwarg)
        )
        queryset = super().get_queryset().filter(author=user)
        if self.request.user != user:
            queryset = queryset.filter(
                category__is_published=True,
                is_published=True
            )
        else:
            queryset = queryset.filter(
                Q(category__is_published=True)
                | Q(category__isnull=True)
                | Q(category__is_published=False)
            )
        annotated_queryset = queryset.annotate(comment_count=Count('comment'))
        return annotated_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = get_object_or_404(
            User,
            username=self.kwargs.get(self.slug_url_kwarg))
        return context


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


class PostDeleteView(UserPassesTestMixin, DeleteView):
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
        return (self.request.user == post.author
                or self.request.user.is_superuser)

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
        return reverse(
            'blog:profile', kwargs={'username': self.request.user.username}
        )


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        post = get_object_or_404(Post, pk=self.kwargs['post_id'])
        if self.request.user == post.author:
            return post
        return get_object_or_404(Post.objects.filter(
            author__isnull=False,
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True,
            pk=self.kwargs['post_id']
        ))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comment.all()
        return context


class PostListView(QuerySetMixin, ListView):
    model = Post
    ordering = ['-pub_date']
    paginate_by = POSTS_ON_PAGE
    template_name = 'blog/index.html'


class CommentCreateView(LoginRequiredMixin, CommentMixin, CreateView):
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        return get_object_or_404(Post, pk=self.kwargs['post_id'])

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = self.get_object()
        return super().form_valid(form)


class CommentUpdateView(UserPassesTestMixin, CommentMixin, UpdateView):
    template_name = 'blog/comment.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm(instance=self.get_object())
        return context

    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author


class CommentDeleteView(UserPassesTestMixin, CommentMixin, DeleteView):
    template_name = 'blog/comment.html'

    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author


class CategoryListView(QuerySetMixin, ListView):
    model = Post
    paginate_by = POSTS_ON_PAGE
    template_name = 'blog/category.html'
    ordering = ['-pub_date']

    def get_queryset(self):
        category_slug = self.kwargs.get('category_slug')
        category = get_object_or_404(Category, slug=category_slug)
        queryset = super().get_queryset().filter(
            category=category,
        )
        return queryset.annotate(comment_count=Count('comment'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_slug = self.kwargs.get('category_slug')
        category = get_object_or_404(Category, slug=category_slug)
        context['category'] = category
        return context

    def dispatch(self, request, *args, **kwargs):
        category_slug = self.kwargs.get('category_slug')
        get_object_or_404(
            Category,
            is_published=True,
            slug=category_slug
        )
        return super().dispatch(request, *args, **kwargs)
