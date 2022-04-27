from django import forms
from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, User

from ..forms import PostForm


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Auth_user')
        cls.group = Group.objects.create(
            title='test_group_1',
            slug='test_slug_1',
            description='test_description_1',
        )
        cls.group_test = Group.objects.create(
            title='test_group_2',
            slug='test_slug_2',
            description='test_description_2'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='test_post',
        )
        cls.templates_urls = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': cls.user.username}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': cls.post.id}):
                'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': cls.post.id}):
                'posts/post_create.html',
            reverse('posts:post_create'): 'posts/post_create.html',
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def post_check(self, post):
        self.assertEqual(post.id, self.post.id)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, self.post.group)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for url, template in self.templates_urls.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_home_page_correct_context(self):
        """Шаблон главной страницы сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.context['page_obj'][0], self.post)

    def test_group_list_page_correct_context(self):
        """Проверка списка постов отфильтрованных по группе."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        post = response.context['page_obj'][0]
        self.post_check(post)
        self.assertEqual(response.context["group"], self.group)

    def test_group_list_page_correct_context(self):
        """Проверка списка постов отфильтрованных по пользователю."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        post = response.context['page_obj'][0]
        self.post_check(post)
        self.assertEqual(self.user, response.context["author"])

    def test_group_list_page_id_correct_context(self):
        """Проверка одного поста отфильтрованного по id."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(
            response.context.get('post').author.posts.count(),
            len(self.user.posts.select_related('author')))
        self.assertEqual(response.context.get('post').author, self.user)

    def test_creat_page_correct_context(self):
        """Шаблон создания поста с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'group': forms.models.ChoiceField,
            'text': forms.fields.CharField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                self.assertIsInstance(
                    response.context['form'].fields[value], expected)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'group': forms.fields.ChoiceField,
            'text': forms.fields.CharField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                self.assertIsInstance(
                    response.context['form'].fields[value], expected)
        self.assertIsInstance(response.context.get('form'), PostForm)

    def test_post_new_create_appears_on_correct_pages(self):
        """При создании поста он должен появляется на главной странице,
        на странице выбранной группы и в профиле пользователя"""
        pages = [
            reverse('posts:index'),
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': self.user.username})
        ]
        for urls in pages:
            with self.subTest(urls=urls):
                response = self.authorized_client.get(urls)
                self.assertIn(self.post, response.context['page_obj'])

    def test_post_in_the_right_group(self):
        """ Проверяем что пост не попал в другую группу """
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test_slug_2'}))
        self.assertEqual(len(response.context['page_obj']), 0)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Auth_user')
        cls.group = Group.objects.create(
            title='test_group',
            slug='test_slug',
            description='test_description',
        )
        cls.posts = []
        for test_post in range(13):
            cls.posts.append(Post(
                author=cls.user,
                text=f'{test_post}',
                group=cls.group)
            )
        Post.objects.bulk_create(cls.posts)
        cls.templates = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}),
            reverse('posts:profile', kwargs={'username': cls.user.username})
        ]
        cls.templates2 = [
            reverse('posts:index') + '?page=2',
            reverse('posts:group_list', kwargs={'slug': cls.group.slug})
            + '?page=2',
            reverse('posts:profile', kwargs={'username': cls.user.username})
            + '?page=2'
        ]

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_page_has_ten_posts(self):
        """Проверяет, что на первой странице 10 постов."""
        for page in self.templates:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']), settings.POSTS_PER_PAGE
                )

    def test_rests_of_the_posts_next_page(self):
        """Проверяет, что на второй странице 3 поста."""
        for page in self.templates2:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']),
                    settings.POSTS_PER_PAGE_2
                )
