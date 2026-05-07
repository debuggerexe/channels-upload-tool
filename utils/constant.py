import enum
from pathlib import Path
from conf import BASE_DIR


# ==================== Bilibili 常量 ====================
class BilibiliZoneTypes(enum.Enum):
    """Bilibili 视频分区"""
    ANIMATION = 1  # 动画
    DOUJIN = 24    # MAD·AMV
    ANIME = 25     # MMD·3D
    SHORTPLAY = 27  # 短片·手书·配音
    ANIME_OTHER = 47  # 动画综合
    COMIC = 13     # 番剧
    COMIC_CHINESE = 51  # 国产动画
    COMIC_INFO = 152  # 番剧资讯
    COMIC_OFFICIAL = 83  # 官方延伸
    DOCUMENTARY = 177  # 纪录片
    DOCUMENTARY_CHINA = 37  # 人文·历史
    DOCUMENTARY_SCIENCE = 178  # 科学·探索·自然
    DOCUMENTARY_MILITARY = 179  # 军事
    DOCUMENTARY_SOCIAL = 180  # 社会·美食·旅行
    MOVIE = 23     # 电影
    MOVIE_CHINESE = 147  # 华语电影
    MOVIE_WEST = 145  # 欧美电影
    MOVIE_JP = 146  # 日本电影
    MOVIE_OTHER = 83  # 其他国家
    TV = 11        # 电视剧
    TV_CHINESE = 185  # 国产剧
    TV_WEST = 187  # 海外剧
    ENTERTAINMENT = 5  # 娱乐
    ENTERTAINMENT_STAR = 71  # 综艺
    ENTERTAINMENT_KOREAN = 131  # 明星
    ENTERTAINMENT_MOVIE = 137  #  Korea综艺
    ENTERTAINMENT_CHINA = 136  # China综艺
    VARIETY = 241  # 综艺
    GAME = 4       # 游戏
    GAME_STANDALONE = 17  # 单机游戏
    GAME_ESPORTS = 171  # 电子竞技
    GAME_MOBILE = 172  # 手机游戏
    GAME_ONLINE = 65  # 网络游戏
    GAME_BOARD = 173  # 桌游棋牌
    GAME_GM = 121  # GMV
    GAME_MUSIC = 136  # 音游
    GAME_MUGEN = 19  # Mugen
    KICHIKU = 119  # 鬼畜
    KICHIKU_MAD = 22  # 鬼畜调教
    KICHIKU_DRAMA = 26  # 音MAD
    KICHIKU_MANUAL = 126  # 人力VOCALOID
    KICHIKU_COURSE = 127  # 鬼畜剧场
    FASHION = 155  # 时尚
    FASHION_MAKEUP = 157  # 美妆护肤
    FASHION_CLOTHES = 158  # 穿搭
    FASHION_MODEL = 159  # 时尚潮流
    LIFE = 160     # 生活
    LIFE_DAILY = 138  # 日常
    LIFE_FOOD = 21  # 美食圈
    LIFE_ANIMAL = 75  # 动物圈
    LIFE_HANDMAKE = 76  # 手工
    LIFE_PAINTING = 161  # 绘画
    LIFE_SPORTS = 162  # 运动
    LIFE_OTHER = 174  # 其他
    CAR = 176      # 汽车
    CAR_LOOK = 224  # 汽车生活
    CAR_TALK = 225  # 汽车测评
    CAR_OTHER = 208  # 汽车文化
    CAR_TECH = 209  # 汽车技术
    CAR_RACING = 216  # 赛车
    CAR_MOTO = 217  # 摩托车
    CAR_POLULAR = 218  # 智能出行
    SCIENCE = 36   # 知识
    SCIENCE_SCIENCE = 201  # 科学科普
    SCIENCE_SOCIAL = 124  # 社科·法律·心理
    SCIENCE_HUMAN = 207  # 人文历史
    SCIENCE_BUSINESS = 208  # 财经商业
    SCIENCE_DESIGN = 209  # 设计创意
    SCIENCE_WORK = 122  # 职场成长
    SCIENCE_SCHOOL = 39  # 校园学习
    SCIENCE_TEACHER = 96  # 教师
    TECH = 188     # 科技
    TECH_DIGITAL = 95  # 数码
    TECH_APPLICATION = 189  # 软件应用
    TECH_COMPUTER = 190  # 计算机技术
    TECH_INDUSTRY = 191  # 工业·工程·机械
    TECH_OTHER = 192  # 极客DIY
    SPORTS = 234   # 运动
    SPORTS_BASKETBALL = 235  # 篮球
    SPORTS_FOOTBALL = 249  # 足球
    SPORTS_ARENA = 238  # 竞技体育
    SPORTS_WRESTLING = 239  # 运动文化·大会员
    SPORTS_FITNESS = 164  # 运动综合
    SPORTS_TABLE = 236  # 运动综合
    SPORTS_OUTDOOR = 237  # 运动综合


# Bilibili Cookie 文件路径
BILIBILI_ACCOUNT_FILE = Path(BASE_DIR) / "cookies" / "bilibili" / "account.json"


class TencentZoneTypes(enum.Enum):
    LIFESTYLE = '生活'
    CUTE_KIDS = '萌娃'
    MUSIC = '音乐'
    KNOWLEDGE = '知识'
    EMOTION = '情感'
    TRAVEL_SCENERY = '旅行风景'
    FASHION = '时尚'
    FOOD = '美食'
    LIFE_HACKS = '生活技巧'
    DANCE = '舞蹈'
    MOVIES_TV_SHOWS = '影视综艺'
    SPORTS = '运动'
    FUNNY = '搞笑'
    CELEBRITIES = '明星名人'
    NEWS_INFO = '新闻资讯'
    GAMING = '游戏'
    AUTOMOTIVE = '车'
    ANIME = '二次元'
    TALENT = '才艺'
    CUTE_PETS = '萌宠'
    INDUSTRY_MACHINERY_CONSTRUCTION = '机械'
    ANIMALS = '动物'
    PARENTING = '育儿'
    TECHNOLOGY = '科技'
