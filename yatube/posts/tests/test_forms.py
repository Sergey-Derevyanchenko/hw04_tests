from django.test import Client, TestCase
from django.shortcuts import get_object_or_404
from django.urls import reverse

from ..models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Auth_user')
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

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post_form(self):
        posts = Post.objects.count()
        form_data = {
            'text': self.post.text,
            'group': self.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data
        )
        self.assertEqual(posts + 1, Post.objects.count())

        last_post = Post.objects.latest('pub_date')
        self.assertEqual(form_data['text'], last_post.text)
        self.assertEqual(form_data['group'], last_post.group.id)
        self.assertEqual(self.user.username, last_post.author.username)
        self.assertRedirects(
            response, reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            )
        )

    def test_edit_post_form(self):
        posts = Post.objects.count()
        form_data = {
            'text': self.post.text * 2,
            'group': self.group.id
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id}
            ), data=form_data
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            )
        )
        post = get_object_or_404(Post, pk=self.post.id)
        self.assertEqual(form_data['text'], post.text)
        self.assertEqual(form_data['group'], post.group.id)
        self.assertEqual(posts, Post.objects.count())
