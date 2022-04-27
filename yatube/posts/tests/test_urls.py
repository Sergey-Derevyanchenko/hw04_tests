from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User


class PostsURLTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Auth_user')
        cls.not_author = User.objects.create_user(username='Not_author')
        cls.group = Group.objects.create(
            title='test_group',
            slug='test_slug',
            description='test_description',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='test_post',
            group=cls.group,
        )
        cls.urls = [
            '/',
            f'/group/{cls.group.slug}/',
            f'/profile/{cls.user.username}/',
            f'/posts/{cls.post.id}/',
            "/unexisting_page/",
        ]
        cls.templates_urls = {
            '/': 'posts/index.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.user.username}/': 'posts/profile.html',
            f'/posts/{cls.post.id}/': 'posts/post_detail.html',
        }
        cls.templates_auth = {
            f'/posts/{cls.post.id}/edit/': 'posts/post_create.html',
            '/create/': 'posts/post_create.html',
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.not_author_client = Client()
        self.not_author_client.force_login(self.not_author)
        self.author_client = Client()
        self.author_client.force_login(self.post.author)

    def test_accessibility_of_urls_for_all(self):
        """Страницы доступны любому пользователю."""
        for url in self.urls:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                if url == "/unexisting_page/":
                    self.assertEqual(
                        response.status_code, HTTPStatus.NOT_FOUND)
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_of_templates(self):
        """URL-адрес использует соответствующий шаблон."""
        for url, template in self.templates_urls.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_post_edit_and_create_for_auth_user(self):
        """Страницы создания/редактирования поста
        доступны авторизованному пользователю.
        """
        for url in self.templates_auth:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_page_accessability_and_template_author(self):
        """Проверка доступности редактирования для автора поста"""
        response = self.author_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}
        ))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_and_create_for_non_auth_user(self):
        """Анониму не доступны страницы создания/редактирования поста."""
        for url in self.templates_auth:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_url_redirect_anonymous_on_login(self):
        """При попытке анонима получить доступ к созданию/редактированию поста,
        его редиректит на страницу логина.
        """
        self.assertRedirects(
            self.guest_client.get(reverse(
                'posts:post_edit', kwargs={'post_id': self.post.id})),
            reverse('users:login')
            + '?next=' + reverse(
                'posts:post_edit', kwargs={'post_id': self.post.id})
        )
        self.assertRedirects(
            self.guest_client.get(reverse('posts:post_create')),
            reverse('users:login') + '?next=' + reverse('posts:post_create')
        )

    def test_url_redirect_anonymous_on_login(self):
        """Не автора поста редиректит на страницу поста."""
        self.assertRedirects(
            self.not_author_client.get(reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id}),
                follow=True),
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
