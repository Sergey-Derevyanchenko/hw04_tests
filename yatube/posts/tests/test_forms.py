from http import HTTPStatus

from django.test import Client, TestCase
from django.shortcuts import get_object_or_404
from django.urls import reverse

from ..models import Group, Post, User


class PostsFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Auth_user')
        cls.test_user = User.objects.create_user(username='Test_user')
        cls.group = Group.objects.create(
            title='test_group',
            slug='test_slug',
            description='test_description',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='test_text',
            group=cls.group,
        )
        cls.form_data = {
            'text': cls.post.text,
            'group': cls.group.id,
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_test_client = Client()
        self.authorized_test_client.force_login(self.test_user)

    def test_create_post_form(self):
        """При отправке валидной формы со страницы создания
        поста создаётся новая запись в базе данных.
        """
        posts = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=self.form_data
        )
        self.assertEqual(posts + 1, Post.objects.count())

        last_post = Post.objects.order_by('id').last()
        self.assertEqual(self.form_data['text'], last_post.text)
        self.assertEqual(self.form_data['group'], last_post.group.id)
        self.assertEqual(self.user.username, last_post.author.username)
        self.assertRedirects(
            response, reverse(
                'posts:profile', kwargs={'username': self.user.username})
        )

    def test_edit_post_form(self):
        """При отправке валидной формы со страницы редактирования поста
        происходит изменение поста с post_id в базе данных.
        """
        posts = Post.objects.count()
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.id}),
            data=self.form_data
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            )
        )
        post = get_object_or_404(Post, pk=self.post.id)
        self.assertEqual(self.form_data['text'], post.text)
        self.assertEqual(self.form_data['group'], post.group.id)
        self.assertEqual(posts, Post.objects.count())

    def test_anonym_client_create_post(self):
        """Проверка возможности создания записи без регистрации."""
        post_count = Post.objects.count()
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=self.form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count)
        self.assertRedirects(
            response,
            reverse('users:login') + '?next=/create/'
        )
        self.assertEqual(Post.objects.count(), post_count)

    def test_create_post_without_group(self):
        """Публикация записи без группы."""
        post_count = Post.objects.count()
        context = {
            'text': 'Текстовый текст',
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=context,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.user})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(Post.objects.latest('id').text, context['text'])

    def test_edit_other_user_post(self):
        """Проверка возможности редактировать чужие записи."""
        form_data = {
            'text': 'Отредактированный текст поста',
        }
        response = self.authorized_test_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        post = Post.objects.get(id=self.post.pk)
        self.assertEqual(post.text, self.post.text)
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
