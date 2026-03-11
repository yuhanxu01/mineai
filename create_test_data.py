import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'memoryforge.settings')
django.setup()

from accounts.models import User
from novel_share.models import SharedNovel, SharedChapter, NovelComment

user, _ = User.objects.get_or_create(email='test@example.com')
user.set_password('123456')
user.save()

novel, _ = SharedNovel.objects.get_or_create(
    title='灵境行者',
    author=user,
    synopsis='亘古通今，传闻世有灵境。关于灵境的说法，历朝历代的名人雅士众说纷纭，诗中记载：“自齐至唐，兹山濚洄，灵境交错。”',
    status='published'
)

SharedChapter.objects.get_or_create(
    novel=novel,
    number=1,
    title='第一章 新世界',
    content='张元清推开门，眼前的景色彻底改变了。\n\n熟悉的街道变成了破败的废墟，天空呈现出诡异的暗红色。他听到远处传来低沉的咆哮声。\n\n“这是哪里？”他喃喃自语。\n\n这只是开始，真正的危险还在后面。'
)

SharedChapter.objects.get_or_create(
    novel=novel,
    number=2,
    title='第二章 探索',
    content='适应了初始的震惊后，张元清开始寻找线索。废墟中到处都是战斗留下的痕迹。\n\n他发现了一个奇怪的徽章，上面刻着“夜游神”。\n\n这似乎是某个古老势力的标志，他在灵境中要面对的不仅仅是怪物，还有错综复杂的势力斗争。'
)

NovelComment.objects.get_or_create(
    user=user,
    novel=novel,
    content='这本书太棒了！非常有代入感。',
    rating=5
)

print("Test data created successfully.")
