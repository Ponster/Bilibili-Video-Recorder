import asyncio
from bilibili_api import video
from bilibili_api import comment, sync
import pprint
import json
import time
import pandas as pd


# 调用库：https://github.com/MoyuScript/bilibili-api
# 参考文档：https://www.moyu.moe/bilibili-api/#/
# xml转ass：https://github.com/1299172402/danmu2ass-simply
# python ../danmaku2ass.py your_danmaku_dir.xml -fn 微软雅黑

class VideoInfo():
    def __init__(self, bvid="", cred=None):
        self.bvid = bvid
        self.cred = cred

        # 获取视频整体信息（异步）
        asyncio.get_event_loop().run_until_complete(self.init(bvid))

        # 获取视频其他信息
        self.comments, self.comments_num = sync(self.get_comments(aid=self.info['aid']))

    """
    用于抓取视频信息的异步类
    """

    async def init(self, bvid):
        # 实例化 Video 类
        self.video = video.Video(bvid=bvid)
        # 获取信息
        self.info = await self.video.get_info()

    """
    用于获取全部评论
    """

    async def get_comments(self, aid=None):
        # 存储评论
        comments = []
        # 页码
        page = 1
        # 当前已获取数量
        count = 0
        while True:
            # 获取评论
            c = await comment.get_comments(aid, comment.ResourceType.VIDEO, page, credential=self.cred)
            # 存储评论
            comments.extend(c['replies'])
            # 增加已获取数量
            count += c['page']['size']
            # 增加页码
            page += 1
            if count >= c['page']['count']:
                # 当前已获取数量已达到评论总数，跳出循环
                break

        # 确定是否有指置顶评论
        # （因为置顶评论和其它评论位置并没有存储在一起）
        self.has_top = c['upper']['top'] is not None
        if self.has_top:
            res = [c['upper']['top']]
            res.extend(comments)
        else:
            res = comments
        return res, len(res)

    """
    处理单条评论，传入一个存储单条评论信息的词典。
    | ID | 时间 | 用户 | 消息 | 点赞数 | 回复数 | 上级评论信息 |
    评论ID：cmt['rpid'], 
    评论者：cmt['member']['uname'], 
    评论内容：cmt['content']['message'], 
    评论时间：cmt['ctime'], 
    点赞数：cmt['like'], 
    回复数：cmt['rcount'], 
    根评论状态：cmt['root']. 
    """

    def get_single_comm_info(self, cmt):
        id = cmt['rpid']
        user = cmt['member']['uname']
        content = cmt['content']['message']
        time = self.ctime_conv(cmt['ctime'])
        like = cmt['like']
        reply = cmt['rcount']
        root = cmt['root']
        return [id, time, user, content, like, reply, root]

    ################# 用于存储和写入信息的函数 #################
    """
    用于存储视频信息（部分）到 'Video_info.txt' 文件中
    """

    def save_info(self, file_name=None):
        # 视频信息
        info_dict = {}
        ZH_titles = [
            'AV号', 'BV号', '视频名', '视频标签', '视频尺寸',
            '点赞数', '投币数', '收藏数', '分享数', '评论数',
            '观看数', '分P数', '封面链接', '视频时长', '发布时间'
        ]
        values = [
            self.info['aid'], self.info['bvid'], self.info['title'], self.info['tname'],
            " x ".join([str(self.info['dimension']['height']), str(self.info['dimension']['width'])]),
            self.info['stat']['like'], self.info['stat']['coin'], self.info['stat']['favorite'],
            self.info['stat']['share'], self.info['stat']['reply'], self.info['stat']['view'],
            self.info['videos'], self.info['pic'],
            self.duration_conv(self.info['duration']), self.ctime_conv(self.info['ctime'])
        ]
        # 视频信息变量，类型为 dict
        self.video_info = dict(zip(ZH_titles, values))
        self.write_info(
            ZH_titles, values, file_name=file_name, additional='【视频整体信息】：\n'
        )
        # self.write_json(self.info, 'info.json')

        # 分P信息
        self.write_info([], [], file_name=file_name, additional="【分P信息】：\n", write_method='a')
        pages_info = self.info['pages']
        for i, item in enumerate(pages_info):
            ZH_p = ['CID', '分P名称', '分P尺寸', '分P时长', '首帧图片']

            # 一些修正
            ff = item['first_frame'] if 'first_frame' in item else 'null'

            values_p = [
                item['cid'], item['part'],
                " x ".join([str(item['dimension']['height']), str(item['dimension']['width'])]),
                self.duration_conv(item['duration']), ff
            ]
            self.write_info(
                ZH_p, values_p, file_name=file_name, additional="------ P" + str(i + 1) + " -----\n", write_method='a'
            )
        print('Save video information at ' + file_name + ' successfully! \n')

    """
    用于存储全部评论
    """

    async def save_comments(self, file_name=None, is_ranked=False, save_sub=True):
        # self.write_json(self.comments, 'comments.json')
        # 创建存储评论的 DataFrame
        headers = ['id', 'time', 'user', 'content', 'like', 'reply', 'root']
        explainers = ['ID', '时间', '用户', '内容', '点赞数', '回复数', '上级评论信息']
        com_pd = pd.DataFrame(columns=headers)
        com_pd.loc['中文列标签'] = explainers
        now_index = 0

        # 存储评论
        for cmt in self.comments:
            cmt_info = self.get_single_comm_info(cmt)
            now_index += 1
            com_pd.loc[str(now_index)] = cmt_info

            # 存储子评论
            if save_sub and len(cmt['replies']) > 0:
                # 实例化 Comment 类
                root_cmt = comment.Comment(self.info['aid'], comment.ResourceType.VIDEO, cmt_info[0],
                                           credential=self.cred)
                # 得到子评论
                sub_cmts = await root_cmt.get_sub_comments()
                if sub_cmts['replies'] is not None:
                    now_sub_index = 0
                    for subc in sub_cmts['replies']:
                        now_sub_index += 1
                        subc_info = self.get_single_comm_info(subc)
                        com_pd.loc[str(now_index) + '.' + str(now_sub_index)] = subc_info

        # 评论信息变量，类型为 DataFrame
        self.cmt_df = com_pd if not is_ranked else self.get_ranked_cmts(com_pd)
        self.cmt_df.to_excel(file_name, sheet_name='评论信息')
        additional = '(ranked by number of likes)\n' if is_ranked else '\n'
        print('Save comments at ' + file_name + ' successfully! ' + additional)

    """
    用于将视频信息写为txt
    """

    def write_info(self, list1, list2, file_name=None, additional="", write_method='w'):
        if file_name is None:
            assert ('File path cannot be empty! ')
        with open(file_name, write_method, encoding='utf-8') as f:
            f.write(additional)
            # 若列表不为空，则进行写入
            if len(list1) == len(list2) and len(list1) > 0:
                for it1, it2 in zip(list1[:-1], list2[:-1]):
                    f.write(str(it1) + '：' + str(it2) + ', \n')
                f.write(list1[-1] + '：' + list2[-1] + '. \n')
                f.write('\n\n')
            f.close()

    """
    用于将词典写为'.json'文件
    参考：https://blog.csdn.net/Strive_For_Future/article/details/107564274
    """

    def write_json(self, dict, file_name=None):
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(dict, f, ensure_ascii=False)  # 使得中文字符能够正常显示
            f.close()
            print('Save ' + file_name + ' successfully! \n')

    ################# 一些转换函数 #################
    """
    将ctime（格林威治时间）（以秒计）转换为正常时间
    """

    def ctime_conv(self, ctime: int):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ctime))

    """
    将视频时长（以分钟计）转化为" xx mins xxx secs"的形式
    """

    def duration_conv(self, duration: int):
        return str(int(duration / 60)) + ' mins ' + str(duration % 60) + ' secs'

    """
    将评论按照点赞数进行排序
    """

    def get_ranked_cmts(self, cmt_df: pd.DataFrame):
        # 通过截取整数标签将 cmt_df 进行分块
        # 例如，第10条评论的区间在: cmt_df.iloc[main_idxs[9]:main_idxs[10], :],
        # 最后一条评论的区间在：cmt_df.iloc[main_idxs[self.comments_num-1]:, :].
        main_idxs = []
        for i, idx in enumerate(cmt_df.index[1:]):
            if float(idx) == int(float(idx)):
                main_idxs.append(i + 1)

        # 只含主评论的 DataFrame
        self.main_cmts_df = cmt_df.iloc[main_idxs, :]

        sorted_index = self.main_cmts_df.sort_values(by='like', ascending=False).index
        self.rearranged_cmt_df = pd.concat([
            self.get_cmt_batch(cmt_df, main_idxs, int(idx)) for idx in sorted_index
        ])
        self.rearranged_cmt_df.columns = cmt_df.iloc[0, :].to_numpy()
        return self.rearranged_cmt_df

    """
    获取评论块
    num := number of cmt_df's index tags, 
    num \in [1, self.comments_num]. 
    """

    def get_cmt_batch(self, cmt_df: pd.DataFrame, main_idxs: list, num: int):
        batch = None
        if num < self.comments_num:
            batch = cmt_df.iloc[main_idxs[num - 1]:main_idxs[num], :]
        if num == self.comments_num:
            batch = cmt_df.iloc[main_idxs[self.comments_num - 1]:, :]
        return batch


if __name__ == '__main__':
    vi = VideoInfo("BV18u411Z7t1")
    vi.save_info(file_name='BV18u411Z7t1/视频信息.txt')
    asyncio.get_event_loop().run_until_complete(
        vi.save_comments(file_name='BV18u411Z7t1/Comments.xlsx', is_ranked=False))
    asyncio.get_event_loop().run_until_complete(
        vi.save_comments(file_name='BV18u411Z7t1/评论信息（已根据点赞数排序）.xlsx', is_ranked=True))
