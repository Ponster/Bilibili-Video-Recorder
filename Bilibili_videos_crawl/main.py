from Bilibili_videos_crawl.VideoInfo import *
import asyncio
from bilibili_api import video, Credential
from Bilibili_videos_crawl.CommentsMerge import *
import os
from shutil import copyfile
from sys import exit
import pandas as pd

bvid = 'BV18f4y1T7qZ'

import os

def del_files(path_file):
    ls = os.listdir(path_file)
    for i in ls:
        f_path = os.path.join(path_file, i)
        # 判断是否是一个目录,若是,则递归删除
        if os.path.isdir(f_path):
            del_files(f_path)
        else:
            os.remove(f_path)

"""
目前只支持单P视频，多P视频可做一些修改。
这里本人没时间做了... 日后填坑。
"""
if __name__ == '__main__':
    ########## Step 1: 创建文件夹 ##########
    if os.path.exists(bvid):
        del_files(bvid)
    else:
        os.mkdir(bvid)

    # 视频信息地址
    video_info_dir = bvid + '/视频信息.txt'

    # 评论信息地址
    hidden_cmt_dir = bvid + '/Comments.xlsx' # 隐藏文件
    cmt_dir = bvid + '/评论信息（已根据点赞数排序）.xlsx'
    print('已成功创建视频信息文件夹！\n')


    ########## Step 2: 抓取视频信息（弹幕、评论） ##########
    vi = VideoInfo(bvid)
    # 抓取弹幕信息部分，使用you-get。
    # 本人能力有限，实在没找到如何能不下载视频，只下载弹幕文件的方法...
    # 于是只好进行一系列骚操作
    video_name = vi.info['title']
    input = 'fake_video.mp4'
    output = bvid + '\\' + video_name + '.mp4'
    try:
       copyfile(input, output)
    except IOError as e:
       print("Unable to copy file. %s" % e)
       exit(1)

    command = 'you-get https://www.bilibili.com/video/' + bvid + ' --skip-existing-file-size-check -o ' + bvid
    os.system(command)
    print('已成功下载弹幕文件！\n')

    # 抓取评论信息部分，使用 bilibili-api。
    # 存储视频信息
    vi.save_info(file_name=video_info_dir)

    # 存储评论信息
    asyncio.get_event_loop().run_until_complete(
        vi.save_comments(file_name=hidden_cmt_dir, is_ranked=False))
    asyncio.get_event_loop().run_until_complete(
        vi.save_comments(file_name=cmt_dir, is_ranked=True))


    ########## Step 3: 将xml文件转'.ass'弹幕，并将评论加入弹幕 ##########
    # xml 文件地址
    xml_path = bvid + '/' + video_name + '.cmt.xml'
    # 视频评论信息
    cmt_df = pd.read_excel(hidden_cmt_dir, index_col=[0])
    # 视频持续时长
    total_length = vi.info['duration']
    merge(xml_path, cmt_df, total_length, xml_path)

    xml2ass_command = 'python danmaku2ass.py \"' + xml_path + '\" -fn 微软雅黑 -r'
    os.system(xml2ass_command)
    print('转换为 .ass 弹幕文件成功！\n')

    ########## Step 4: 清场工作：删除不必要的文件 ##########
    list = [
        hidden_cmt_dir, xml_path, bvid + '/' + video_name + '.mp4'
    ]
    for item in list:
        os.remove(item)
    print('工作已完成！\n')

